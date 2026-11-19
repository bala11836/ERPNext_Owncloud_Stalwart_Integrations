"""P38: an app blocked on production gets its OAuth redirect URIs back on test."""
import os
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
STORE = {}
frappe = types.ModuleType('frappe')
frappe.conf = {}
frappe.get_all = lambda doctype, filters=None, pluck=None: [n for n, v in STORE.items() if v['app_name'] == filters['app_name']]
frappe.db = types.SimpleNamespace(set_value=lambda doctype, name, values: STORE[name].update(values))
sys.modules['frappe'] = frappe
sys.path.insert(0, str(ROOT))
from erpnext_drive_integrations.operations import bootstrap  # noqa: E402

BLOCKED = 'urn:blocked:production-test-only-app'


class TestOAuthClients(unittest.TestCase):
    def setUp(self):
        STORE.clear()
        STORE['c1'] = {'app_name': 'Mobile', 'redirect_uris': BLOCKED, 'default_redirect_uri': BLOCKED}
        STORE['c2'] = {'app_name': 'Other', 'redirect_uris': BLOCKED, 'default_redirect_uri': BLOCKED}
        os.environ['CLOUD_DEPLOYMENT_TIER'] = 'test'
        frappe.conf = {'cloud_test_copy': True}

    def test_restores_only_the_named_app(self):
        out = bootstrap.restore_test_oauth_clients([{'app_name': 'Mobile', 'redirect_uris': 'app://cb exp://x/cb',
                                                     'default_redirect_uri': 'app://cb'}])
        self.assertEqual(out, ['Mobile'])
        self.assertEqual(STORE['c1']['redirect_uris'], 'app://cb exp://x/cb')
        self.assertEqual(STORE['c1']['default_redirect_uri'], 'app://cb')
        self.assertEqual(STORE['c2']['redirect_uris'], BLOCKED)

    def test_refuses_outside_a_marked_test_copy(self):
        frappe.conf = {}
        with self.assertRaises(RuntimeError):
            bootstrap.restore_test_oauth_clients([])
        frappe.conf = {'cloud_test_copy': True}
        os.environ['CLOUD_DEPLOYMENT_TIER'] = 'production'
        with self.assertRaises(RuntimeError):
            bootstrap.restore_test_oauth_clients([])

    def test_default_must_be_one_of_the_uris(self):
        with self.assertRaises(ValueError):
            bootstrap.restore_test_oauth_clients([{'app_name': 'Mobile', 'redirect_uris': 'app://cb',
                                                   'default_redirect_uri': 'evil://x'}])

    def tearDown(self):
        os.environ.pop('CLOUD_DEPLOYMENT_TIER', None)


if __name__ == '__main__':
    unittest.main(verbosity=2)
