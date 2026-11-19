# Copyright (c) 2026, Cloud. Part of onboarding (ADR-039).
import frappe
from frappe import _
from frappe.model.document import Document

from erpnext_drive_integrations.onboarding.kyc import norm
from erpnext_drive_integrations.onboarding.vendor import VENDOR_FIELDS as FORM_FIELDS

SYSTEM_FIELDS = ("status", "response_request", "supplier", "approved_by", "approved_on", "checks", "sent_snapshot",
                 "gst_legal_name", "gst_trade_name", "gst_status", "gst_category", "gst_checked_on", "from_gst",
                 "bank_name", "bank_branch")
VENDOR_FIELDS = (*FORM_FIELDS, "invite_name", "invite_email", "invite_mobile")
PERSON_LOCKED = ("person_name", "designation", "email", "mobile", "is_principal", "whatsapp_opt_in", "opt_in_on", "email_verified_on")


class VendorOnboarding(Document):
    """Staff may pre-fill in Draft. Once sent, only the vendor (through the link) changes the vendor fields;
    staff may still record the director check, add a screenshot and write notes."""

    def validate(self):
        for field in ("pan", "gstin", "ifsc", "cin", "udyam_number", "bank_account_no"):
            if self.get(field):
                self.set(field, norm(self.get(field)))
        if frappe.flags.hov_system_write:
            return
        if self.is_new():
            for field in SYSTEM_FIELDS:
                self.set(field, None)
            self.status = "Draft"
            self.auto_fill(None)
            return
        before = self.get_doc_before_save()
        locked = SYSTEM_FIELDS + (VENDOR_FIELDS if before.status != "Draft" else ())
        changed = [f for f in locked if str(before.get(f) or "") != str(self.get(f) or "")]
        if before.status != "Draft":
            old = {p.name: tuple(str(p.get(f) or "") for f in PERSON_LOCKED) for p in before.persons}
            new = {p.name: tuple(str(p.get(f) or "") for f in PERSON_LOCKED) for p in self.persons}
            if old != new:
                changed.append("contact persons")
            old_docs = {d.name: (d.document_type, d.file) for d in before.documents}
            if any((d.document_type, d.file) != old_docs.get(d.name, (d.document_type, d.file)) for d in self.documents) \
                    or set(old_docs) - {d.name for d in self.documents}:
                changed.append("documents already attached")
            for p, b in ((p, next((x for x in before.persons if x.name == p.name), None)) for p in self.persons):
                if b and (p.director_check or "") != (b.director_check or ""):
                    p.director_checked_by = frappe.session.user
        if changed:
            frappe.throw(_("These can't be changed here: {0}. After sending, changes go through the vendor's form or a KYC Amendment.")
                         .format(", ".join(changed)))
        if before.status == "Draft":
            self.auto_fill(before)

    def auto_fill(self, before):
        from erpnext_drive_integrations.onboarding.vendor import auto_fill
        for note in auto_fill(self, before):
            frappe.msgprint(_(note), indicator="orange", alert=True)

    def on_trash(self):
        if self.status != "Draft" and not frappe.flags.hov_system_write:
            frappe.throw(_("Only Draft onboarding forms can be deleted."))
