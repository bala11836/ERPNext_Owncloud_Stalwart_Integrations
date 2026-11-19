"""The app header always offers a way back to the app menu (portal home).

A sub-menu opened in a new tab has no history, so the browser's back swipe
cannot return to the app menu; the header's logo and "All apps" link must.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEADER = (ROOT / 'erpnext_drive_integrations/public/module-header-20261115.js').read_text()


class AppMenuLinkTests(unittest.TestCase):
    def test_logo_and_all_apps_link_to_the_app_menu(self):
        self.assertIn("home.href='/'", HEADER)
        self.assertIn("home.append(image)", HEADER)
        self.assertIn("apps.href='/'", HEADER)
        self.assertIn('All apps', HEADER)
        # Inside the portal frame the links must replace the whole tab.
        self.assertIn("home.target='_top'", HEADER)
        self.assertIn("apps.target='_top'", HEADER)


if __name__ == '__main__':
    unittest.main(verbosity=2)
