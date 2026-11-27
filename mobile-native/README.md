# Native Android app (in progress)

The Android app rebuilt in Kotlin with Jetpack Compose (owner and developer decision, 26 November 2026). It will
replace the Expo app in `mobile/` when it does everything that app does and passes the same checks; until then
the Expo app stays the app in use and this one is installed beside it for testing.

**State: Phase 0 (foundation) and the first three parts of Phase 1 (the fingerprint lock, the safe, the
connection).** It signs in nowhere and reads no business data yet.

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
  flash at start in night mode. The app's icon is its own mark, a white key on the accent colour, as one drawing
  for every phone's icon shape and for themed icons; Android 12 and newer show it on the page colour while the
  app starts (Android 9 to 11 show the plain page colour). A frame that shows a bottom bar on phones and a side rail on tablets with the
  five agreed places (Today, Inbox, Chat, Mail, More; only More is finished, the others are in test builds only:
  Today and Inbox as a page that says what will be there, Chat and Mail against stand-ins), and behind More three
  finished screens: **Data trace** (list and detail; side by side on a tablet), **This phone** (fingerprint sensor,
  secure chip, Android version, checked for real) and **Display** (the look in use and the two Outdoor switches).
- **Building blocks with rules built in** (`Parts.kt`): a plain status line cannot be tapped and must not name an
  action; a message that needs the person to act cannot be created without its action. The look of every screen
  comes from these: a cool white page with white **row cards** (an icon in a tinted square, a title, one line, and
  a status **pill** that moves under the text at large font sizes), tinted **notice cards**, and one wide main
  button. The tints behind a status are part of the tested palette; Outdoor mode uses heavy lines and no tints.
- **The Welcome screens** (`core` `Welcome`, `app` `WelcomeScreen.kt`): the app's first screen is decided by a
  rule, never by the person, from what the phone knows (its key) and what the server says about this phone's
  access request: request access, pending approval (two approvers, with cancel that asks once more), refused with
  the reason, ran out, approved and make your key, unlock, and "your key is gone" with the reason. A key on the
  phone always wins; "approved" needs both approvers in any order. "How it works" opens from every situation and
  leads back. **Not live:** the server part for access requests and the fingerprint lock do not exist yet, so the
  screens run against a stand-in (`WelcomePreview.kt`) that only test builds can reach; no key is made and
  nothing is sent.

- **The fingerprint lock** (`core` `Lock`, `app` `PhoneLock.kt`): the app opens only after a strong fingerprint
  match. A key is made inside the phone's secure chip (StrongBox where the phone has one) that can be used only
  for the moment of one match: no PIN, no pattern, no weak face unlock. After making it the app reads back what
  the phone really did and deletes a key that is protected less than asked. That key locks a random data key, and
  holding the data key (in memory only, overwritten when dropped) is what "open" means, and the safe (below) is
  locked with it. Rules: 5 misses in a row erase the key (each miss is written at once, so closing the app does
  not give tries back; the miss that makes the phone lock its own sensor counts too); a fingerprint added to the phone destroys it (the chip does this); away from the app for
  5 minutes, or the app's process ended, and the fingerprint is asked again. The real "Welcome back", "Make your
  key" and "Your key is gone" screens are in use. **Stand-in until sign-in exists:** a phone without a key goes
  straight to "Make your key" as if approved; the key protects nothing but the app's own screens yet.

- **The safe** (`core` `Seal`, `app` `Safe.kt`): the one place for anything secret on the phone (the sign-in tokens
  from the sign-in part on). Each value is sealed with AES-256-GCM under the data key, with its own random starting
  number and its name bound in, so a stored value cannot be read without a fingerprint match, passed off under
  another name, or changed unnoticed. A locked app writes nothing, and the data key cannot be wiped in the middle of a use. The safe is emptied when the key is erased and
  when a new key is made; nothing is in a backup. **Today it holds only a test note** that test builds can save
  from "This phone", so the behaviour can be checked on a phone before sign-in exists.

- **The connection** (`app` `HttpTransport.kt`): the one real `Transport` behind `Saver`, built on the platform's own
  HTTP client (no added library). It talks to the one configured server and to nothing else (a redirect is handed
  back, never followed, and reads as "signed out"), encrypted only (the device's own loopback address is the single
  exception, for the tests' pretend server; the manifest forbids cleartext as well), sends the tracking number with
  every call (`X-Request-ID`) and the sign-in token only as a header. It reads ERPNext's answers: the record's
  fields, the server's own refusal sentence, 401 as signed out, 403 as not allowed; a page where an answer should
  be (a hotspot's or a sign-in page) is never taken for "saved". Numbers are written out in full (never "1.25E7"),
  so an amount of a crore or more stays an amount. **No sign-in yet**, so no token is sent; test
  builds have "Try the connection" on Data trace, which makes one real call and shows where it stopped.

- **Chat screens** (`core` `Chat`, `app` `ChatScreen.kt`): the list of rooms (Notices first, then the person's site,
  then the newest), a room (read, write, answer one message by tapping it), and starting a one-to-one chat with a
  colleague. Rooms are made by the server, never in the app. Company rooms say that their messages are kept by the
  company; Notices cannot be written to; a message written without a connection waits, marked in words, and is
  sent later. Phone: list, then room; tablet: side by side. **Not live:** there is no chat server and no sign-in
  yet, so the screens run against a stand-in (`ChatPreview.kt`) that only test builds can reach, with made-up
  rooms in memory; nothing is sent or stored. Not built yet: photos, the unread badge on the place, keeping 7
  days on the phone, alerts.

- **Mail screens** (`core` `Mail`, `app` `MailScreen.kt`): the received mail as conversations (the list is called
  "Received", because "Inbox" is the approvals place), folders, reading, reply, reply to all, forward and a new
  mail. Built in: mail from outside the company says so (only an exact company domain counts as inside);
  pictures from the internet are not loaded until asked for; a link shows the host it really leads to (look-alike
  letters in their coded form, a name before an "@" ignored) and is opened only after a yes; a mail to someone
  outside says so before it is sent; Send exists only when the mail can be sent. Attachments open inside the app;
  there is no "save to phone" (a setting that is off, owner's decision). **Not live:** there is no mail sign-in
  yet, so the screens run against a stand-in (`MailPreview.kt`) that only test builds can reach; nothing is sent,
  no link is opened, and there is no file viewer and no picture loading yet.

## Contents

- `core/`: the rules module and its tests.
- `app/`: the Android app.
- `build.gradle.kts`: pinned versions and the one check command.
- `gradle/verification-metadata.xml`: the SHA-256 checksum of every library and build tool; a changed or
  unexpected file stops the build.

## Requirements

JDK 17, the Android SDK (platform 37) and Gradle 9.9.2 or newer (older Gradle versions have open security
advisories, see `docs/decisions.md`). No Gradle wrapper is committed. The app needs
Android 9 or newer.

## Reuse

`core` has no dependency besides the Kotlin standard library and can be copied into any Kotlin project. The
building blocks in `app` depend only on Compose Material 3.

## Configuration

The server address is set privately as well (`erpServer=https://...` in the user's own Gradle properties, outside
this repository). Without it the build reaches no server.

The app ID defaults to the neutral `com.example.erp.next`. A deployment sets its own in a private
`gradle.properties` (`erpAppId=...`), never in this repository. Signing keys and service files stay outside the
repository (`.gitignore`).

## Tests

```
cd mobile-native
gradle checkAll
```

runs the rules module's unit tests (54), Android lint with warnings as errors, the app's screen and connection tests (30) and a
debug build. CI runs the same command on every push and pull request (job `native-app` in
`.github/workflows/check.yml`, Gradle 9.9.2 checked against its published checksum).

The screen tests run on the computer (Robolectric). **The robot that walks every link** opens every place in the
frame and every item on it, in the light, dark and outdoor looks, at phone and tablet width and at normal and
double font size, and fails when a destination is missing, when anything that can be tapped is under 48 dp, or
when text runs off the side. Proven once by breaking the rule on purpose (smaller buttons: five tests failed).
`tests/test_mobile_native.py` checks from the repository's side that the app stays neutral, keeps its backup and
screenshot protection, and keeps the "no action words without an action" building blocks.

Checked by hand on a phone on 26 November 2026 (Oppo, Android 15): the app starts, Data trace shows a failed and a
complete sample trace, and the detail shows the eight points with the failed one and its reason; the look turns
dark and light with the phone's night mode, the Outdoor switch changes the look, and the light sensor is read.
The key store and the fingerprint question cannot run on a computer: the lock's rules are unit-tested and its
protections are checked as text by `tests/test_mobile_native.py`. No automated test yet proves that a miss is
stored, that the fifth erases, or that leaving the app locks it; those are checked by hand on phones. Open points
from the second review: growing waits between tries (in the decision record, not built), a second copy of the
screen opened by another app can lock the app early, and a stored data key that can no longer be opened after a
match has no way out except clearing the app's data.
Checked by hand by the developer on 27 November 2026 (same phone): a key is made and opens the app; a test note
stays in the safe across a full close and reopen; five wrong fingers count the tries down, end in "Your key is
gone", and the safe is empty after a new key; the fingerprint is asked again after more than 5 minutes away and
not before; "Try the connection" without a server address stops at the network point. The same checks were repeated by the developer on a
second phone (Samsung, Android 13) the same day. Not reported yet: a fingerprint added in the phone's Settings.
The connection tests run on the computer's own HTTP client; the phone's differs in details and has not met a real
server yet. `Safe` itself has no behaviour test (its sealing has, in `core`); its rules are checked as text.
Not yet covered: picture comparison (the robot measures sizes and positions, it does not see overlapping or
ugly layouts), Android 9 to 14, a real tablet. Not yet looked at by a person in real sunlight or at the largest
font size.

## Licenses

Our own code, AGPL-3.0-or-later like the repository. Libraries (all Apache-2.0 unless noted; the connection uses Android's own HTTP client and JSON reader): Kotlin 2.2.10
(JetBrains), Jetpack Compose (BOM 2026.09.00: UI, Material 3, adaptive navigation suite), AndroidX Activity
1.12.4 and Biometric 1.1.0, the Android Gradle plugin 9.2.1; for tests only: JUnit 4.13.2 (EPL-1.0), Robolectric
4.18 (MIT) and Compose's UI test library.

The icons and the app's mark are simple line drawings made for this app (our own work, same licence).

## AI-assisted development

Written with Claude Code and checked by the developer.
