"""Run: python test_monitor.py  (no Frappe needed; tiny fake `frappe`)."""
import datetime
import pathlib
import sys
import types
import unittest

STATE = {}


def reset(errors=(), failed=0, cloud_ok=True, test_copy=False):
    STATE.update(errors=list(errors), failed=failed, cloud_ok=cloud_ok, cache={}, logs=[])
    frappe.conf = {"onboarding_test_copy": 1} if test_copy else {}


frappe = types.ModuleType("frappe")
frappe.get_all = lambda doctype, **kw: STATE["errors"] if doctype == "Error Log" else ["admin@x", "off@x", "Administrator"]
frappe.db = types.SimpleNamespace(count=lambda *a, **k: STATE["failed"], commit=lambda: None,
                                  get_value=lambda dt, name, field: name != "off@x")
frappe.cache = types.SimpleNamespace(get_value=lambda k: STATE["cache"].get(k),
                                     set_value=lambda k, v, expires_in_sec=None: STATE["cache"].__setitem__(k, v))


class Doc(dict):
    def insert(self, ignore_permissions=False):
        STATE["logs"].append(dict(self))


frappe.get_doc = lambda d: Doc(d)
utils = types.ModuleType("frappe.utils")
utils.add_to_date = lambda d, minutes=0: d + datetime.timedelta(minutes=minutes)
utils.now_datetime = datetime.datetime.now
utils.escape_html = lambda s: s.replace("<", "&lt;")
frappe.utils = utils
sys.modules.update({"frappe": frappe, "frappe.utils": utils})


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from erpnext_drive_integrations.onboarding import monitor  # noqa: E402
monitor.sender_problem = lambda: None if STATE["cloud_ok"] else "noreply SMTP unavailable"


class MonitorTests(unittest.TestCase):
    def test_all_healthy_no_alert(self):
        reset()
        monitor.check_mail()
        self.assertEqual(STATE["logs"], [])

    def test_smtp_down_alerts_enabled_admins_once(self):
        reset(cloud_ok=False)
        monitor.check_mail()
        self.assertEqual([l["for_user"] for l in STATE["logs"]], ["admin@x"])  # disabled + Administrator skipped
        self.assertIn("SMTP", STATE["logs"][0]["email_content"])
        monitor.check_mail()  # within 6 h: no second alert
        self.assertEqual(len(STATE["logs"]), 1)

    def test_error_log_and_failed_queue(self):
        reset(errors=["[Mail] SMTP unreachable (email.send_email)"], failed=2)
        problems = monitor.find_problems()
        self.assertEqual(len(problems), 2)
        self.assertIn("2 email(s) failed", problems[1])

    def test_silent_on_test_copy(self):
        reset(cloud_ok=False, test_copy=True)
        monitor.check_mail()
        self.assertEqual(STATE["logs"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
