"""The app header leads back to the portal home through the logo; it has no "All apps" item.

A sub-menu opened in a new tab has no history, so the browser's back swipe
cannot return to the app menu; the header's logo must. The owner removed the
"All apps" sidebar item from ERPNext, HRMS, Onboarding and India Compliance;
it came back once when the repository build replaced the hand-patched files,
so this test fails if it ever reappears.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEADER = (ROOT / 'erpnext_drive_integrations/public/module-header-20261115.js').read_text()
HOOKS = (ROOT / 'erpnext_drive_integrations/portal/hooks.py').read_text()


class AppMenuLinkTests(unittest.TestCase):
    def test_logo_links_to_the_portal_home_in_the_whole_tab(self):
        self.assertIn("home.href='/place_holder'", HEADER)
        self.assertIn("home.append(image)", HEADER)
        # Inside the portal frame the link must replace the whole tab.
        self.assertIn("home.target='_top'", HEADER)

    def test_there_is_no_all_apps_item(self):
        self.assertNotIn('All apps', HEADER)
        self.assertNotIn("className='uf-all-apps'", HEADER)
        self.assertNotIn("apps.href", HEADER)
        # ... and a copy left in an already open tab is removed.
        self.assertEqual(HEADER.count('uf-all-apps'), 1)
        self.assertIn(".querySelectorAll('.uf-all-apps').forEach(item=>item.remove())", HEADER)

    def test_other_fixed_actions_and_the_hidden_native_home_item_stay(self):
        self.assertIn('Edit Sidebar', HEADER)
        self.assertIn("help.className='uf-help'", HEADER)
        self.assertIn("'uf-hide-home'", HEADER)

    def test_browsers_get_the_new_script_version(self):
        self.assertIn("module-header-20261115.js?v=5", HOOKS)


if __name__ == '__main__':
    unittest.main(verbosity=2)
