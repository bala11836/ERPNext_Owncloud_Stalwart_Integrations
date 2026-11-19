"""Run: python test_schedule.py  (no Frappe needed; tiny fake `frappe`)."""
import pathlib
import sys
import types
import unittest

ROLES = {}
frappe = types.ModuleType("frappe")
frappe.whitelist = lambda **kw: (lambda f: f)
frappe._ = lambda s: s
frappe.session = types.SimpleNamespace(user="u")
frappe.get_roles = lambda user=None: ROLES.get(user or frappe.session.user, [])
frappe.PermissionError = type("PermissionError", (Exception,), {})
frappe.has_permission = lambda *a, **k: True


def throw(msg, exc=Exception):
    raise exc(msg)


frappe.throw = throw
sys.modules["frappe"] = frappe
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from erpnext_drive_integrations.onboarding import schedule  # noqa: E402


def t(name, start, end, deps=()):
    return {"name": name, "start": start, "end": end, "deps": list(deps)}


class CriticalPathTests(unittest.TestCase):
    def test_longest_chain_is_critical(self):
        # A(3d) -> B(5d) -> D(2d) is the longest chain; C(2d) after A has slack.
        tasks = [t("A", "2026-11-01", "2026-11-03"), t("B", "2026-11-04", "2026-11-08", ["A"]),
                 t("C", "2026-11-04", "2026-11-05", ["A"]), t("D", "2026-11-09", "2026-11-10", ["B", "C"])]
        self.assertEqual(sorted(schedule.critical_path(tasks)), ["A", "B", "D"])

    def test_tasks_without_dates_and_unknown_deps_are_ignored(self):
        tasks = [t("A", "2026-11-01", "2026-11-02", ["ghost"]), t("X", None, None, ["A"])]
        self.assertEqual(schedule.critical_path(tasks), ["A"])

    def test_dependency_loop_returns_nothing_instead_of_failing(self):
        tasks = [t("A", "2026-11-01", "2026-11-02", ["B"]), t("B", "2026-11-03", "2026-11-04", ["A"])]
        self.assertEqual(schedule.critical_path(tasks), [])


class EditRuleTests(unittest.TestCase):
    def test_only_projects_manager_and_coordinator_may_edit(self):
        ROLES.update({"pm": ["Projects Manager"], "pc": ["Project Coordinator"], "user": ["Projects User"],
                      "sysman": ["System Manager"]})
        self.assertTrue(schedule.can_edit_dates("pm"))
        self.assertTrue(schedule.can_edit_dates("pc"))
        self.assertFalse(schedule.can_edit_dates("user"))
        self.assertFalse(schedule.can_edit_dates("sysman"))  # MD: PM and PC only

    def test_update_refused_for_others_and_bad_dates(self):
        frappe.session.user = "user"
        with self.assertRaises(frappe.PermissionError):
            schedule.update_dates("T1", "2026-11-01", "2026-11-02")
        frappe.session.user = "pm"
        with self.assertRaises(Exception):
            schedule.update_dates("T1", "2026-11-05", "2026-11-02")


if __name__ == "__main__":
    unittest.main(verbosity=2)
