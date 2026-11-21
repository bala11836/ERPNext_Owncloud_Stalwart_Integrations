"""The portal's app menu turns into two vertical columns above five icons (P58)."""
from pathlib import Path
import re
import unittest

PAGE = (Path(__file__).resolve().parents[1] / 'erpnext_drive_integrations/www/place_holder.html').read_text()


class PortalMenuColumnTests(unittest.TestCase):
    def test_script_switches_on_more_than_five_icons(self):
        self.assertIn("nav.querySelectorAll(':scope > a[data-app-id]').length>5", PAGE)
        self.assertIn("nav.classList.add('ph-two-cols')", PAGE)

    def test_two_column_rule_fills_down_then_across(self):
        rule = re.search(r'#ph-sidebar\.ph-two-cols\{([^}]*)\}', PAGE).group(1)
        self.assertIn('column-count:2', rule)  # balanced, top to bottom, then the next column
        # The default (five or fewer icons) layout is untouched.
        self.assertIn('#ph-sidebar{position:fixed;left:10px;', PAGE)
        self.assertIn('width:84px;display:flex;flex-direction:column', PAGE)


if __name__ == '__main__':
    unittest.main()
