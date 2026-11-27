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
        # Status lines, pills and notice cards only tell; none of them can be tapped.
        for block in ('Status', 'Pill', 'Notice'):
            body = parts.split(f'fun {block}(')[1].split('\n}\n')[0]
            self.assertNotIn('clickable', body, block)
            self.assertNotIn('onClick', body, block)

    def test_status_tints_are_part_of_the_tested_palette(self):
        palette = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Palette.kt').read_text(encoding='utf-8')
        look = (NATIVE / 'core/src/test/kotlin/com/example/erp/core/LookTest.kt').read_text(encoding='utf-8')
        for tint in ('okSoft', 'warnSoft', 'badSoft'):
            self.assertIn(f'val {tint}: Long', palette)
            self.assertIn(f'look.{tint}', look, f'the contrast test covers {tint}')

    def test_every_destination_in_the_frame_has_a_screen(self):
        main = (KOTLIN / 'AppFrame.kt').read_text(encoding='utf-8')
        places = re.findall(r'^\s+([A-Z_]+)\("', main.split('enum class Place')[1].split('}')[0], re.M)
        self.assertTrue(places)
        for place in places:
            self.assertRegex(main, rf'Place\.{place} -> \w+Screen\(', f'{place} has no screen')

    def test_the_look_follows_the_phone_and_never_the_wallpaper(self):
        kotlin = ''.join(p.read_text(encoding='utf-8') for p in KOTLIN.glob('*.kt'))
        self.assertIn('isSystemInDarkTheme()', kotlin, 'day and night follow the phone')
        self.assertIn('Sensor.TYPE_LIGHT', kotlin, 'Outdoor mode follows bright light')
        self.assertIn('"outdoor-automatic", true', kotlin, 'automatic by default; the person can switch it off')
        self.assertNotRegex(kotlin, r'dynamic(Light|Dark)ColorScheme', 'status colours must not change with the wallpaper')
        # Screens name colours by their job only; raw colour numbers live in the tested palette.
        for path in KOTLIN.glob('*.kt'):
            if path.name != 'Theme.kt':
                self.assertNotRegex(path.read_text(encoding='utf-8'), r'Color\(0x|Color\.(White|Black|Red|Green|Gray)', path.name)
        night = (APP / 'res/values-night/themes.xml').read_text(encoding='utf-8')
        self.assertIn('#0F141A', night, 'no white flash at start in night mode')
        palette = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Palette.kt').read_text(encoding='utf-8')
        self.assertIn('0x0F141A', palette, 'the start colour is the page colour of the dark look')

    def test_text_sizes_scale_with_the_phone(self):
        theme = (KOTLIN / 'Theme.kt').read_text(encoding='utf-8')
        self.assertNotRegex(theme, r'fontSize = [^,]*\.dp', 'text sizes are in sp so they follow the font size set on the phone')
        sizes = [int(n) for n in re.findall(r'fontSize = \((\d+) \+ more\)\.sp', theme)]
        self.assertTrue(sizes and min(sizes) >= 15, 'no text smaller than 15')

    def test_the_robot_walks_every_link_in_every_look_and_size(self):
        robot = (NATIVE / 'app/src/test/kotlin/com/example/erp/app/ScreensTest.kt').read_text(encoding='utf-8')
        self.assertIn('for (place in Place.entries)', robot, 'every place, also ones added later')
        for look in ('LIGHT', 'DARK', 'OUTDOOR'):
            self.assertIn(f'walk(Palettes.{look}', robot)
        self.assertIn('fontScale = 2.0f', robot, 'double font size')
        self.assertIn('w1100dp', robot, 'tablet width')
        self.assertIn('48.dp', robot, 'tap targets are measured')
        self.assertIn('runs off the side', robot, 'text overflow is measured')
        build = (NATIVE / 'build.gradle.kts').read_text(encoding='utf-8')
        self.assertIn('":app:testDebugUnitTest"', build, 'the check command runs the robot')

    def test_every_save_goes_through_the_one_calling_layer(self):
        saver = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Saver.kt').read_text(encoding='utf-8')
        for point in ('Point.SCREEN', 'Point.NETWORK', 'Point.GATEWAY', 'Point.SERVER', 'Point.READ_BACK'):
            self.assertIn(point, saver)
        # A raw server error text is never the sentence a person reads.
        self.assertIn('"The server has a problem right now.', saver)

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
