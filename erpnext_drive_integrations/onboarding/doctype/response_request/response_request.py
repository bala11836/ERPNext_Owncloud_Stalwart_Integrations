# Copyright (c) 2026, Cloud. Part of onboarding (ADR-039).
import frappe
from frappe import _
from frappe.model.document import Document

class ResponseRequest(Document):
    """Written only by erpnext_drive_integrations.onboarding.respond (never edited or deleted by people): the audit trail of a sent link."""

    def validate(self):
        if not self.is_new() and not frappe.flags.hov_system_write:
            frappe.throw(_("Response Requests are changed only by the system."))

    def on_trash(self):
        frappe.throw(_("Response Requests are never deleted (audit trail)."))
