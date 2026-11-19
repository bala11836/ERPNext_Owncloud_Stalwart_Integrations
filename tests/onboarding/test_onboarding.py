"""Run: python test_onboarding.py  (no Frappe needed). Gatekeeping rules of erpnext_drive_integrations.onboarding.vendor (ADR-039)."""
import pathlib
import sys
import types
import unittest


class Throw(Exception):
    pass


def throw(msg, exc=None):
    raise Throw(msg)


frappe = types.ModuleType("frappe")
frappe.whitelist = lambda **kw: (lambda f: f)
frappe._ = lambda s: s
frappe.throw = throw
frappe.PermissionError = Throw
frappe.parse_json = lambda s: __import__("json").loads(s)
utils = types.ModuleType("frappe.utils")
for name in ("add_days", "escape_html", "format_datetime", "get_datetime", "now_datetime", "get_url"):
    setattr(utils, name, lambda *a, **k: None)
utils.cint = int
frappe.utils = utils
rate = types.ModuleType("frappe.rate_limiter")
rate.rate_limit = lambda **kw: (lambda f: f)
sys.modules.update({"frappe": frappe, "frappe.utils": utils, "frappe.rate_limiter": rate,
                    "requests": types.ModuleType("requests")})
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from erpnext_drive_integrations.onboarding import vendor as onboarding  # noqa: E402


class Doc(types.SimpleNamespace):
    def get(self, k, default=None):
        return getattr(self, k, default)

    def set(self, k, v):
        setattr(self, k, v)

    def append(self, table, row):
        getattr(self, table).append(types.SimpleNamespace(**row))

    def check_permission(self, right):
        pass


def make_doc(**kw):
    base = {f: "" for f in onboarding.VENDOR_FIELDS}
    base.update({f: None for f in onboarding.GST_FACTS})
    base.update(name="VOB-1", persons=[], documents=[], status="Sent", from_gst=0, bank_name="SBI", bank_branch="X",
                ifsc="SBIN0001234", gstin="")
    base.update(kw)
    return Doc(**base)


class Gatekeeping(unittest.TestCase):
    def test_vendor_cannot_write_gst_facts_or_unknown_fields(self):
        doc = make_doc()
        onboarding._apply(doc, {"business_name": "Ravi", "gst_status": "Active", "gst_checked_on": "now",
                                "supplier": "SUP-9", "status": "Approved"}, None)
        self.assertEqual(doc.business_name, "Ravi")
        self.assertIsNone(doc.gst_status)
        self.assertIsNone(doc.gst_checked_on)
        self.assertEqual(doc.status, "Sent")
        self.assertFalse(hasattr(doc, "supplier"))

    def test_gst_address_is_locked_and_changes_clear_old_facts(self):
        doc = make_doc(from_gst=1, city="Khammam", gstin="36AAAFR1234K1Z5", gst_status="Active")
        onboarding._apply(doc, {"city": "Elsewhere", "gstin": "36AAAFR1234K1Z5"}, None)
        self.assertEqual(doc.city, "Khammam")  # GST-locked
        onboarding._apply(doc, {"gstin": "27AAPFU0939F1ZV"}, None)  # different GSTIN -> old GST facts dropped
        self.assertIsNone(doc.gst_status)
        self.assertIsNone(doc.from_gst)
        onboarding._apply(doc, {"ifsc": "HDFC0001234"}, None)  # new IFSC -> bank name must be looked up again
        self.assertIsNone(doc.bank_name)

    def test_persons_are_sanitised(self):
        doc = make_doc()
        onboarding._apply(doc, {}, [{"person_name": " Ravi ", "is_principal": "yes", "email_verified_on": "2026-01-01",
                                     "director_check": "Director"}] * 15)
        self.assertEqual(len(doc.persons), 10)  # capped
        p = doc.persons[0]
        self.assertEqual((p.person_name, p.is_principal), ("Ravi", 1))
        self.assertFalse(hasattr(p, "email_verified_on"))  # vendor can't mark themselves verified
        self.assertFalse(hasattr(p, "director_check"))

    def test_file_type_is_checked_by_content(self):
        self.assertTrue(onboarding.file_ok("gst.pdf", b"%PDF-1.7 ..."))
        self.assertTrue(onboarding.file_ok("cheque.JPG", b"\xff\xd8\xff\xe0..."))
        self.assertFalse(onboarding.file_ok("cheque.jpg", b"%PDF-1.7"))  # name says jpg, content is not
        self.assertFalse(onboarding.file_ok("evil.html", b"<html>"))
        self.assertFalse(onboarding.file_ok("noext", b"%PDF"))

    def test_nothing_is_approved_before_the_vendor_submits(self):
        onboarding._staff_doc = lambda name, right="write": make_doc(status="Sent", owner="buyer")
        onboarding.check_role = lambda *a, **k: None
        onboarding.check_different_approver = lambda *a, **k: None
        with self.assertRaises(Throw):
            onboarding.approve("VOB-1")

    def test_link_is_created_only_once(self):
        onboarding._staff_doc = lambda name, right="write": make_doc(status="Sent", response_request="RSP-1")
        onboarding.check_role = lambda *a, **k: None
        with self.assertRaises(Throw) as e:
            onboarding.send("VOB-1")
        self.assertIn("already created once", str(e.exception))

    def test_staff_draft_is_filled_automatically(self):
        cache = {}
        onboarding.frappe.cache = types.SimpleNamespace(get_value=cache.get, set_value=lambda k, v, **kw: cache.__setitem__(k, v))
        onboarding.frappe.clear_last_message = lambda: None
        onboarding.now_datetime = lambda: "now"
        onboarding.ifsc_details = lambda ifsc: {"bank_name": "HDFC Bank", "bank_branch": "Khammam"} if ifsc == "HDFC0001234" else None
        calls = []
        onboarding.gst_info = lambda g: calls.append(g) or ({"gstin": g, "legal_name": "RAVI TRADERS", "status": "Active",
                                                             "permanent_address": {"city": "Khammam"}} if g == "27AAPFU0939F1ZV" else None)
        doc = make_doc(status="Draft", ifsc="HDFC0001234", bank_name="typed by hand", gstin="27AAPFU0939F1ZV", no_gst=0, pan="")
        self.assertEqual(onboarding.auto_fill(doc, None), [])
        self.assertEqual((doc.bank_name, doc.gst_legal_name, doc.city, doc.from_gst, doc.pan),
                         ("HDFC Bank", "RAVI TRADERS", "Khammam", 1, "AAPFU0939F"))
        before = make_doc(**vars(doc))
        self.assertEqual(onboarding.auto_fill(doc, before), [])  # nothing changed: no second paid lookup
        self.assertEqual(len(calls), 1)
        doc.ifsc, doc.gstin = "SBIN0009999", "36ABCDE1234F1Z5"  # unknown IFSC, GSTIN with a wrong check digit
        notes = onboarding.auto_fill(doc, before)
        self.assertEqual(len(notes), 2)
        self.assertEqual((doc.bank_name, doc.gst_status, doc.from_gst, len(calls)), (None, None, None, 1))
        doc.no_gst = 1  # "no GST": facts stay empty and nothing is looked up
        self.assertEqual(len(onboarding.auto_fill(doc, before)), 1)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
