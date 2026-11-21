"""The authentik sign-in card has rounded corners (owner request, 21 November 2026)."""
import json
from pathlib import Path
import unittest

CONFIG = json.loads((Path(__file__).resolve().parents[1] / "integrations/authentik/configuration.json").read_text())


def brand_css(node):
    if isinstance(node, dict):
        if "branding_custom_css" in node:
            yield node["branding_custom_css"]
        for value in node.values():
            yield from brand_css(value)
    elif isinstance(node, list):
        for value in node:
            yield from brand_css(value)


class CardCornerTests(unittest.TestCase):
    def test_brand_css_rounds_the_login_card_and_keeps_the_logo_rule(self):
        found = list(brand_css(CONFIG))
        self.assertTrue(found)
        for css in found:
            self.assertIn(".pf-c-login__main { border-radius: 16px !important; overflow: hidden; }", css)
            self.assertIn(".pf-c-login__main-header .branding-logo", css)


if __name__ == "__main__":
    unittest.main()
