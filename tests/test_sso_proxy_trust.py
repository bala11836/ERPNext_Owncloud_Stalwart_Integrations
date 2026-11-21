"""P65: forwarded headers are trusted on the SSO host's private entry point from the bridge sources only."""
from pathlib import Path
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_auth_bridge import forwarded_trust  # noqa: E402
from sso_proxy_trust import apply  # noqa: E402

COMPOSE = yaml.safe_dump({'services': {'traefik': {'command': [
    '--entrypoints.http.address=:80', '--entrypoints.https.address=:443', '--entrypoints.private.address=:444',
    '--providers.file.directory=/traefik/dynamic/']}}})


def command(text):
    return yaml.safe_load(text)['services']['traefik']['command']


class SsoProxyTrustTests(unittest.TestCase):
    def test_adds_exact_trust_to_the_private_entry_point_only(self):
        out = command(apply(COMPOSE, 'private', ['100.64.0.20']))
        self.assertIn('--entrypoints.private.forwardedheaders.trustedips=100.64.0.20/32', out)
        self.assertFalse(any('https.forwardedheaders' in c for c in out))
        self.assertEqual([c for c in command(COMPOSE)], [c for c in out if 'trustedips' not in c])

    def test_replaces_an_earlier_value_and_can_remove_it(self):
        once = apply(COMPOSE, 'private', ['100.64.0.20', '100.64.0.21'])
        again = command(apply(once, 'private', ['100.64.0.20']))
        self.assertEqual([c for c in again if 'trustedips' in c], ['--entrypoints.private.forwardedheaders.trustedips=100.64.0.20/32'])
        self.assertFalse(any('trustedips' in c for c in command(apply(once, 'private', []))))

    def test_refuses_public_entry_points_undefined_ones_and_ranges(self):
        for entry in ('https', 'http', 'websecure'):
            with self.assertRaises(ValueError):
                apply(COMPOSE, entry, ['100.64.0.20'])
        with self.assertRaises(ValueError):
            apply(COMPOSE, 'other', ['100.64.0.20'])
        with self.assertRaises(ValueError):
            apply(COMPOSE, 'private', ['100.64.0.0/24'])

    def test_bridge_profile_gives_the_entry_point_and_its_exact_sources(self):
        profile = {'auth_bridge_private': {'entrypoint': 'private', 'sources': ['100.64.0.20']}}
        self.assertEqual(forwarded_trust(profile), ('private', ['100.64.0.20/32']))
        self.assertIsNone(forwarded_trust({}))
        with self.assertRaises(ValueError):
            forwarded_trust({'auth_bridge_private': {'entrypoint': 'https', 'sources': ['100.64.0.20']}})


if __name__ == '__main__':
    unittest.main()
