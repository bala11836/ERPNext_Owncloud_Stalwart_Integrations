"""Vendor Onboarding (ADR-039).

Flow:
1. Staff create a Vendor Onboarding record, optionally pre-filling it.
2. "Send" makes the ONE onboarding link (email + a hand-share link, shown once).
3. The vendor fills or confirms the form on respond.example.com (no login) and submits. Server-side checks
   run on submit.
4. The principal contact's email is verified by a second link.
5. A different person, with an approver role, approves.
6. Only then are ERPNext's own Supplier, Address, Contact(s), Bank Account (+ Bank) and files created.

Outside data is untrusted until approved. The vendor can change only the fields in VENDOR_FIELDS. GST facts
come only from the server's own lookup.
"""
import base64
import json

import frappe
import requests
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime

from erpnext_drive_integrations.onboarding import kyc
from erpnext_drive_integrations.onboarding.respond import (check_different_approver, check_role, create_request, finish, guard, log, notify,
                               send_email, system_save)

DOCTYPE = "Vendor Onboarding"
VENDOR_FIELDS = {
    "business_name": "Business name", "constitution": "Constitution", "pan": "PAN", "gstin": "GSTIN",
    "no_gst": "No GST registration", "address_line1": "Address line 1", "address_line2": "Address line 2",
    "city": "City", "state": "State", "pincode": "PIN code", "cin": "CIN", "udyam_number": "Udyam number",
    "ifsc": "Bank IFSC", "bank_account_no": "Bank account no.", "account_holder_name": "Account holder name",
}
ADDRESS_FIELDS = ("address_line1", "address_line2", "city", "state", "pincode")
GST_FACTS = ("gst_legal_name", "gst_trade_name", "gst_status", "gst_category", "gst_checked_on", "from_gst")
PERSON_FIELDS = ("person_name", "designation", "email", "mobile", "is_principal", "whatsapp_opt_in")
VENDOR_DOC_TYPES = tuple(t for t in kyc.DOCUMENT_TYPES if t != "Director check screenshot")
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES = 12
MAX_GST_LOOKUPS = 5  # per onboarding link: each lookup costs India Compliance credits
FILE_MAGIC = {"pdf": (b"%PDF",), "jpg": (b"\xff\xd8\xff",), "jpeg": (b"\xff\xd8\xff",), "png": (b"\x89PNG",)}


def values_of(doc):
    data = {f: doc.get(f) for f in (*VENDOR_FIELDS, *GST_FACTS, "name")}
    persons = [{f: p.get(f) for f in (*PERSON_FIELDS, "email_verified_on", "opt_in_on", "director_check", "name")} for p in doc.persons]
    return data, persons


def onboarding_of(req):
    if req.reference_doctype != DOCTYPE:
        frappe.throw(_("This link is not for a vendor form."), frappe.PermissionError)
    return frappe.get_doc(DOCTYPE, req.reference_name)


# ---------- handler API for respond.py ----------

def form_spec(req):
    doc = onboarding_of(req)
    if req.purpose == "Email verification":
        person = next((p for p in doc.persons if p.name == req.target), None)
        return {"kind": "email_verify", "email": kyc.mask_email(person.email if person else "")}
    data, persons = values_of(doc)
    return {"kind": "vendor_form", "values": {k: data.get(k) for k in (*VENDOR_FIELDS, *GST_FACTS)},
            "persons": [{f: p.get(f) for f in (*PERSON_FIELDS, "name")} for p in persons],
            "documents": [{"document_type": d.document_type, "uploaded": bool(d.file)} for d in doc.documents if d.uploaded_by_vendor],
            "constitutions": list(kyc.CONSTITUTIONS), "document_types": list(VENDOR_DOC_TYPES)}


def on_answer(req, channel, decision, reason):
    if req.purpose != "Email verification" or decision != "Verified":
        frappe.throw(_("Not allowed."), frappe.PermissionError)
    doc = onboarding_of(req)
    person = next((p for p in doc.persons if p.name == req.target), None)
    if not person:
        frappe.throw(_("This contact no longer exists."), frappe.PermissionError)
    finish(req, "Verified", channel)
    person.email_verified_on = now_datetime()
    system_save(doc)
    notify(req.owner, f"{doc.name}: principal contact email verified", DOCTYPE, doc.name)
    return {"ok": True, "message": "Thank you. Your email address is verified."}


# ---------- guest API (the vendor's form) ----------

def _open_form(key):
    req, channel = guard(key)
    if req.purpose != "Vendor Onboarding":
        frappe.throw(_("Not allowed."), frappe.PermissionError)
    doc = onboarding_of(req)
    if doc.status != "Sent":
        frappe.throw(_("This form is no longer open."), frappe.PermissionError)
    return req, channel, doc


def _apply(doc, values, persons):
    """Copy only what the vendor may change. GST-locked address fields and GST facts are never taken."""
    values = frappe.parse_json(values) if isinstance(values, str) else (values or {})
    locked = set(ADDRESS_FIELDS) if doc.from_gst else set()
    if "ifsc" in values and kyc.norm(values["ifsc"]) != kyc.norm(doc.ifsc):
        doc.bank_name = doc.bank_branch = None  # bank name must come from a lookup of THIS IFSC
    if "gstin" in values and kyc.norm(values["gstin"]) != kyc.norm(doc.gstin):
        for field in GST_FACTS:  # GST facts belonged to the old GSTIN
            doc.set(field, None)
    for field in VENDOR_FIELDS:
        if field in values and field not in locked:
            value = values[field]
            doc.set(field, (1 if value else 0) if field == "no_gst" else str(value or "").strip()[:140])
    if persons is not None:
        persons = frappe.parse_json(persons) if isinstance(persons, str) else persons
        doc.set("persons", [])
        for p in (persons or [])[:10]:
            doc.append("persons", {f: ((1 if p.get(f) else 0) if f in ("is_principal", "whatsapp_opt_in")
                                       else str(p.get(f) or "").strip()[:140]) for f in PERSON_FIELDS})


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=60)
def save(key, values=None, persons=None):
    req, channel, doc = _open_form(key)
    _apply(doc, values, persons)
    system_save(doc)
    return {"ok": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=3600)
def lookup_gstin(key, gstin):
    req, channel, doc = _open_form(key)
    gstin = kyc.norm(gstin)
    if problem := kyc.gstin_problem(gstin):
        return {"ok": False, "message": problem}
    counter = f"hov:gst-lookups:{req.name}"
    if (frappe.cache.get_value(counter) or 0) >= MAX_GST_LOOKUPS:
        return {"ok": False, "message": "Too many GST lookups on this form. Please type the address."}
    frappe.cache.set_value(counter, (frappe.cache.get_value(counter) or 0) + 1, expires_in_sec=7 * 86400)
    try:
        info = gst_info(gstin)
    except Exception:
        frappe.clear_last_message()
        frappe.log_error(title="Vendor onboarding: GSTIN lookup failed", reference_doctype=DOCTYPE, reference_name=doc.name)
        return {"ok": False, "message": "GST lookup is not available right now. Please type your address; we will check it."}
    if not info:
        return {"ok": False, "message": "This GSTIN was not found on the GST portal."}
    apply_gst_info(doc, gstin, info)
    system_save(doc)
    log(req, "GSTIN looked up", channel, f"{gstin}: {doc.gst_status}")
    return {"ok": True, "values": {f: doc.get(f) for f in (*VENDOR_FIELDS, *GST_FACTS)}}


def gst_info(gstin):
    """GST portal facts through India Compliance (uses credits). None when the GSTIN is unknown."""
    from india_compliance.gst_india.utils.gstin_info import _get_gstin_info
    info = _get_gstin_info(gstin, throw_error=True)
    return info if info and info.get("gstin") else None


def apply_gst_info(doc, gstin, info):
    doc.gstin, doc.no_gst = gstin, 0
    doc.gst_legal_name, doc.gst_trade_name = info.get("legal_name"), info.get("trade_name")
    doc.gst_status, doc.gst_category, doc.gst_checked_on = info.get("status"), info.get("gst_category"), now_datetime()
    if addr := info.get("permanent_address"):
        for field in ADDRESS_FIELDS:
            doc.set(field, addr.get(field) or "")
        doc.from_gst = 1
    if not doc.business_name:
        doc.business_name = info.get("business_name")
    if not doc.pan:
        doc.pan = kyc.pan_from_gstin(gstin)


def auto_fill(doc, before=None):
    """Staff side, Draft only (MD 2026-11-12: no manual check buttons): when the IFSC or GSTIN changes, the
    server looks up the bank and the GST facts by itself. Returns plain notes for the user."""
    notes = []
    ifsc = kyc.norm(doc.ifsc)
    if ifsc != (kyc.norm(before.ifsc) if before else "") or (ifsc and not doc.bank_name):
        doc.bank_name = doc.bank_branch = None
        details = None
        if ifsc and (problem := kyc.ifsc_problem(ifsc)):
            notes.append(problem)
        elif ifsc:
            try:
                details = ifsc_details(ifsc)
                if not details:
                    notes.append("This IFSC was not found. Please check it.")
            except Exception:
                notes.append("Bank lookup is not available right now. It is tried again on the next save.")
        if details:
            doc.bank_name, doc.bank_branch = details["bank_name"], details["bank_branch"]
    effective = lambda d: "" if not d or d.no_gst else kyc.norm(d.gstin)  # noqa: E731
    gstin = effective(doc)
    if gstin != effective(before) or (gstin and not doc.gst_checked_on):
        for field in GST_FACTS:  # GST facts belong to one GSTIN
            doc.set(field, None)
        if gstin and (problem := kyc.gstin_problem(gstin)):
            notes.append(problem)
        elif gstin and not frappe.cache.get_value(f"hov:gst-unknown:{gstin}"):
            try:
                info = gst_info(gstin)
            except Exception:
                frappe.clear_last_message()
                notes.append("GST lookup is not available (India Compliance API account). Type the address by hand.")
            else:
                if info:
                    apply_gst_info(doc, gstin, info)
                else:  # ponytail: remembered for a day so each save does not spend a lookup credit
                    frappe.cache.set_value(f"hov:gst-unknown:{gstin}", 1, expires_in_sec=86400)
                    notes.append("This GSTIN was not found on the GST portal.")
    return notes


def ifsc_details(ifsc):
    """Razorpay's open IFSC directory (free, no key). Cached 30 days. None when unknown."""
    ifsc = kyc.norm(ifsc)
    cache_key = f"hov:ifsc:{ifsc}"
    cached = frappe.cache.get_value(cache_key)
    if cached is not None:
        return cached or None
    resp = requests.get(f"https://ifsc.razorpay.com/{ifsc}", timeout=8)
    if resp.status_code == 404:
        frappe.cache.set_value(cache_key, {}, expires_in_sec=86400)
        return None
    resp.raise_for_status()
    details = kyc.parse_ifsc(resp.json())
    frappe.cache.set_value(cache_key, details, expires_in_sec=30 * 86400)
    return details


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=600)
def lookup_ifsc(key, ifsc):
    req, channel, doc = _open_form(key)
    if problem := kyc.ifsc_problem(ifsc):
        return {"ok": False, "message": problem}
    try:
        details = ifsc_details(ifsc)
    except Exception:
        frappe.log_error(title="Vendor onboarding: IFSC lookup failed", reference_doctype=DOCTYPE, reference_name=doc.name)
        return {"ok": False, "message": "Bank lookup is not available right now. Please try again in a minute."}
    if not details:
        return {"ok": False, "message": "This IFSC was not found. Please check it on your cheque."}
    doc.ifsc, doc.bank_name, doc.bank_branch = kyc.norm(ifsc), details["bank_name"], details["bank_branch"]
    system_save(doc)
    return {"ok": True, "bank_name": doc.bank_name, "bank_branch": doc.bank_branch}


def file_ok(filename, content):
    ext = (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    return ext in FILE_MAGIC and any(content.startswith(m) for m in FILE_MAGIC[ext])


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=600)
def upload(key, document_type, filename, data):
    req, channel, doc = _open_form(key)
    if document_type not in VENDOR_DOC_TYPES:
        frappe.throw(_("Choose a document type."))
    if len(doc.documents) >= MAX_FILES:
        frappe.throw(_("Too many files on this form."))
    if len(str(data or "")) > MAX_FILE_BYTES * 4 // 3 + 200:  # refuse before decoding (base64 is 4/3 larger)
        frappe.throw(_("Files must be smaller than 5 MB."))
    try:
        content = base64.b64decode(str(data).split(",", 1)[-1], validate=True)
    except Exception:
        frappe.throw(_("The file could not be read."))
    if not content or len(content) > MAX_FILE_BYTES:
        frappe.throw(_("Files must be smaller than 5 MB."))
    if not file_ok(filename, content):
        frappe.throw(_("Only PDF, JPG or PNG files are accepted."))
    ext = filename.rsplit(".", 1)[-1].lower()
    file = frappe.get_doc({"doctype": "File", "file_name": f"{doc.name} {document_type}.{ext}", "content": content,
                           "is_private": 1, "attached_to_doctype": DOCTYPE, "attached_to_name": doc.name})
    file.flags.ignore_permissions = True
    try:
        file.insert()
    except frappe.ValidationError:
        raise
    except Exception:  # e.g. a damaged PDF that Frappe's own content check cannot parse
        frappe.clear_last_message()
        frappe.throw(_("This file is damaged and could not be read. Please upload it again, or use a photo (JPG / PNG)."))
    doc.append("documents", {"document_type": document_type, "file": file.file_url, "uploaded_by_vendor": 1})
    system_save(doc)
    log(req, "Document uploaded", channel, document_type)
    return {"ok": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def submit(key, values=None, persons=None, account_confirm=None):
    req, channel, doc = _open_form(key)
    _apply(doc, values, persons)
    data, people = values_of(doc)
    problems = kyc.vendor_problems(data, people, account_confirm=account_confirm or "")
    errors = [m for level, m in problems if level == kyc.ERROR]
    if errors:
        system_save(doc)  # keep what they typed
        return {"ok": False, "errors": errors}
    snapshot = json.loads(doc.sent_snapshot or "{}")
    changed = kyc.changed_fields(snapshot, data, VENDOR_FIELDS) if snapshot else []
    notes = [f"[{level}] {m}" for level, m in problems]
    if changed:
        notes.append("[info] Vendor changed: " + ", ".join(changed))
    have = {d.document_type for d in doc.documents if d.file}
    missing = [t for t in ("PAN card", "Cancelled cheque") + (() if doc.no_gst else ("GST certificate",)) if t not in have]
    if missing:
        notes.append("[warning] Documents not attached: " + ", ".join(missing))
    for p in doc.persons:
        if p.whatsapp_opt_in and not p.opt_in_on:
            p.opt_in_on = now_datetime()
    doc.checks = "\n".join(notes) or "No problems found."
    doc.status = "Submitted by vendor"
    system_save(doc)
    finish(req, "Submitted", channel)
    main = kyc.principal(people)
    row = next(p for p in doc.persons if p.is_principal)
    vreq, urls = create_request(DOCTYPE, doc.name, "Email verification", recipient_name=main["person_name"],
                                email=main["email"].strip(), channels=("Email",), path="v", target=row.name)
    send_email(vreq, urls["Email"], "Please confirm your email address (Example Organization Constructions)",
               "Please confirm that this email address belongs to you. It will be used for purchase orders and payments.")
    notify(doc.owner, f"{doc.name}: vendor submitted the onboarding form", DOCTYPE, doc.name)
    return {"ok": True, "message": "Thank you. Your details are submitted. Please confirm your email from the message we just sent."}


# ---------- staff API ----------

def _staff_doc(name, right="write"):
    doc = frappe.get_doc(DOCTYPE, name)
    doc.check_permission(right)
    return doc


@frappe.whitelist(methods=["POST"])
def send(name):
    """Create the ONE onboarding link (MD rule: generated only once; later changes = KYC Amendment)."""
    doc = _staff_doc(name)
    check_role(DOCTYPE, "requester_roles", fallback=None)
    if doc.response_request:
        frappe.throw(_("The onboarding link was already created once. For changes, use a KYC Amendment."))
    if doc.invite_email and not kyc.EMAIL_RE.match(doc.invite_email.strip()):
        frappe.throw(_("Invite email address looks wrong."))
    channels = ("Email", "Manual") if doc.invite_email else ("Manual",)
    req, urls = create_request(DOCTYPE, doc.name, "Vendor Onboarding", recipient_name=doc.invite_name or doc.business_name,
                               email=(doc.invite_email or "").strip() or None, mobile=kyc.norm_mobile(doc.invite_mobile) or None,
                               channels=channels, path="o")
    data, persons = values_of(doc)
    doc.sent_snapshot = json.dumps({k: data.get(k) for k in VENDOR_FIELDS}, default=str)
    doc.response_request, doc.status = req.name, "Sent"
    system_save(doc)
    if doc.invite_email:
        send_email(req, urls["Email"], "Vendor registration with Example Organization Constructions",
                   "Please fill in (or check) your company details, bank details and contact persons.")
    return {"manual_link": urls["Manual"], "request": req.name}


@frappe.whitelist(methods=["POST"])
def reject(name, reason):
    doc = _staff_doc(name)
    check_role(DOCTYPE, "approver_roles")
    if doc.status not in ("Sent", "Submitted by vendor"):
        frappe.throw(_("Only open forms can be rejected."))
    doc.status, doc.staff_note = "Rejected", ((doc.staff_note or "") + f"\nRejected: {reason}").strip()
    system_save(doc)
    if doc.response_request:
        req = frappe.get_doc("Response Request", doc.response_request)
        if req.status == "Sent":
            req.status = "Cancelled"
            log(req, "Cancelled (onboarding rejected)", "", f"by {frappe.session.user}")
    return True


def insert_bank_account(values, supplier, bank):
    """ERPNext names a Bank Account '<account_name> - <bank>'. On a clash (same holder name at the same bank)
    add ' (2)', ' (3)' ... to account_name. Normally account_name stays exactly the holder name."""
    if not frappe.db.exists("Bank", bank):
        frappe.get_doc({"doctype": "Bank", "bank_name": bank}).insert()
    doc = kyc.bank_account_doc(values, supplier, bank)
    holder, n = doc["account_name"], 1
    while frappe.db.exists("Bank Account", f"{doc['account_name']} - {bank}"):
        n += 1
        doc["account_name"] = f"{holder} ({n})"
    return frappe.get_doc(doc).insert()


def find_duplicates(doc):
    """Existing Suppliers / Bank Accounts with the same GSTIN, PAN or bank account (ghost vendors, double entry)."""
    found = []
    for field, value in (("gstin", kyc.norm(doc.gstin)), ("pan", kyc.norm(doc.pan))):
        if value:
            found += [f"{field.upper()} already on Supplier {s}" for s in frappe.get_all("Supplier", {field: value}, pluck="name")]
    for acc in frappe.get_all("Bank Account", {"bank_account_no": kyc.norm(doc.bank_account_no)}, ["name", "party"]):
        found.append(f"Bank account already used by {acc.party or acc.name}")
    return found


@frappe.whitelist(methods=["POST"])
def approve(name, confirm_duplicates=0):
    doc = _staff_doc(name)
    check_role(DOCTYPE, "approver_roles")
    check_different_approver(DOCTYPE, doc)
    if doc.status != "Submitted by vendor":
        frappe.throw(_("Only a form submitted by the vendor can be approved."))
    data, persons = values_of(doc)
    errors = [m for level, m in kyc.vendor_problems(data, persons) if level == kyc.ERROR]
    if errors:
        frappe.throw("<br>".join(map(frappe.utils.escape_html, errors)))
    main = next(p for p in doc.persons if p.is_principal)
    if not main.email_verified_on:
        frappe.throw(_("The principal contact has not verified their email yet."))
    if doc.constitution == "Company" and any(p.director_check in (None, "", "Not checked") for p in doc.persons if p.is_principal):
        frappe.throw(_("Company: record the director check for the principal contact first (MCA / Tofler screenshot)."))
    duplicates = find_duplicates(doc)
    if duplicates and not frappe.utils.cint(confirm_duplicates):
        return {"duplicates": duplicates}

    supplier = frappe.get_doc(kyc.supplier_doc(data)).insert()
    address = frappe.get_doc(kyc.address_doc(data, supplier.name)).insert()
    contacts = [frappe.get_doc(kyc.contact_doc(p, supplier.name)).insert() for p in persons]
    bank = doc.bank_name or (ifsc_details(doc.ifsc) or {}).get("bank_name")
    if not bank:
        frappe.throw(_("Bank name unknown for this IFSC; look it up again and retry."))
    account = insert_bank_account(data, supplier.name, bank)
    supplier.supplier_primary_address = address.name
    supplier.supplier_primary_contact = next(c.name for c, p in zip(contacts, persons) if p.get("is_principal"))
    supplier.save()
    for d in doc.documents:
        # Audit HOV-04: copy only files really attached to THIS onboarding, never any private URL typed into a row.
        if d.file and frappe.db.exists("File", {"file_url": d.file, "attached_to_doctype": DOCTYPE, "attached_to_name": doc.name}):
            frappe.get_doc({"doctype": "File", "file_url": d.file, "file_name": f"{d.document_type} ({doc.name})",
                            "is_private": 1, "attached_to_doctype": "Supplier", "attached_to_name": supplier.name}).insert(ignore_permissions=True)
    doc.supplier, doc.status, doc.approved_by, doc.approved_on = supplier.name, "Approved", frappe.session.user, now_datetime()
    if duplicates:
        doc.checks = (doc.checks or "") + "\n[warning] Approved despite: " + "; ".join(duplicates)
    system_save(doc)
    return {"supplier": supplier.name, "bank_account": account.name}
