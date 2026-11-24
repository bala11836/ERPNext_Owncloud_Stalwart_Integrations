"""Prove the test request boundary without Docker, SSH, or a live Frappe site."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest


class Denied(Exception):
    pass


frappe = types.SimpleNamespace(conf={}, session=types.SimpleNamespace(user='admin@example.com'),
    request=types.SimpleNamespace(url='https://test.example.com/api/method/refresh', method='POST'),
    whitelist=lambda **kw: lambda f: f, get_roles=lambda: ['System Manager'],
    PermissionError=Denied, ValidationError=Denied)
frappe.throw = lambda message, kind: (_ for _ in ()).throw(kind(message))
sys.modules['frappe'] = frappe
path = Path(__file__).resolve().parents[1] / 'erpnext_drive_integrations/portal/test_refresh.py'
spec = importlib.util.spec_from_file_location('test_refresh_boundary_module', path)
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


class RefreshBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        refresh.STATE_ROOT = Path(self.temp.name)
        frappe.conf = {'cloud_test_copy': True, 'cloud_test_refresh_enabled': True,
                       'cloud_test_refresh_users':['admin@example.com'],
                       'host_name': 'https://test.example.com'}
        frappe.session.user = 'admin@example.com'
        frappe.request.url = 'https://test.example.com/api/method/refresh'
        frappe.request.method = 'POST'
        frappe.get_roles = lambda: ['System Manager']
        self.old_tier = os.environ.get('CLOUD_DEPLOYMENT_TIER')
        os.environ['CLOUD_DEPLOYMENT_TIER'] = 'test'

    def tearDown(self):
        self.temp.cleanup()
        if self.old_tier is None:
            os.environ.pop('CLOUD_DEPLOYMENT_TIER', None)
        else:
            os.environ['CLOUD_DEPLOYMENT_TIER'] = self.old_tier

    def test_restored_database_cannot_enable_production(self):
        os.environ['CLOUD_DEPLOYMENT_TIER'] = 'production'
        with self.assertRaises(Denied):
            refresh.request_refresh()

    def test_unlisted_system_manager_cannot_trigger_production_snapshot(self):
        frappe.session.user='another-manager@example.com'
        with self.assertRaises(Denied):
            refresh.request_refresh()
        self.assertFalse((refresh.STATE_ROOT / 'request.json').exists())

    def test_host_role_and_method_are_enforced(self):
        for attr, value in [('url', 'https://erp.example.com/api/method/refresh'), ('method', 'GET')]:
            previous = getattr(frappe.request, attr)
            setattr(frappe.request, attr, value)
            with self.assertRaises(Denied):
                refresh.request_refresh()
            setattr(frappe.request, attr, previous)
        frappe.get_roles = lambda: ['Desk User']
        with self.assertRaises(Denied):
            refresh.request_refresh()

    def test_one_complete_request_without_commands_or_destinations(self):
        reply = refresh.request_refresh()
        request = json.loads((refresh.STATE_ROOT / 'request.json').read_text())
        self.assertEqual(reply['request_id'], request['request_id'])
        self.assertEqual(set(request), {'request_id', 'actor', 'requested_at', 'kind'})
        self.assertEqual(request['kind'], 'data')
        with self.assertRaises(Denied):
            refresh.request_refresh()
        self.assertEqual(request, json.loads((refresh.STATE_ROOT / 'request.json').read_text()))

    def test_retired_code_refresh_cannot_queue_work(self):
        for bad in ['code', 'branch', '']:
            with self.assertRaises(Denied):
                refresh.request_refresh(kind=bad)
        self.assertFalse((refresh.STATE_ROOT / 'request.json').exists())

    def test_legacy_code_status_keeps_the_last_data_refresh_timestamp(self):
        stamp = '2026-11-15T00:00:00+00:00'
        (refresh.STATE_ROOT / 'status.json').write_text(json.dumps({
            'phase': 'updating-code', 'kind': 'code', 'revision': 'abc1234',
            'last_successful_at': stamp,
        }))
        (refresh.STATE_ROOT / 'request.json').write_text(json.dumps({
            'kind': 'code', 'request_id': 'legacy', 'requested_at': stamp,
        }))
        result = refresh.status()
        self.assertEqual((result['phase'], result['kind']), ('idle', 'data'))
        self.assertEqual(result['last_successful_at'], stamp)
        self.assertNotIn('revision', result)

    def test_status_excludes_private_details_and_keeps_success_time(self):
        stamp = '2026-11-15T00:00:00+00:00'
        (refresh.STATE_ROOT / 'status.json').write_text(json.dumps({'phase': 'failed',
            'last_successful_at': stamp, 'actor': 'private@example.com', 'error': 'private log'}))
        result = refresh.status()
        self.assertEqual(result['last_successful_at'], stamp)
        self.assertNotIn('actor', result)
        self.assertNotIn('error', result)

    def test_symlink_status_is_rejected(self):
        target = refresh.STATE_ROOT / 'private.json'
        target.write_text('{"secret":"not public"}')
        (refresh.STATE_ROOT / 'status.json').symlink_to(target)
        with self.assertRaises(RuntimeError):
            refresh.status()


if __name__ == '__main__':
    unittest.main()
