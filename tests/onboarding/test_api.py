"""Run: python test_api.py  (no Frappe needed; a tiny fake `frappe` module)."""
import pathlib
import sys
import types
import unittest

frappe = types.ModuleType("frappe")
frappe.whitelist = lambda **kw: (lambda f: f)
frappe.session = types.SimpleNamespace(user="user-a")
frappe.get_roles = lambda user: ["Desk User", "Accounts User"]
frappe.utils = types.SimpleNamespace(get_fullname=lambda user: "User A")
boot = types.ModuleType("frappe.boot")
sys.modules.update({"frappe": frappe, "frappe.boot": boot})
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from erpnext_drive_integrations.onboarding import api  # noqa: E402

SIDEBARS = {
    "Payroll": {"name": "Payroll", "label": "Payroll", "app": "hrms", "items": [
        {"type": "Link", "link_type": "Workspace", "link_to": "Payroll", "label": "Home"},
        {"type": "Section Break", "label": "Reports"},
        {"type": "Section Break", "label": "Setup"},
        {"type": "Link", "link_type": "DocType", "link_to": "Salary Slip", "label": "Salary Slip"},
        {"type": "Link", "link_type": "Report", "link_to": "Salary Register", "label": "Salary Register"},
    ]},
    "Accounts": {"name": "Accounts", "label": "Accounts", "app": "erpnext", "items": [
        {"type": "Link", "link_type": "DocType", "link_to": "Payment Entry", "label": None},
    ]},
    "Empty": {"name": "Empty", "label": "Empty", "items": [
        {"type": "Link", "link_type": "Workspace", "link_to": "Empty", "label": "Home"},
        {"type": "Section Break", "label": "Nothing"},
    ]},
}


class MenuTests(unittest.TestCase):
    def test_keeps_doctype_links_under_their_section(self):
        menus = api.menus_from_sidebars(SIDEBARS)
        self.assertEqual([m["label"] for m in menus], ["Accounts", "Payroll"])  # sorted, "Empty" dropped
        payroll = menus[1]["items"]
        self.assertEqual(payroll, [{"type": "section", "label": "Setup"},
                                   {"type": "doctype", "label": "Salary Slip", "doctype": "Salary Slip"}])

    def test_label_falls_back_to_doctype(self):
        accounts = api.menus_from_sidebars(SIDEBARS)[0]
        self.assertEqual(accounts["items"][0]["label"], "Payment Entry")

    def test_bootstrap_uses_the_session_user_and_frappe_sidebars(self):
        boot.get_module_sidebars = lambda: SIDEBARS
        frappe.session.user = "Administrator"  # role filtering itself is covered in test_access.py
        result = api.bootstrap()
        self.assertEqual(result["user"], {"email": "Administrator", "full_name": "User A"})
        self.assertEqual(result["roles"], ["Desk User", "Accounts User"])
        self.assertEqual(len(result["menus"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
