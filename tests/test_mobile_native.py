"""mobile-native module: the native Android app stays neutral and keeps its safety rules.

The Kotlin code has its own unit tests (`gradle checkAll` in mobile-native). These checks run without Android
tools, so every contributor and the repository check see at once when a protection is removed.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'mobile-native'
APP = NATIVE / 'app/src/main'
KOTLIN = APP / 'kotlin/com/example/erp/app'


class MobileNativeTests(unittest.TestCase):
    def test_app_identity_is_neutral_and_set_privately(self):
        build = (NATIVE / 'app/build.gradle.kts').read_text(encoding='utf-8')
        self.assertIn('providers.gradleProperty("erpAppId").getOrElse("com.example.erp.next")', build)
        self.assertIn('minSdk = 28', build)
        self.assertEqual((APP / 'res/values/strings.xml').read_text(encoding='utf-8').count('>ERP<'), 1)

    def test_nothing_leaves_the_phone_by_backup_or_screenshot(self):
        manifest = (APP / 'AndroidManifest.xml').read_text(encoding='utf-8')
        self.assertIn('android:allowBackup="false"', manifest)
        self.assertIn('android:dataExtractionRules="@xml/no_backup"', manifest)
        rules = (APP / 'res/xml/no_backup.xml').read_text(encoding='utf-8')
        for part in ('cloud-backup', 'device-transfer'):
            block = rules.split(f'<{part}>')[1].split(f'</{part}>')[0]
            self.assertEqual(set(re.findall(r'<exclude domain="(\w+)"', block)),
                             {'root', 'file', 'database', 'sharedpref', 'external'}, part)
        self.assertNotIn('<include', rules)
        self.assertIn('FLAG_SECURE', (KOTLIN / 'MainActivity.kt').read_text(encoding='utf-8'))

    def test_only_the_permissions_the_app_uses(self):
        manifest = (APP / 'AndroidManifest.xml').read_text(encoding='utf-8')
        self.assertEqual(re.findall(r'uses-permission android:name="android\.permission\.(\w+)"', manifest), ['USE_BIOMETRIC'])
        self.assertEqual(manifest.count('android:exported="true"'), 1, 'only the launcher screen is open to other apps')

    def test_a_message_that_names_an_action_must_carry_one(self):
        parts = (KOTLIN / 'Parts.kt').read_text(encoding='utf-8')
        # The action message cannot be built without its action; the plain status line has no click.
        self.assertRegex(parts, r'fun ActionMessage\(kind: StatusKind, text: String, actionLabel: String, onAct: \(\) -> Unit')
        status = parts.split('fun Status(')[1].split('\n}\n')[0]
        self.assertNotIn('clickable', status)
        self.assertNotIn('onClick', status)

    def test_every_destination_in_the_frame_has_a_screen(self):
        main = (KOTLIN / 'MainActivity.kt').read_text(encoding='utf-8')
        places = re.findall(r'^\s+([A-Z_]+)\("', main.split('enum class Place')[1].split('}')[0], re.M)
        self.assertTrue(places)
        for place in places:
            self.assertRegex(main, rf'Place\.{place} -> \w+Screen\(', f'{place} has no screen')

    def test_reports_leave_values_out_by_default(self):
        trace = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Trace.kt').read_text(encoding='utf-8')
        self.assertIn('fun report(withValues: Boolean = false)', trace)
        self.assertIn('if (withValues && mark.detail != null)', trace)

    def test_versions_and_checksums_are_pinned(self):
        text = (NATIVE / 'build.gradle.kts').read_text(encoding='utf-8') + (NATIVE / 'app/build.gradle.kts').read_text(encoding='utf-8')
        for line in re.findall(r'(?:implementation|testImplementation)\("([^"]+)"\)', text):
            if line.startswith('androidx.compose.') and ':compose-bom:' not in line:
                continue  # versions come from the pinned Compose list
            self.assertRegex(line, r':\d+(\.\d+)+$', f'{line} has no exact version')
        self.assertNotRegex(text, r'[:"]\+"|latest\.release|-SNAPSHOT')
        metadata = (NATIVE / 'gradle/verification-metadata.xml').read_text(encoding='utf-8')
        self.assertIn('<verify-metadata>true</verify-metadata>', metadata)
        self.assertGreater(metadata.count('<sha256 '), 300)

    def test_source_names_no_host(self):
        for path in list(NATIVE.rglob('*.kt')) + list(NATIVE.rglob('*.kts')):
            if 'build' in path.parts:
                continue
            for host in re.findall(r'https?://([A-Za-z0-9.-]+)', path.read_text(encoding='utf-8')):
                self.fail(f'{path.relative_to(ROOT)} names {host}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
