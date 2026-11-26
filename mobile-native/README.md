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
- **The app shell** (`app`): the sunlight look (white ground, near-black text, one accent, large type, 56 dp touch
  targets, status always as a mark and words), a frame that shows a bottom bar on phones and a side rail on
  tablets, and two finished screens: **Data trace** (list and detail; side by side on a tablet) and **This phone**
  (fingerprint sensor, secure chip, Android version, checked for real).
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

runs the rules module's unit tests, Android lint with warnings as errors, the app's unit tests and a debug build.
`tests/test_mobile_native.py` checks from the repository's side that the app stays neutral, keeps its backup and
screenshot protection, and keeps the "no action words without an action" building blocks.

Checked by hand on a phone on 26 November 2026 (Oppo, Android 15): the app starts, Data trace shows a failed and a
complete sample trace, and the detail shows the eight points with the failed one and its reason. Not yet covered
by automatic screen tests; those are the next step of Phase 0.

## Licenses

Our own code, AGPL-3.0-or-later like the repository. Libraries (all Apache-2.0 unless noted): Kotlin 2.2.10
(JetBrains), Jetpack Compose (BOM 2026.09.00: UI, Material 3, adaptive navigation suite), AndroidX Activity
1.12.4 and Biometric 1.1.0, the Android Gradle plugin 9.2.1; JUnit 4.13.2 for tests (EPL-1.0).

## AI-assisted development

Written with Claude Code and checked by the developer.
