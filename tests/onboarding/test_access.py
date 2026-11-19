"""Run: python test_access.py  (no Frappe needed; tiny fake `frappe`)."""
import pathlib
import sys
import types
import unittest

ROLES = {}
TABLES = {
    "DocPerm": [
        {"parent": "Contact", "role": "All", "read": 1, "permlevel": 0},
        {"parent": "Payment Entry", "role": "Accounts User", "read": 1, "permlevel": 0},
        {"parent": "Payment Entry", "role": "Accounts User", "read": 1, "permlevel": 1},
        {"parent": "Employee", "role": "HR User", "read": 1, "permlevel": 0},
        {"parent": "Item", "role": "Stock User", "read": 1, "permlevel": 0},
    ],
    # Item has custom permissions, so its standard DocPerm rows no longer apply.
    "Custom DocPerm": [{"parent": "Item", "role": "Purchase User", "read": 1, "permlevel": 0}],
    "Has Role": [
        {"parent": "field-attendance", "parenttype": "Page", "role": "Field Supervisor"},
        {"parent": "Accounts Payable", "parenttype": "Report", "role": "Accounts Manager"},
    ],
}
REPORT_DOCTYPE = {"Accounts Payable": "Payment Entry", "Payment Summary": "Payment Entry"}


def get_all(doctype, filters=None, fields=None, pluck=None, distinct=False):
    rows = TABLES[doctype]
    for key, cond in (filters or {}).items():
        if isinstance(cond, list) and cond[0] == "in":
            rows = [r for r in rows if r[key] in cond[1]]
        else:
            rows = [r for r in rows if r[key] == cond]
    if pluck:
        values = [r[pluck] for r in rows]
        return list(dict.fromkeys(values)) if distinct else values
    return [types.SimpleNamespace(**r) for r in rows]


frappe = types.ModuleType("frappe")
frappe.whitelist = lambda **kw: (lambda f: f)
frappe.session = types.SimpleNamespace(user="u")
frappe.get_roles = lambda user=None: ROLES[user or frappe.session.user]
frappe.get_all = get_all
frappe.db = types.SimpleNamespace(get_value=lambda dt, name, field: REPORT_DOCTYPE.get(name))
frappe.get_hooks = lambda hook, app_name=None: [{"route": "/desk/hr"}] if hook == "add_to_apps_screen" else []
frappe.utils = types.SimpleNamespace(get_fullname=lambda u: u)
dock_mod = types.ModuleType("frappe.desk.doctype.dock.dock")
dock_mod.get_app_entry_set = lambda app: [{"link_type": "Sidebar", "link_to": "Shift & Attendance"},
                                          {"link_type": "Sidebar", "link_to": "Payroll"}]
boot_mod = types.ModuleType("frappe.boot")
for name in ["frappe.desk", "frappe.desk.doctype", "frappe.desk.doctype.dock"]:
    sys.modules[name] = types.ModuleType(name)
sys.modules.update({"frappe": frappe, "frappe.boot": boot_mod, "frappe.desk.doctype.dock.dock": dock_mod})
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from erpnext_drive_integrations.onboarding import access, api  # noqa: E402


def link(kind, to, label=None):
    return {"type": "Link", "link_type": kind, "link_to": to, "label": label or to}


HOME = {"type": "Link", "link_type": "Workspace", "link_to": "X", "label": "Home"}
SIDEBARS = {
    "Accounts": {"name": "Accounts", "label": "Accounts", "app": "erpnext", "items": [
        HOME, {"type": "Section Break", "label": "Payments"}, link("DocType", "Payment Entry"),
        {"type": "Section Break", "label": "Reports"}, link("Report", "Accounts Payable"), link("Report", "Payment Summary"),
        {"type": "Section Break", "label": "Everyone"}, link("DocType", "Contact")]},
    "Stock": {"name": "Stock", "label": "Stock", "app": "erpnext", "items": [HOME, link("DocType", "Item")]},
    "Shift & Attendance": {"name": "Shift & Attendance", "label": "Shift & Attendance", "app": "hrms",
                           "items": [HOME, link("URL", "/hr/roster", "Roster"), link("Page", "field-attendance", "Field Attendance"), link("DocType", "Employee")]},
    "Payroll": {"name": "Payroll", "label": "Payroll", "app": "hrms", "items": [HOME, link("DocType", "Employee")]},
}


def boot_for(user, roles, hr_visible=False):
    ROLES[user] = roles
    frappe.session.user = user
    bootinfo = types.SimpleNamespace()
    bootinfo.module_sidebars = {k: {**v, "items": list(v["items"])} for k, v in SIDEBARS.items()}
    bootinfo.dock = {"hrms": [{"link_type": "Sidebar", "link_to": "Payroll"}, {"link_type": "Sidebar", "link_to": "Shift & Attendance"}]}
    bootinfo.app_data = [
        {"app_name": "erpnext", "on_apps_screen": True, "dock": [{"link_type": "Sidebar", "link_to": "Accounts"}, {"link_type": "Sidebar", "link_to": "Stock"}]},
        {"app_name": "hrms", "on_apps_screen": hr_visible, "dock": []},
        {"app_name": "suite", "on_apps_screen": True, "dock": []},
    ]
    bootinfo.get = lambda key, default=None: getattr(bootinfo, key, default)
    access.boot_session(bootinfo)
    return bootinfo


def labels(items):
    return [i["label"] for i in items]


class RuleTests(unittest.TestCase):
    def test_everyone_grants_do_not_show_anything(self):
        b = boot_for("plain", ["All", "Desk User", "Guest"])
        self.assertTrue(all(not e["items"] for e in b.module_sidebars.values()))  # Contact (All) does not count
        self.assertFalse(next(a for a in b.app_data if a["app_name"] == "erpnext")["on_apps_screen"])
        self.assertTrue(next(a for a in b.app_data if a["app_name"] == "suite")["on_apps_screen"])  # not ruled here

    def test_accounts_user_sees_only_connected_items(self):
        b = boot_for("acc", ["All", "Accounts User"])
        self.assertEqual(labels(b.module_sidebars["Accounts"]["items"]),
                         ["Home", "Payments", "Payment Entry", "Reports", "Payment Summary"])  # role-listed report hidden
        self.assertEqual(b.module_sidebars["Stock"]["items"], [])
        erp = next(a for a in b.app_data if a["app_name"] == "erpnext")
        self.assertTrue(erp["on_apps_screen"])
        self.assertEqual([d["link_to"] for d in erp["dock"]], ["Accounts"])  # empty Stock module leaves the rail

    def test_report_with_its_own_roles(self):
        b = boot_for("mgr", ["Accounts Manager"])
        self.assertEqual(labels(b.module_sidebars["Accounts"]["items"]), ["Home", "Reports", "Accounts Payable"])

    def test_custom_permissions_replace_standard_ones(self):
        self.assertEqual(boot_for("st", ["Stock User"]).module_sidebars["Stock"]["items"], [])
        self.assertEqual(labels(boot_for("pu", ["Purchase User"]).module_sidebars["Stock"]["items"]), ["Home", "Item"])

    def test_field_supervisor_gets_hr_with_only_field_attendance(self):
        b = boot_for("sup", ["All", "Field Supervisor"], hr_visible=False)
        self.assertEqual(labels(b.module_sidebars["Shift & Attendance"]["items"]), ["Home", "Field Attendance"])
        hr = next(a for a in b.app_data if a["app_name"] == "hrms")
        self.assertTrue(hr["on_apps_screen"])  # reopened although HR's own check hid it
        self.assertEqual(hr["app_route"], "/desk/hr")
        self.assertEqual([d["link_to"] for d in hr["dock"]], ["Shift & Attendance"])
        self.assertEqual([d["link_to"] for d in b.dock["hrms"]], ["Shift & Attendance"])
        self.assertFalse(next(a for a in b.app_data if a["app_name"] == "erpnext")["on_apps_screen"])

    def test_administrator_untouched(self):
        b = boot_for("Administrator", ["Administrator"])
        self.assertEqual(b.module_sidebars["Stock"]["items"], SIDEBARS["Stock"]["items"])

    def test_mobile_bootstrap_uses_the_same_rule(self):
        ROLES["sup"] = ["All", "Field Supervisor", "HR User"]
        frappe.session.user = "sup"
        boot_mod.get_module_sidebars = lambda: {k: {**v, "items": list(v["items"])} for k, v in SIDEBARS.items()}
        menus = api.bootstrap()["menus"]
        self.assertEqual([m["label"] for m in menus], ["Payroll", "Shift & Attendance"])  # no Accounts (Contact only)


if __name__ == "__main__":
    unittest.main(verbosity=2)
