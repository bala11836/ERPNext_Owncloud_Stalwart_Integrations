"""Run: python test_kyc.py  (pure rules, no Frappe needed)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from erpnext_drive_integrations.onboarding import kyc  # noqa: E402


def gstin_for(pan, state="36"):
    first14 = f"{state}{pan}1Z"
    return first14 + kyc.gstin_check_digit(first14)


GOOD = {"business_name": "Ravi Steels", "constitution": "Partnership", "pan": "AAAFR1234K",
        "address_line1": "Plot 4, IDA", "city": "Khammam", "state": "Telangana", "pincode": "507001",
        "ifsc": "SBIN0001234", "bank_account_no": "123456789012", "account_holder_name": "Ravi Steels"}
PERSON = {"person_name": "Ravi Kumar", "email": "ravi@example.com", "mobile": "90000 12345", "is_principal": 1}


def errors(problems):
    return [m for level, m in problems if level == kyc.ERROR]


class Rules(unittest.TestCase):
    def test_known_gstin_check_digit(self):
        self.assertIsNone(kyc.gstin_problem("27AAPFU0939F1ZV"))  # widely published sample GSTIN
        self.assertIn("check digit", kyc.gstin_problem("27AAPFU0939F1ZA"))
        self.assertIn("format", kyc.gstin_problem("27AAPFU0939F1Z"))

    def test_pan_rules(self):
        self.assertEqual(kyc.pan_problems("aaafr 1234k", "Partnership"), [])
        self.assertIn("format", kyc.pan_problems("AAAF1234K", "Partnership")[0])
        self.assertIn("type letter", kyc.pan_problems("AAACR1234K", "Proprietorship")[0])
        self.assertEqual(kyc.pan_problems("AAAAT1234K", "Trust / Society"), [])
        self.assertEqual(kyc.pan_problems("AAAFR1234K", "LLP"), [])

    def test_pan_must_match_gstin(self):
        self.assertEqual(kyc.pan_problems("AAAFR1234K", "Partnership", gstin_for("AAAFR1234K")), [])
        self.assertIn("inside the GSTIN", kyc.pan_problems("AAAFR9999K", "Partnership", gstin_for("AAAFR1234K"))[0])

    def test_ifsc_and_mobile(self):
        self.assertIsNone(kyc.ifsc_problem("sbin0001234"))
        self.assertIsNotNone(kyc.ifsc_problem("SBIN1001234"))  # 5th character must be 0
        self.assertEqual(kyc.norm_mobile("+91 90000-12345"), "+919000012345")
        self.assertEqual(kyc.norm_mobile("09000012345"), "+919000012345")
        self.assertEqual(kyc.norm_mobile("12345"), "")
        self.assertEqual(kyc.norm_mobile("5848012345"), "")  # Indian mobiles start 6-9
        self.assertEqual(kyc.parse_ifsc({"BANK": "State Bank of India", "BRANCH": "KHAMMAM", "MICR": "507002002"})["bank_name"],
                         "State Bank of India")

    def test_masks(self):
        self.assertEqual(kyc.mask_email("ravi@example.com"), "r***@example.com")
        self.assertEqual(kyc.mask_mobile("+919000012345"), "••••••2345")

    def test_good_vendor_has_no_errors(self):
        data = dict(GOOD, gstin=gstin_for(GOOD["pan"]), gst_checked_on="2026-11-09", gst_status="Active",
                    gst_legal_name="RAVI STEELS")
        self.assertEqual(kyc.vendor_problems(data, [PERSON], account_confirm="1234 5678 9012"), [])

    def test_vendor_without_gst(self):
        data = dict(GOOD, no_gst=1)
        self.assertEqual(errors(kyc.vendor_problems(data, [PERSON])), [])
        self.assertTrue(errors(kyc.vendor_problems(dict(data, gstin=gstin_for(GOOD["pan"])), [PERSON])))

    def test_blocking_errors(self):
        data = dict(GOOD, gstin=gstin_for("AAAFR9999K"))
        errs = errors(kyc.vendor_problems(data, [PERSON], account_confirm="999"))
        self.assertTrue(any("inside the GSTIN" in e for e in errs))
        self.assertTrue(any("re-typed" in e for e in errs))
        # exactly one principal contact, with email + mobile
        self.assertTrue(errors(kyc.vendor_problems(dict(GOOD, no_gst=1), [dict(PERSON, is_principal=0)])))
        two = [PERSON, dict(PERSON, person_name="Second")]
        self.assertTrue(any("exactly one" in e for e in errors(kyc.vendor_problems(dict(GOOD, no_gst=1), two))))
        self.assertTrue(errors(kyc.vendor_problems(dict(GOOD, no_gst=1), [dict(PERSON, email="")])))

    def test_warnings_for_staff(self):
        data = dict(GOOD, gstin=gstin_for(GOOD["pan"]), gst_checked_on="x", gst_status="Cancelled",
                    gst_legal_name="SOMEONE ELSE TRADERS")
        warns = [m for level, m in kyc.vendor_problems(data, [PERSON]) if level == kyc.WARN]
        self.assertTrue(any("Cancelled" in w for w in warns))
        self.assertTrue(any("differs" in w for w in warns))
        self.assertTrue(kyc.name_matches("M/s Ravi Steels Pvt. Ltd.", "RAVI STEELS PRIVATE LIMITED"))

    def test_mapping(self):
        ob = dict(GOOD, name="VOB-1", gstin=gstin_for(GOOD["pan"]), gst_category="Registered Regular", constitution="LLP")
        sup = kyc.supplier_doc(ob)
        self.assertEqual((sup["supplier_type"], sup["hov_constitution"], sup["pan"]), ("Partnership", "LLP", "AAAFR1234K"))
        addr = kyc.address_doc(ob, "SUP-1")
        self.assertEqual(addr["links"], [{"link_doctype": "Supplier", "link_name": "SUP-1"}])
        contact = kyc.contact_doc(PERSON, "SUP-1")
        self.assertEqual((contact["first_name"], contact["last_name"], contact["is_primary_contact"]), ("Ravi", "Kumar", 1))
        self.assertEqual(contact["phone_nos"], [{"phone": "+919000012345", "is_primary_mobile_no": 1}])
        bank = kyc.bank_account_doc(ob, "SUP-1", "State Bank of India")
        self.assertEqual((bank["party_type"], bank["branch_code"], bank["is_company_account"]), ("Supplier", "SBIN0001234", 0))

    def test_changed_fields(self):
        labels = {"bank_account_no": "Bank account no.", "city": "City"}
        self.assertEqual(kyc.changed_fields({"bank_account_no": "1", "city": "X"}, {"bank_account_no": "2", "city": "X"}, labels),
                         ["Bank account no."])

    def test_amendment_rules(self):
        self.assertEqual(kyc.amendment_problems([{"field": "Bank IFSC", "new_value": "HDFC0001234"}]), [])
        self.assertTrue(kyc.amendment_problems([{"field": "Supplier group", "new_value": "x"}]))
        self.assertTrue(kyc.amendment_problems([{"field": "Bank IFSC", "new_value": "BAD"}]))
        self.assertTrue(kyc.amendment_problems([{"field": "City", "new_value": "A"}, {"field": "City", "new_value": "B"}]))
        self.assertIn("Bank IFSC", kyc.BANK_LABELS)

    def test_contact_change_drops_verification(self):  # audit HOV-01
        self.assertFalse(kyc.changed("Ravi@Example.in ", "ravi@example.in"))
        self.assertTrue(kyc.changed("ravi@example.in", "staff@example.com"))
        self.assertTrue(kyc.changed("ravi@example.in", None))


if __name__ == "__main__":
    unittest.main()
