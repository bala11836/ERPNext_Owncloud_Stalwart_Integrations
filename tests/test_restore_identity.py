"""P44: the sign-in service is rebuilt from the repository stack with production's secrets."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import restore_identity as r  # noqa: E402

COMPOSE = """services:
  server:
    environment:
      AUTHENTIK_POSTGRESQL__PASSWORD: dbpassword123
      AUTHENTIK_SECRET_KEY: 'k3y-that-is-long-enough-for-authentik-0123456789'
      AUTHENTIK_EMAIL__PASSWORD: "mail-pass"
"""


class RestoreIdentityTests(unittest.TestCase):
    def test_secrets_are_read_from_the_backup_compose(self):
        found = r.secrets_from_compose(COMPOSE)
        self.assertEqual(found['CI_IDENTITY_SERVER_AUTHENTIK_SECRET_KEY'], 'k3y-that-is-long-enough-for-authentik-0123456789')
        self.assertEqual(found['CI_IDENTITY_POSTGRESQL_POSTGRES_PASSWORD'], 'dbpassword123')
        self.assertEqual(found['CI_IDENTITY_SERVER_AUTHENTIK_EMAIL__PASSWORD'], 'mail-pass')

    def test_missing_or_short_key_is_refused(self):
        with self.assertRaises(ValueError):
            r.secrets_from_compose(COMPOSE.replace('AUTHENTIK_SECRET_KEY', 'OTHER'))
        with self.assertRaises(ValueError):
            r.secrets_from_compose(COMPOSE.replace('k3y-that-is-long-enough-for-authentik-0123456789', 'short'))

    def test_settings_feed_the_repository_identity_stack(self):
        inputs = json.loads((ROOT / 'deployment/stacks/inputs.json').read_text())
        stack = (ROOT / 'deployment/stacks/identity.compose.json').read_text()
        for setting in r.SECRET_KEYS.values():
            self.assertEqual(inputs[setting]['kind'], 'secret')
            self.assertIn('${' + setting, stack)

    def test_reports_real_counts_and_never_prints_secrets(self):
        self.assertIn('exclude_anonymous', r.COUNTS)
        source = (ROOT / 'tools/restore_identity.py').read_text()
        self.assertNotIn('print(found', source)
        # A recovery host starts empty: pull the digest-pinned images if missing.
        self.assertNotIn("'--pull', 'never'", source)
        self.assertIn("'DROP DATABASE IF EXISTS authentik WITH (FORCE)", source.replace('b\'', "'"))


if __name__ == '__main__':
    unittest.main()
