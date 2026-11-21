"""mobile-app module: the public source stays tenant-neutral and matches the server API.

The app's name, app ID, link scheme, ERP address and OAuth client ID belong to one deployment and
come from the private mobile/.env. These checks fail if a real value is written into the source.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / 'mobile'


class MobileAppTests(unittest.TestCase):
    def test_app_identity_defaults_are_neutral(self):
        expo = json.loads((MOBILE / 'app.json').read_text())['expo']
        self.assertEqual(expo['ios']['bundleIdentifier'], 'com.example.erp')
        self.assertEqual(expo['android']['package'], 'com.example.erp')
        self.assertEqual(expo['name'], 'ERP')

    def test_source_names_no_real_host(self):
        for path in list((MOBILE / 'src').rglob('*.ts*')) + [MOBILE / 'app.config.ts', MOBILE / '.env.example']:
            for host in re.findall(r'https?://([A-Za-z0-9.-]+)', path.read_text()):
                self.assertTrue(host.endswith('example.com'), f'{path.relative_to(ROOT)} names {host}')

    def test_oauth_client_id_is_not_built_in(self):
        session = (MOBILE / 'src/auth/session.tsx').read_text()
        self.assertIn("process.env.EXPO_PUBLIC_OAUTH_CLIENT_ID ?? ''", session)
        self.assertIn('EXPO_PUBLIC_OAUTH_CLIENT_ID=\n', (MOBILE / '.env.example').read_text())

    def test_bootstrap_path_matches_a_whitelisted_server_method(self):
        path = re.search(r"BOOT_PATH = '/api/method/([\w.]+)'", (MOBILE / 'src/lib/erp.ts').read_text()).group(1)
        module, func = path.rsplit('.', 1)
        source = (ROOT / (module.replace('.', '/') + '.py')).read_text()
        self.assertRegex(source, r'@frappe\.whitelist\([^)]*\)\s*\ndef ' + func + r'\(')

    def test_install_scripts_stay_blocked(self):
        settings = (MOBILE / 'pnpm-workspace.yaml').read_text()
        self.assertIn('onlyBuiltDependencies: []', settings)
        self.assertTrue((MOBILE / 'pnpm-lock.yaml').is_file())


if __name__ == '__main__':
    unittest.main(verbosity=2)
