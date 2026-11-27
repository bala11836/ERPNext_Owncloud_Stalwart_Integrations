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

    def test_the_icon_is_our_own_neutral_mark_in_the_accent_colour(self):
        manifest = (APP / 'AndroidManifest.xml').read_text(encoding='utf-8')
        self.assertIn('android:icon="@mipmap/ic_launcher"', manifest)
        icon = (APP / 'res/mipmap-anydpi/ic_launcher.xml').read_text(encoding='utf-8')
        for layer in ('<background android:drawable="@color/icon_ground"', '<foreground ', '<monochrome '):
            self.assertIn(layer, icon)
        themes = (APP / 'res/values/themes.xml').read_text(encoding='utf-8')
        palette = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Palette.kt').read_text(encoding='utf-8')
        self.assertIn('<color name="icon_ground">#0B4F9E</color>', themes)
        self.assertIn('0x0B4F9E', palette, 'the icon ground is the accent of the day look')
        # Vector drawings only: no picture files that could carry a brand.
        pictures = [p.name for p in (APP / 'res').rglob('*') if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')]
        self.assertEqual(pictures, [])

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
        self.assertEqual(re.findall(r'uses-permission android:name="android\.permission\.(\w+)"', manifest), ['INTERNET', 'USE_BIOMETRIC'])
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

    def test_the_welcome_stand_in_stays_out_of_the_real_app(self):
        frame = (KOTLIN / 'AppFrame.kt').read_text(encoding='utf-8')
        self.assertRegex(frame, r'WELCOME\("Welcome", "Welcome preview", R\.drawable\.ic_key, testOnly = true\)')
        self.assertIn('Place.entries.filter { !it.testOnly || state.testBuild }', frame)
        # The first screen is decided in the rules module, never by the person, and a key on the phone wins.
        rules = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Welcome.kt').read_text(encoding='utf-8')
        self.assertIn('key == KeyState.PRESENT -> Welcome.Unlock', rules.split('fun welcomeFor(')[1].split('\n')[1])
        # Every button of a Welcome screen needs its action: none has a default.
        screen = (KOTLIN / 'WelcomeScreen.kt').read_text(encoding='utf-8')
        actions = screen.split('class WelcomeActions(')[1].split(')\n')[0]
        self.assertEqual(actions.count('() -> Unit,'), 6)
        self.assertNotIn('= {', actions)

    def test_the_lock_opens_only_for_a_strong_fingerprint(self):
        lock = (KOTLIN / 'PhoneLock.kt').read_text(encoding='utf-8')
        for needed in ('.setUserAuthenticationRequired(true)', '.setInvalidatedByBiometricEnrollment(true)',
                       'setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG)',
                       '.setAllowedAuthenticators(BIOMETRIC_STRONG)', 'isUserAuthenticationRequirementEnforcedBySecureHardware',
                       'BiometricPrompt.CryptoObject(cipher)'):
            self.assertIn(needed, lock)
        # No PIN, pattern or weak face unlock anywhere in the app.
        kotlin = ''.join(p.read_text(encoding='utf-8') for p in KOTLIN.glob('*.kt'))
        self.assertNotRegex(kotlin, r'DEVICE_CREDENTIAL|BIOMETRIC_WEAK|setDeviceCredentialAllowed')
        # A miss is written before anything else happens, and the fifth erases.
        count = lock.split('fun countMiss(): Boolean {')[1].split('lateinit var prompt')[0]
        self.assertLess(count.index('prefs.edit(commit = true) { putInt(MISSES, now) }'), count.index('erase(KeyLoss.MISSES)'))
        self.assertIn('countMiss()', lock.split('override fun onAuthenticationFailed()')[1].split('override fun')[0])
        self.assertIn('countMiss()', lock.split('override fun onAuthenticationError(')[1].split('when (errorCode)')[0])
        self.assertIn('info.userAuthenticationValidityDurationSeconds <= 0', lock)
        # A fingerprint question is never answered to a rebuilt screen, and the stand-in cannot reach a real build.
        manifest = (APP / 'AndroidManifest.xml').read_text(encoding='utf-8')
        for change in ('orientation', 'screenSize', 'uiMode', 'fontScale'):
            self.assertIn(change, manifest.split('android:configChanges="')[1].split('"')[0])
        # The open app exists in memory only, and the app is shown only while it is open.
        self.assertNotRegex(lock.split('object Session')[1], r'prefs|SharedPreferences|File')
        main = (KOTLIN / 'MainActivity.kt').read_text(encoding='utf-8')
        self.assertIn('if (!Session.isOpen) {', main)
        self.assertIn('check(BuildConfig.DEBUG || view.key != KeyState.NONE)', main)
        self.assertIn('Session.left()', main.split('override fun onStop()')[1].split('}')[0])
        rules = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Lock.kt').read_text(encoding='utf-8')
        self.assertIn('const val MAX_MISSES = 5', rules)
        self.assertIn('const val AWAY_MS = 5 * 60 * 1000L', rules)

    def test_the_safe_stores_nothing_in_the_clear_and_goes_with_the_key(self):
        safe = (KOTLIN / 'Safe.kt').read_text(encoding='utf-8')
        # Every write is sealed with the data key first, and a locked app writes nothing.
        put = safe.split('fun put(')[1].split('\n    }')[0]
        self.assertIn('Session.withKey { Seal.seal(it, name, value.toByteArray()) } ?: return false', put)
        self.assertLess(put.index('Seal.seal(it, name,'), put.index('putString('))
        self.assertIn('.commit()', put)
        self.assertEqual(safe.count('putString('), 1)
        self.assertIn('Session.withKey { Seal.open(it, name, sealed) }', safe)
        # The data key is used only through the one guarded door, which a wipe cannot interrupt.
        self.assertNotIn('Session.dataKey', safe)
        session = (KOTLIN / 'PhoneLock.kt').read_text(encoding='utf-8').split('object Session')[1]
        self.assertEqual(session.count('@Synchronized'), 3)
        # The safe is emptied when the key is erased and when a new one is made.
        lock = (KOTLIN / 'PhoneLock.kt').read_text(encoding='utf-8')
        erase = lock.split('private fun erase(')[1].split('\n    }')[0]
        self.assertIn('Safe.wipe(app)', erase)
        self.assertIn('Session.lock()', erase)
        self.assertIn('Safe.wipe(app)', lock.split('fun make(')[1].split('fun open(')[0])
        # Only the lock's own state and the display settings are stored unsealed.
        kotlin = {p.name: p.read_text(encoding='utf-8') for p in KOTLIN.glob('*.kt')}
        writers = sorted(name for name, text in kotlin.items() if 'getSharedPreferences(' in text)
        self.assertEqual(writers, ['MainActivity.kt', 'PhoneLock.kt', 'Safe.kt'])
        self.assertEqual(re.findall(r'getSharedPreferences\("(\w+)"', kotlin['MainActivity.kt']), ['display'])
        seal = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Seal.kt').read_text(encoding='utf-8')
        self.assertIn('"AES/GCM/NoPadding"', seal)
        self.assertIn('SecureRandom().nextBytes(it)', seal)
        self.assertEqual(seal.count('cipher.updateAAD(name.toByteArray())'), 2)

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

    def test_the_app_reaches_one_server_encrypted_and_follows_no_redirect(self):
        net = (KOTLIN / 'HttpTransport.kt').read_text(encoding='utf-8')
        self.assertIn('connection.instanceFollowRedirects = false', net)
        self.assertIn('uri.scheme == "https" || (uri.scheme == "http" && uri.host == LOOPBACK)', net)
        self.assertIn('const val LOOPBACK = "127.0.0.1"', net)
        self.assertIn('connection.setRequestProperty("X-Request-ID", trackingId)', net)
        self.assertIn('"Authorization", "Bearer $it"', net)
        # The network is opened in this one file only, and the phone itself refuses unencrypted traffic too.
        kotlin = {p.name: p.read_text(encoding='utf-8') for p in KOTLIN.glob('*.kt')}
        opens = sorted(name for name, text in kotlin.items() if re.search(r'openConnection|HttpURLConnection|java\.net\.Socket|OkHttp', text))
        self.assertEqual(opens, ['HttpTransport.kt'])
        manifest = (APP / 'AndroidManifest.xml').read_text(encoding='utf-8')
        self.assertIn('android:usesCleartextTraffic="false"', manifest)
        self.assertNotIn('networkSecurityConfig', manifest)
        # The server's address is set privately, never here.
        build = (NATIVE / 'app/build.gradle.kts').read_text(encoding='utf-8')
        self.assertIn('providers.gradleProperty("erpServer").getOrElse("")', build)
        self.assertNotIn('erpServer', (NATIVE / 'gradle.properties').read_text(encoding='utf-8'))

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
