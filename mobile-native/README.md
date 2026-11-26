# Native Android app (in progress)

The Android app rebuilt in Kotlin with Jetpack Compose (owner and developer decision, 26 November 2026). It will
replace the Expo app in `mobile/` when it does everything that app does and passes the same checks; until then
the Expo app stays the app in use and this one is installed beside it for testing.

**State: Phase 0, foundation.** It signs in nowhere and reads no business data yet.

## Purpose

One app for phones and tablets that staff can read in sunlight, that works without signal, and in which every
tap leads to a finished screen. This folder currently holds the foundation every later feature is built on:

- **The rules module** (`core`): pure Kotlin with no Android in it, so it is tested on any computer and can later
  be shared with an iPhone app.
  - `Money`: exact decimals, shown the Indian way (1,50,000.00); refuses anything that is not a plain amount.
  - `Trace`: the data-flow tracker. Every action gets one tracking number (its request ID); each of eight points
    its data passes (screen, phone store, network, gateway, server function, read-back, follow-up, display) writes
    a mark. The first red mark names where it went wrong. Reports leave values out unless a test build asks.
  - `ReadBack`: after a save, compares what was sent with what the server stored, field by field and by kind
    (text, whole number, decimal, date and time, yes/no); names a time-zone shift as one.
  - `Palette`, `Contrast`, `OutdoorSwitch`: the colours of the three looks (light, dark, outdoor) by their job,
    the WCAG contrast formula, and the bright-light switch with two thresholds so the look does not flicker.
    A unit test checks every text and status colour against every background in every look (7:1 or more;
    10:1 outdoors).
  - `Saver`: the one place every save passes through. It sends, sorts the answer to the point where it failed
    (no connection, signed out, not allowed, refused by a server rule, server failure), reads the record back and
    compares it, writes every step into the trace, and returns a plain sentence for the person. The network itself
    is an interface until Phase 1, so every path is tested without a server.
  - `Format`: the fixed ways of writing dates ("26 Nov 2026", "Today, 08:57") and waiting times ("12 min", "3 h",
    counted from when the thing started waiting), and cutting long text at a word.
- **The app shell** (`app`): a look that adjusts to the person's phone by itself: day or night mode, the phone's
  font size (all sizes in sp, none below 15) and its own font, and **Outdoor mode** in bright light from the
  light sensor (strongest contrast, larger and heavier type), automatic by default and switchable by the person.
  Wallpaper colours are deliberately not used: a status colour must mean the same on every phone. 56 dp touch
  targets, status always as a mark and words, edge to edge with readable system bar icons in every look, no white
  flash at start in night mode. A frame that shows a bottom bar on phones and a side rail on tablets, and three
  finished screens: **Data trace** (list and detail; side by side on a tablet), **This phone** (fingerprint sensor,
  secure chip, Android version, checked for real) and **Display** (the look in use and the two Outdoor switches).
- **Building blocks with rules built in** (`Parts.kt`): a plain status line cannot be tapped and must not name an
  action; a message that needs the person to act cannot be created without its action.

## Contents

- `core/`: the rules module and its tests.
- `app/`: the Android app.
- `build.gradle.kts`: pinned versions and the one check command.
- `gradle/verification-metadata.xml`: the SHA-256 checksum of every library and build tool; a changed or
  unexpected file stops the build.

## Requirements

JDK 17, the Android SDK (platform 37) and Gradle 9.4 or newer. No Gradle wrapper is committed. The app needs
Android 9 or newer.

## Reuse

`core` has no dependency besides the Kotlin standard library and can be copied into any Kotlin project. The
building blocks in `app` depend only on Compose Material 3.

## Configuration

The app ID defaults to the neutral `com.example.erp.next`. A deployment sets its own in a private
`gradle.properties` (`erpAppId=...`), never in this repository. Signing keys and service files stay outside the
repository (`.gitignore`).

## Tests

```
cd mobile-native
gradle checkAll
```

runs the rules module's unit tests (29), Android lint with warnings as errors, the app's screen tests (11) and a
debug build.

The screen tests run on the computer (Robolectric). **The robot that walks every link** opens every place in the
frame and every item on it, in the light, dark and outdoor looks, at phone and tablet width and at normal and
double font size, and fails when a destination is missing, when anything that can be tapped is under 48 dp, or
when text runs off the side. Proven once by breaking the rule on purpose (smaller buttons: five tests failed).
`tests/test_mobile_native.py` checks from the repository's side that the app stays neutral, keeps its backup and
screenshot protection, and keeps the "no action words without an action" building blocks.

Checked by hand on a phone on 26 November 2026 (Oppo, Android 15): the app starts, Data trace shows a failed and a
complete sample trace, and the detail shows the eight points with the failed one and its reason; the look turns
dark and light with the phone's night mode, the Outdoor switch changes the look, and the light sensor is read.
Not yet covered: picture comparison (the robot measures sizes and positions, it does not see overlapping or
ugly layouts), Android 9 to 14, a real tablet. Not yet looked at by a person in real sunlight or at the largest
font size.

## Licenses

Our own code, AGPL-3.0-or-later like the repository. Libraries (all Apache-2.0 unless noted): Kotlin 2.2.10
(JetBrains), Jetpack Compose (BOM 2026.09.00: UI, Material 3, adaptive navigation suite), AndroidX Activity
1.12.4 and Biometric 1.1.0, the Android Gradle plugin 9.2.1; for tests only: JUnit 4.13.2 (EPL-1.0), Robolectric
4.18 (MIT) and Compose's UI test library.

## AI-assisted development

Written with Claude Code and checked by the developer.
