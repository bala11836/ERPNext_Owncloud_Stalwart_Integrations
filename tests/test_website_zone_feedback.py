"""Employee Zone gives instant feedback on the first click and ignores repeat clicks (P58).

On the test site the sign-in hops take about three seconds; the page did not change,
people clicked again and the second click cancelled the first request.
"""
from pathlib import Path
import unittest

PAGE = (Path(__file__).resolve().parents[1] / "integrations/website/site/index.html").read_text()


class ZoneFeedbackTests(unittest.TestCase):
    def test_first_click_marks_the_link_busy(self):
        self.assertIn("zone.classList.add('opening'); zone.setAttribute('aria-busy', 'true');", PAGE)
        self.assertIn(".zone.opening {", PAGE)

    def test_repeat_clicks_do_not_cancel_the_navigation(self):
        self.assertIn("if (zone.classList.contains('opening')) { e.preventDefault(); return; }", PAGE)

    def test_modified_clicks_open_normally_and_back_button_resets(self):
        self.assertIn("e.ctrlKey || e.metaKey || e.shiftKey || e.altKey", PAGE)
        self.assertIn("ev.persisted", PAGE)

    def test_link_target_is_still_the_placeholder_token(self):
        self.assertIn('<a class="zone" href="__EMPLOYEE_ZONE_URL__">', PAGE)


if __name__ == "__main__":
    unittest.main()
