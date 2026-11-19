"""KYC Amendment (ADR-039): the only way to change an onboarded vendor's details.

The vendor asks us by hand. Staff then choose:
- (a) "Staff edit, vendor confirms": staff type the new values; the vendor sees old -> new and taps
  Confirm or Reject.
- (b) "Amendment form": staff unlock some fields; the vendor fills them in on a one-time form.

Rules:
- The request always goes to the vendor's CURRENT, verified principal contact email, even when that email
  is the thing being changed. That blocks "please pay our new account" fraud.
- Nothing changes in ERPNext until a different person with an approver role approves.
- Bank changes create a NEW Bank Account; the old one is disabled, never edited.
- A changed email or mobile becomes unverified again.
"""
import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime

from erpnext_drive_integrations.onboarding import kyc
from erpnext_drive_integrations.onboarding.respond import (check_different_approver, check_role, create_request, finish, guard, notify,
                               send_email, system_save)

DOCTYPE = "KYC Amendment"
WAY_CONFIRM, WAY_FORM = "Staff edit, vendor confirms", "Amendment form"
MASKED = {"Bank account no."}


def default_bank_account(supplier):
    filters = {"party_type": "Supplier", "party": supplier, "disabled": 0}
    return frappe.db.get_value("Bank Account", {**filters, "is_default": 1}) or frappe.db.get_value("Bank Account", filters)


def current_records(supplier):
    sup = frappe.get_doc("Supplier", supplier)
    get = lambda dt, name: frappe.get_doc(dt, name) if name else None  # noqa: E731
    return {"Supplier": sup, "Address": get("Address", sup.supplier_primary_address),
            "Contact": get("Contact", sup.supplier_primary_contact),
            "Bank Account": get("Bank Account", default_bank_account(supplier))}


def current_values(records):
    return {label: str((records[rec].get(field) if records[rec] else "") or "")
            for label, (rec, field) in kyc.AMENDABLE.items()}


def shown(label, value):
    """What the vendor sees for an OLD value (bank account numbers masked)."""
    value = str(value or "")
    return ("••••" + value[-4:]) if label in MASKED and value else value


def principal_email(records):
    contact = records["Contact"]
    if not contact or not contact.email_id:
        frappe.throw(_("This supplier has no principal contact email."))
    if not contact.get("hov_email_verified_on"):
        frappe.throw(_("The principal contact's email is not verified, so it can't be used to confirm changes."))
    return contact


def unverify_changed_contact(doc, method=None):
    """Contact validate hook (audit HOV-01): anyone who edits a vendor's email / mobile in the desk must not
    inherit the old verification, or they could confirm a bank change sent to their own address."""
    before = doc.get_doc_before_save()
    if not before:
        return
    if kyc.changed(before.email_id, doc.email_id):
        doc.hov_email_verified_on = None
    if kyc.changed(before.mobile_no, doc.mobile_no):
        doc.hov_whatsapp_verified_on = None


def refresh(doc):
    """Server-side fill of old values / bank flag / recipient (called from the DocType's validate)."""
    records = current_records(doc.supplier)
    old = current_values(records)
    for row in doc.changes:
        row.old_value = old.get(row.field, "")
    doc.includes_bank_change = int(any(r.field in kyc.BANK_LABELS for r in doc.changes))
    contact = records["Contact"]
    doc.send_to_email = contact.email_id if contact else None


# ---------- handler API for respond.py ----------

def form_spec(req):
    doc = frappe.get_doc(DOCTYPE, req.reference_name)
    title = f"Change of details for {frappe.db.get_value('Supplier', doc.supplier, 'supplier_name')}"
    if doc.way == WAY_CONFIRM:
        return {"kind": "confirm_changes", "title": title,
                "changes": [{"field": r.field, "old": shown(r.field, r.old_value), "new": r.new_value} for r in doc.changes]}
    return {"kind": "amendment_form", "title": title,
            "rows": [{"field": r.field, "old": shown(r.field, r.old_value), "value": r.new_value or "",
                      "editable": bool(r.editable_by_vendor)} for r in doc.changes],
            "needs_account_confirm": any(r.field == "Bank account no." and r.editable_by_vendor for r in doc.changes)}


def on_answer(req, channel, decision, reason):
    doc = frappe.get_doc(DOCTYPE, req.reference_name)
    if doc.way != WAY_CONFIRM or doc.status != "Sent" or decision not in ("Confirmed", "Rejected"):
        frappe.throw(_("Not allowed."), frappe.PermissionError)
    finish(req, decision, channel, reason)
    doc.status = "Confirmed by vendor" if decision == "Confirmed" else "Rejected"
    if reason:
        doc.staff_note = ((doc.staff_note or "") + f"\nVendor: {reason}").strip()
    system_save(doc)
    notify(doc.owner, f"{doc.name}: vendor {decision.lower()} the changes", DOCTYPE, doc.name)
    return {"ok": True, "message": f"Thank you. Your answer ({decision}) is recorded."}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def submit_form(key, values=None, account_confirm=None):
    """Guest, way (b): the vendor fills the unlocked fields."""
    req, channel = guard(key)
    doc = frappe.get_doc(DOCTYPE, req.reference_name) if req.reference_doctype == DOCTYPE else None
    if not doc or doc.way != WAY_FORM or doc.status != "Sent":
        frappe.throw(_("This form is no longer open."), frappe.PermissionError)
    values = frappe.parse_json(values) if isinstance(values, str) else (values or {})
    for row in doc.changes:
        if row.editable_by_vendor:
            row.new_value = str(values.get(row.field) or "").strip()[:140]
    errors = kyc.amendment_problems([{"field": r.field, "new_value": r.new_value} for r in doc.changes])
    account = next((r for r in doc.changes if r.field == "Bank account no." and r.editable_by_vendor), None)
    if account and kyc.norm(account_confirm) != kyc.norm(account.new_value):
        errors.append("The re-typed bank account number does not match.")
    if errors:
        return {"ok": False, "errors": errors}
    doc.status = "Submitted by vendor"
    system_save(doc)
    finish(req, "Submitted", channel)
    notify(doc.owner, f"{doc.name}: vendor submitted the amendment form", DOCTYPE, doc.name)
    return {"ok": True, "message": "Thank you. Your changes are submitted for approval."}


# ---------- staff API ----------

@frappe.whitelist(methods=["POST"])
def send(name):
    doc = frappe.get_doc(DOCTYPE, name)
    doc.check_permission("write")
    check_role(DOCTYPE, "requester_roles", fallback=None)
    if doc.status != "Draft" or doc.response_request:
        frappe.throw(_("Already sent."))
    if not doc.changes:
        frappe.throw(_("Add at least one change."))
    if doc.way == WAY_CONFIRM:
        if errors := kyc.amendment_problems([{"field": r.field, "new_value": r.new_value} for r in doc.changes]):
            frappe.throw("<br>".join(map(frappe.utils.escape_html, errors)))
        path, intro = "r", "We have prepared the changes you asked for. Please check them and confirm."
    else:
        if not any(r.editable_by_vendor for r in doc.changes):
            frappe.throw(_("Tick 'Vendor fills this' on at least one row."))
        path, intro = "o", "Please fill in the new details you asked us to change."
    contact = principal_email(current_records(doc.supplier))
    req, urls = create_request(DOCTYPE, doc.name, "KYC Amendment", recipient_name=contact.full_name or contact.first_name,
                               email=contact.email_id, channels=("Email",), path=path)
    doc.response_request, doc.status = req.name, "Sent"
    system_save(doc)
    send_email(req, urls["Email"], "Change of your details with Example Organization Constructions", intro)
    return {"request": req.name}


@frappe.whitelist(methods=["POST"])
def approve(name):
    doc = frappe.get_doc(DOCTYPE, name)
    doc.check_permission("write")
    check_role(DOCTYPE, "approver_roles")
    check_different_approver(DOCTYPE, doc)
    if doc.status not in ("Confirmed by vendor", "Submitted by vendor"):
        frappe.throw(_("Only changes confirmed or submitted by the vendor can be approved."))
    if errors := kyc.amendment_problems([{"field": r.field, "new_value": r.new_value} for r in doc.changes]):
        frappe.throw("<br>".join(map(frappe.utils.escape_html, errors)))
    records = current_records(doc.supplier)
    new = {r.field: r.new_value.strip() if r.new_value else "" for r in doc.changes}
    touched = set()
    for label, value in new.items():
        rec, field = kyc.AMENDABLE[label]
        if rec in ("Supplier", "Address"):
            if not records[rec]:
                frappe.throw(_("This supplier has no primary {0}.").format(rec))
            records[rec].set(field, value or None)
            touched.add(rec)
    contact = records["Contact"]
    if "Principal contact email" in new:
        _set_primary(contact, "email_ids", "email_id", "is_primary", new["Principal contact email"])
        contact.hov_email_verified_on = None
        touched.add("Contact")
    if "Principal contact mobile" in new:
        _set_primary(contact, "phone_nos", "phone", "is_primary_mobile_no", kyc.norm_mobile(new["Principal contact mobile"]))
        contact.hov_whatsapp_verified_on = None
        touched.add("Contact")
    for rec in touched:
        records[rec].save()
    if kyc.BANK_LABELS & set(new):
        doc.new_bank_account = _replace_bank_account(doc.supplier, records["Bank Account"], new)
    doc.status, doc.approved_by, doc.approved_on = "Approved", frappe.session.user, now_datetime()
    system_save(doc)
    return {"ok": True, "new_bank_account": doc.new_bank_account}


def _set_primary(contact, table, field, flag, value):
    for row in contact.get(table):
        row.set(flag, 0)
    row = next((r for r in contact.get(table) if (r.get(field) or "").strip().lower() == value.lower()), None)
    if row:
        row.set(flag, 1)
    else:
        contact.append(table, {field: value, flag: 1})


def _replace_bank_account(supplier, old, new):
    from erpnext_drive_integrations.onboarding.vendor import ifsc_details, insert_bank_account

    values = {"account_holder_name": new.get("Account holder name") or (old.account_name if old else ""),
              "bank_account_no": new.get("Bank account no.") or (old.bank_account_no if old else ""),
              "ifsc": new.get("Bank IFSC") or (old.branch_code if old else "")}
    if not all(values.values()):
        frappe.throw(_("Bank holder name, account number and IFSC are all needed for the new bank account."))
    bank = (ifsc_details(values["ifsc"]) or {}).get("bank_name") if "Bank IFSC" in new else (old.bank if old else None)
    if not bank:
        frappe.throw(_("Could not find the bank for the new IFSC. Try again in a minute."))
    if old:
        old.is_default, old.disabled = 0, 1
        old.save()
    return insert_bank_account(values, supplier, bank).name
