# Copyright (c) 2026, Cloud. Part of onboarding (ADR-039).
import frappe
from frappe import _
from frappe.model.document import Document

LOCKED = ("supplier", "way", "status", "response_request", "new_bank_account", "approved_by", "approved_on",
          "send_to_email", "includes_bank_change")


class KYCAmendment(Document):
    def validate(self):
        if frappe.flags.hov_system_write:
            return
        if self.is_new():
            self.status, self.response_request, self.new_bank_account, self.approved_by, self.approved_on = "Draft", None, None, None, None
        else:
            before = self.get_doc_before_save()
            if before.status != "Draft":
                rows = lambda d: [(r.field, r.new_value or "", r.editable_by_vendor) for r in d.changes]  # noqa: E731
                if any(str(before.get(f) or "") != str(self.get(f) or "") for f in LOCKED) or rows(before) != rows(self):
                    frappe.throw(_("After sending, only the note can be changed."))
                return
            if any(str(before.get(f) or "") != str(self.get(f) or "") for f in LOCKED if f not in ("supplier", "way")):
                frappe.throw(_("These fields are set by the system."))
        from erpnext_drive_integrations.onboarding.amendment import refresh

        refresh(self)

    def on_trash(self):
        if self.status != "Draft":
            frappe.throw(_("Only Draft amendments can be deleted."))
