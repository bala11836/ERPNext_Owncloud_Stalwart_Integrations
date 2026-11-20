"""Every logout ends on the company website; a sign-in asks for the passkey once.

The landing address exists in exactly one place (sso.LANDING, rendered from the
private profile's landing_url, default https://www.<domain>/). Apps hand over to
the ERP's /login?logged_out=1 handler, which forwards there. These tests fail if
an app script names a final logout page of its own again, or if the sign-in goes
back to prompt=login with max_age=0 (which made authentik ask twice).
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from render_runtime import render  # noqa: E402

SSO = (ROOT / "erpnext_drive_integrations/portal/sso.py").read_text()
HANDOVER = "https://erp.example.com/login?logged_out=1"
APP_SCRIPTS = {
    "integrations/drive/workspace.js": r"OUT='([^']+)'",
    "integrations/dms/cloud_session/session.js": r"OUT='([^']+)'",
    "integrations/dms/cloud_session/middleware.py": r"OUT = '([^']+)'",
    "integrations/mail/overlay/lib/cloud-session.ts": r"SIGNED_OUT = '([^']+)'",
}


class LogoutLanding(unittest.TestCase):
    def test_the_landing_address_is_named_only_in_sso(self):
        self.assertIn('LANDING = "https://www.example.com/"', SSO)
        for path in list(APP_SCRIPTS) + ["erpnext_drive_integrations/public/session.js",
                                         "erpnext_drive_integrations/www/place_holder.html"]:
            text = (ROOT / path).read_text()
            self.assertNotIn("www.example.com", text, path)
            # Only hand-overs to the ERP (relative /signed-out finishes a still-valid
            # session first); never an absolute final page of its own.
            self.assertNotIn("example.com/signed-out", text, path)

    def test_every_app_hands_over_to_the_erp_logged_out_handler(self):
        for path, pattern in APP_SCRIPTS.items():
            found = re.search(pattern, (ROOT / path).read_text())
            self.assertIsNotNone(found, path)
            self.assertEqual(found.group(1), HANDOVER, path)

    def test_logged_out_and_signed_out_go_to_the_landing_address(self):
        self.assertIn('if path == "/login" and frappe.form_dict.get("logged_out"):\n        redirect(LANDING)', SSO)
        self.assertIn('redirect(FINISH)\n        redirect(LANDING)', SSO)
        self.assertNotIn('redirect("https://erp.example.com/signed-out")', SSO)
        # finish_logout still ends the gateway session (its flow then redirects to the website).
        self.assertIn('redirect("https://erp.example.com/outpost.goauthentik.io/sign_out")', SSO)

    def test_landing_address_comes_from_the_profile(self):
        build = render(ROOT, Path(tempfile.mkdtemp()) / "b", {"domain": "example.net", "landing_url": "https://test.example.net/"})
        self.assertIn('LANDING = "https://test.example.net/"', (build / "erpnext_drive_integrations/portal/sso.py").read_text())
        default = render(ROOT, Path(tempfile.mkdtemp()) / "b", {"domain": "example.net"})
        self.assertIn('LANDING = "https://www.example.net/"', (default / "erpnext_drive_integrations/portal/sso.py").read_text())
        with self.assertRaises(ValueError):
            render(ROOT, Path(tempfile.mkdtemp()) / "b", {"domain": "example.net", "landing_url": "javascript:alert(1)"})


class OnePasskeyPrompt(unittest.TestCase):
    def test_signin_does_not_force_an_immediate_second_prompt(self):
        start = SSO[SSO.index("def start_signin"):]
        start = start[:start.index("\n\n\n") if "\n\n\n" in start else len(start)]
        self.assertNotIn('"prompt": "login"', start)
        self.assertNotIn('"max_age": "0"', start)
        self.assertIn('query.update({"max_age": str(FRESH_WINDOW)})', start)
        self.assertIn('query.pop("prompt", None)', start)

    def test_freshness_window_is_ten_minutes_and_enforced_on_callback(self):
        self.assertIn("FRESH_WINDOW = 600", SSO)
        self.assertIn('< int(requested_at) - FRESH_WINDOW:', SSO)
        self.assertNotIn('< int(requested_at) - 5:', SSO)


if __name__ == "__main__":
    unittest.main()
