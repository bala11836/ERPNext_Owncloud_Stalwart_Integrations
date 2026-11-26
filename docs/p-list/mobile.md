# Mobile: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 26 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# Mobile: P items

The native mobile app, push notifications, offline behaviour and phone clients.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P14 — Retained mobile/browser push acceptance

**App:** mobile · **Also touches:** erp, raven · **State:** open

**Status:** approved-session OAuth/PKCE binding, refresh/revocation and push modules are retained; current-stack native Raven and fresh-device acceptance remain incomplete. Earlier ERP/HR notification receipt is recorded at its earlier deployment checkpoint, not re-certified on the current portal.

Verify the new portal's per-device opt-in controls, ERP/HR notification receipt and tapping, and Raven background delivery from another user on actual devices. Native relay credentials and registrations stay private. Mocked tests and a provider HTTP success do not prove device delivery. No notification test or business approval message was sent during consolidation.

Recheck native Raven login/chat/refresh and revoked-token refusal, and coordinate realtime recovery with P01. Preserve exact validated callbacks and existing workers/drafts. See [push and Raven scope](../roadmap.md#1-push-and-session-bound-native-raven).

### P50 — Native mobile app for phones and tablets (module `mobile-app`)

**App:** mobile · **Also touches:** none · **State:** open

**Status:** planning with the owner (opened 19 November 2026); nothing built.
Own app (not the colleague's P38 app), native on Android and iOS, one codebase
for phones and tablets, in this repository as a self-contained module. No
Supabase: ERPNext is the data backend, authentik the sign-in (native-client
login already exists).

**Decided so far (owner):**
- Users: office staff, field workers, management; menus from each person's
  ERPNext roles and project access, enforced by the server (the app never
  decides permissions).
- Data capture happens mainly on the app; the experience must be intuitive,
  fast and engaging. Same work possible on phone and tablet (parity); no
  special desktop-handoff feature.
- Version 1 scope: attendance and checkout, site reports and photos, vendor
  onboarding and KYC capture, approvals and requests; Drive, Mail and DMS
  access; chat and alerts.
- Screens: hybrid. Hand-designed screens for the top daily tasks per module,
  automatic forms generated from ERPNext's definitions for everything else.
- Offline: capture works without a signal and syncs later, with a visible
  "waiting to send" state. This replaces the web-app (PWA) offline work: P23
  closed as superseded (owner, 26 November 2026).
- Layout: four bottom tabs on the phone (Work = the person's own module,
  opening with a Today dashboard; Chat; Mail; Drive); floating "+" for quick
  capture; module switcher only for the few multi-module users; project
  selector limited to assigned projects. Tablet: permanent side rail with the
  same four areas and list/detail panes. Separate layout per ERP module.
- Pilot module: HR attendance and checkout (sets the shared look and
  components).
- Distribution: Android signed APK hosted by us; iOS needs an Apple Developer
  account (TestFlight or Ad Hoc); no store listing. Framework recommended:
  React Native with Expo (TypeScript); Flutter is the runner-up, final choice
  after asking what the colleague and owner can maintain.

**Still to decide:** look and feel (logo, colours, languages, light/dark),
sign-in and security details (biometrics, session length, lost-device wipe),
notifications, the module list and each module's layout, delivery and update
method, build order after the pilot.

**Update (21 November 2026): native sign-in on the test site.** PR #15 (module `mobile-app`, from the
colleague's fork) was reviewed and deployed to the test site: the test gateway has production's native app
routes, the app's OAuth client is created on test from the private profile ("ERP Mobile", public PKCE client),
native sign-in is on for that client only. The colleague tests on a real phone. **Open (owner decision):** the first
sign-in via the relayed test host returns to the front page because the production proxy's private entry point
drops `X-Forwarded-Uri`; fix = trust forwarded headers on that entry point for the bridge sources only (a production
proxy setting). His own SSH access (forced-command deploy key plus a tailnet share) follows P54. **Later the same day:** the app's 500 after sign-in was a server
bug (`portal/mobile.py` imported a non-existent `before_request`); fixed in PR #15 (`4d28354`), installed on test,
app requests now succeed. The same line is latent on production: promote it with PR #15 (ERP release). **Naming (owner, 21 November 2026):** one universal app name with no company name, **"ERP Mobile"**,
for the app title, its sign-in record and its link scheme (`erpmobile`); on test the client id is `erpmobiletest1`.

**Branding per server (owner, 25 November 2026; replaces the single universal name above):**
one build per brand, same code, built automatically from a small brand file (name, icon,
colours, server address). The home-screen name and icon come from the build, because phones
cannot reliably rename an app or swap its icon while it runs; inside the app the logo and
colours also come from the server it connects to. For now there is one brand, **unformat**
with the **UN** icon, for the test site, demo sites and production. The first client
(<tenant company>; production holds its assets) gets its own build from the same
script when it goes live. Demo sites use the unformat build. Record the change in the decision
log with the first pull request.

**Passkeys in the app (owner, 25 November 2026):** ERP Mobile becomes the phone's passkey
provider and holds each person's sign-in key; Android first. Scope, decisions and the decision
path are in **P82** (sign-in list).

### P64 — Native app sign-in on production: latent auth-hook crash and a stale client list

**App:** mobile · **Also touches:** signin, erp · **State:** in progress

**Status:** open, found 21 November 2026 while connecting the mobile app (PR #15) to the test site.
- **Flaw:** `portal/mobile.py` (the `auth_hooks` entry) imported `before_request` from `portal/combined.py`, a
  function that never existed in this repository (a leftover of the retired pre-repository Suite role guard). Every
  Bearer request from an approved native client failed with ImportError (HTTP 500) before reaching the app's API.
  The existing test replaced `combined` with a fake module that still had the function, so it could not catch this.
- **Fixed on test:** colleague's commit `4d28354` (PR #15) removes the call and makes the test import the real module;
  installed on the test site 21 November 10:19 UTC; app requests succeed since (check_access and the app's bootstrap 200).
- **Production:** the same line is live, native sign-in is on (`cloud_raven_mobile_enabled`), but the native client
  list (`cloud_native_mobile_clients` and the legacy `unformat_native_mobile_clients`) names `psvrvmandb`, the
  colleague's old client that was deleted from production on 20 November (P38). So nothing can trigger it today, and
  the setting is stale. Only "Raven Mobile" exists as an OAuth client on production, and it is not in the native list.
- **To do (normal order):** merge PR #15, ERP release with a rollback point; when the app goes to production (P50),
  create its client and set the native list to it (drop the stale id and the legacy key); browser and phone check after
  promotion. Decide whether Raven Mobile should be a native client.

**Progress (21 November 2026):** the fix is **live on production** (ERP `4a5151f`, merged via PR #15 and #18): a Bearer request
no longer raises the ImportError. **Remaining:** the stale native client list on production (`psvrvmandb`) is corrected
when the app goes to production (P50), and whether Raven Mobile should be a native client is decided then.

### P74 — Document and photo store in the mobile app (Drive / oCIS)

**App:** mobile · **Also touches:** drive, erp, signin · **State:** in progress

**Status:** proposed in public issue #53 (owner decisions 23 November 2026), design revised by the owner on
24 November 2026. Server part public PR #65, app part PR #66 (builds on #64).
- **Owner decisions (23 and 24 November 2026):** no Drive app on phones; no separate photo server (Immich and
  PhotoPrism compared and set aside); site photos go straight to the project's Drive space, tagged (project, site,
  type, time, GPS, who, "From gallery", "Captured offline"); nobody deletes a work photo; phone storage only for the
  encrypted offline queue (at most 1 day); receipts, bills and scans stay with the DMS; phone scanning to Paperless
  later. **Everything through ERPNext with one sign-in:** the phone talks only to ERPNext, which checks site
  membership (the attendance rule); a dedicated Drive account (`erp-photo-service`, Space Admin) owned by the server
  writes and reads one project space per ERPNext Project; no member sync, no TUS.
- **Review fixes (24 November 2026, on #65):** full photo id in the Drive path (no upload can replace a photo);
  project browsing limited to the person's own site folders; Drive thumbnail sizes gain `256x256` (owner chose
  option A; oCIS served 1080 px for the 256 px preview).
- **Test site (24 November 2026):** #65 head `db3969c` deployed; 30 of 31 live API checks passed, the failed one
  (preview size) fixed by the Drive setting. Receipts `p74-test-*`.
- **Merged 24 November 2026:** #65 at `059f8bf` (tree identical to tested `db3969c`). Production held: it needs the
  main ERP release with PR #40 and #51 (owner decision).
- **Production 25 November 2026:** Drive preview size, ERP main `059f8bf` (with #40 and #51), the
  `erp-photo-service` account and `drive_store` config are live (release log, receipts `p74-production-*`). No
  production test photo (owner).
- **26 November 2026:** owner browser checks on production working; first nightly renewal run without failure.
  Phone test started on the test site (owner: colleague's Android development build of #66 head `f195a2d`, which
  contains #64 head `5c7c3b5`; the owner's test administrator; site Mobile Attendance QA, project PROJ-0002, no
  new test data: the account is a System Manager, so it counts as a member of every enabled site).
- **Phone test, first part (25 November, found 26 November):** two camera photos from the app on test passed the
  server checks (folder, tags, no EXIF, 256 px preview, no duplicate). Gallery, offline, list, project files and
  sign-out still to test.
- **Open:** the rest of the phone test with #64 and #66 (checklist on #66); backups and disk growth with P72 (about 1 MB per photo
  before compression; the app sends about 200 KB); privacy (photos show workers and the public: project access only,
  no public links); the daily token renewal needs the scheduler (test has none).
