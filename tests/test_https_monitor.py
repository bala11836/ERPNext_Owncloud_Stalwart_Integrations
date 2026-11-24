from io import BytesIO
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integrations/monitoring"))
from https_probe import check, NoRedirect


class ProbeTests(unittest.TestCase):
    target = {"name": "Document manager", "url": "https://docs.example.com/", "statuses": [302]}

    @patch("https_probe.build_opener")
    def test_only_configured_status_is_healthy(self, opener):
        for status, expected in ((302, True), (500, False)):
            opener.return_value.open.side_effect = HTTPError(self.target["url"], status, "", {}, BytesIO())
            self.assertEqual(check(self.target), ("Document manager", expected, f"HTTP {status}"))
        self.assertIsInstance(opener.call_args.args[0], NoRedirect)

    @patch("https_probe.build_opener")
    def test_connection_failure_suppresses_remote_error_details(self, opener):
        opener.return_value.open.side_effect = URLError("detail from remote connection")
        self.assertEqual(check(self.target), ("Document manager", False, "connection failed"))


if __name__ == "__main__":
    unittest.main()
