# Mobile: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 21 November 2026
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

### P23 — PWA offline and poor-connectivity behavior

**App:** mobile · **Also touches:** portal · **State:** open

**Status:** planned. Audit retained drafts and existing service workers before
adding any caching or queue. Design user-isolated caches, safe logout/wipe,
idempotent retries, conflict/error visibility and bounded storage. Test browser
and installed iOS behavior, airplane mode and reconnect; do not cache sensitive
business data or replay consequential actions by default.

### P38 — Colleague's mobile app: test-only access and safe contributions

**App:** mobile · **Also touches:** none · **State:** closed

**Status:** **closed 20 November 2026 (owner):** the owner builds the mobile app
(P50) and no longer supports the colleague's own app; he may contribute to the
open-source repository if he chooses. His app's OAuth client "<colleague's app>"
was removed from the production ERP and from test (backup
`<rollback folder>` on production); the test bootstrap no
longer restores it (`test_oauth_clients` emptied in the two private test
profiles, backups beside them). Rest of this entry is history.
Earlier status: requested by the owner on 18 November 2026; after test-site acceptance (P33). Order agreed: relay (done), test acceptance, P02 backups, P37 production move, then P38.
Since 19 November 2026 the code repository is public: the colleague forks
`rdavuluri44/ERPNext_Owncloud_Stalwart_Integrations` and opens pull requests
to `main`; no access grant is needed.

A colleague is building a mobile app (in their own repository) that works with
and updates this system. Until the app is thoroughly tested it must reach the
**test site only**, and the colleague also contributes to this repository.

- **Test-only app access.** App credentials (a dedicated test integration
  user or OAuth client) exist only on the test site; nothing is issued on
  production. The colleague's sign-in account is in the shared authentik,
  bound to the test application only. Test-only accounts and keys must
  survive the production-to-test refresh (re-created after each refresh,
  secrets kept outside Git). Outbound mail/WhatsApp quarantine applies.
- **Data.** The test site holds a copy of production business data; the
  owner decides what the colleague's test role may see (or whether to mask).
- **Done 18 November 2026 (owner request):** in authentik, new group
  "Test Site Access" (no rights of its own) now gates the seven test
  applications; "Unformat Users" inherits it, so existing users are
  unchanged. The two colleague accounts moved to "Test Site Users" (child of
  "Test Site Access"), out of "Unformat Users"; one was also removed from
  "authentik Admins". Verified with authentik's policy engine: colleagues can
  open only the test applications; the owner keeps all. One colleague's
  production ERP sessions and active OAuth tokens (4 "<colleague's app>", 1
  "Raven Mobile") were revoked. Production ERP user records stay enabled,
  because the refresh copies them to test. Both colleagues added to the test
  refresh users (private profile). Before-state in
  `<rollback folder>` on production.
- **Revised the same day (owner):** the colleague is also a regular user, so
  both accounts are back in "Unformat Users" (production and test, rights
  defined in ERPNext) and out of "Test Site Users"; authentik admin rights
  stay removed. The app's production OAuth client stays blocked (below).
- **Replaced 19 November 2026 (owner):** test access now comes only from one
  flat group "Testers" bound directly to the seven test applications (no
  inheritance); "Test Site Access" and "Test Site Users" were removed. For
  now Testers = all enrolled users except <user> and <user>; the owner adds or
  removes testers. See the production release log.
- **Open:** the app's OAuth client ("<colleague's app>") still exists on
  production; to make the app unable to use production, disable it there
  and re-create a test-only client after each refresh (owner decision).
  Blocked on production 18 November with owner approval (redirect URIs set
  to `urn:blocked:production-test-only-app`; before-state in
  `<rollback folder>`). Each
  refresh copies the blocked client to test; the test bootstrap (run after
  every refresh) restores its redirect URIs from the private profile's
  `test_oauth_clients` (`a2bbaf7`, applied 18 November). The app keeps its
  client ID and points at https://test.example.com; users sign in again
  after each refresh.
- **Form e-mails on test:** owner approved real sending. Implemented
  (`3606926`): forms only, dedicated account, `[TEST]` subject and banner;
  also fixed the test copy silently dropping form e-mails. **Enabled 18
  November:** send-only `test-forms-noreply@example.com` created on production
  with `integrations/mail/smtp_senders.py` (app password limited to tailnet
  traffic, root-only credential file), password moved directly to the test
  VM's private profile; test egress allows only production mail
  100.64.0.10:465; TLS verified for mx.example.com; SMTP login accepted.
- **Contributions.** The repository is private on a free plan, so branch
  protection is unavailable. Use read access + fork + pull request: only the
  owner merges. Reviewed changes go to test first; production is promoted
  only by the owner's confirmation (production fetches read-only and changes
  only through the documented promotion).

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
  "waiting to send" state.
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

### P64 — Native app sign-in on production: latent auth-hook crash and a stale client list

**App:** mobile · **Also touches:** signin, erp · **State:** open

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
