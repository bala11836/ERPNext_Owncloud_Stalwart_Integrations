# ERP Mobile: build guide for agents and developers

The one guide for building the native app in this module. **Order of authority:** the repository's `AGENTS.md`
(binding for everything), then this guide, then `mobile/AGENTS.md` (Expo basics), then any other document.
Externally written plans (for example the "complete build guide" from another AI tool, 22 November 2026) are
background only; where they differ from this guide, this guide wins (section 13 lists the known differences).

Status: owner decisions of 22 November 2026; nothing in sections 6 to 12 is built yet unless marked **exists**.

## 1. Owner decisions (22 November 2026)

1. One universal app name, **ERP Mobile**; no company name in code, assets or docs.
2. Bottom tabs **Today · Inbox · My HR · Menu** (replaces the earlier Work/Chat/Mail/Drive layout of P50).
   **No Chat, Mail or Drive** in the app: they are separate apps, and the Menu has no links to them.
3. **Web parity by role:** everything a person can do on the web (all their DocTypes, onboarding forms, reports
   they may open) is possible in the app. Hand-designed screens for the top daily tasks; every other DocType
   through the generic form engine built from ERPNext's own metadata.
4. **Incident report:** a pop-up to pick the kind, photos, the person chooses one or more Raven threads (channels
   they belong to), the post carries a colour code and banner so others notice at once. The lock-screen text of
   the resulting notification may name the incident kind and the site, never a person. No separate safety
   register for now.
5. **Approval limits** (delegation of authority) and which document a project manager raises for payments:
   decided by ERPNext and its workflows; the app shows and performs the workflow actions ERPNext allows.
6. **English only** for now; every screen text goes through one translation file so languages can be added.
7. **Self check-in outside the site fence is refused** (by the server).
8. **Remote wipe** of a phone when its account or device is disabled; data may stay offline at most **1 day**.
9. iPhone distribution through **TestFlight** (needs the Apple Developer account; the owner says when it is
   bought). Android: signed APK.
10. Oldest supported phones: Android 9 and later, iPhone 11 and later.
11. **No crash reporting service** for now.

## 2. Hard rules

**Process** (from the repository's `AGENTS.md`; never skip)
- No change of any kind until the owner says "go"; a "go" covers only the item asked. One branch and one pull
  request per item, to `main`; the maintainers test the branch on the test site; the owner merges.
- Server code lives only in the existing Frappe app `erpnext_drive_integrations` (DocTypes as JSON in the app,
  patches, whitelisted methods). Never create a second Frappe app, never create or edit DocTypes, workflows or
  settings by hand on a server.
- The public repository holds no real company, people or project names, hosts, addresses or data. Sample data
  uses neutral placeholders ("Worker A", "PRJ-0001", "Site 1").
- Never print secrets; nothing secret in the app bundle (only `EXPO_PUBLIC_*` values, which are public).
- New npm packages: through `pnpm exec expo install` (SDK-matched); at least 3 days old; install scripts stay
  blocked (`mobile/pnpm-workspace.yaml`); check licence and maintenance first. Never run `npx <package>` for a
  package that is not pinned in this project (the Expo EAS skills say `npx --yes eas-cli@latest`: pin `eas-cli`
  as a dev dependency and use that). Builds, TestFlight or store submissions and over-the-air updates only with
  the owner's explicit go.

**Security and data**
- ERPNext decides every permission. Hiding a screen is not security; the server must refuse.
- The app runs every request as the signed-in person. No API keys, no service accounts in the app.
- Notifications and Live Activities carry no names, amounts, vendor or bank details.
- Money: amounts come computed from the server and are only displayed (Indian format `₹ 1,50,000.00`); no
  floating-point arithmetic on money in the app.
- Submitted documents are cancelled or amended through ERPNext, never deleted.

**Interface**
- Light theme only; text contrast at least 7:1 (`scripts/check-contrast.ts`); touch targets at least 48 dp,
  primary buttons 56 dp; status always icon plus word; one-tap Outdoor Mode; readable at large system font sizes.
- Phone: bottom tabs and a floating "+" button. Tablet (600 dp and wider): side rail instead of tabs, list and
  detail side by side; landscape gets three panes where useful.

## 3. How the agents work (every item)

Installed on the owner's PC (read before installing): plugins `feature-dev`, `pr-review-toolkit`,
`typescript-lsp` (Anthropic, Apache-2.0); skills from Expo (`expo-overview`, `expo-router`, `expo-data-fetching`,
`expo-native-ui`, `expo-ui`, `expo-design-system`, `expo-animation`, `expo-dev-client`, `expo-module`,
`expo-project-structure`, `eas-app-stores`, `eas-update`, `eas-workflows`, `expo-upgrade`) and Callstack
(`react-native-best-practices`, `react-native-testing`, `github-actions`). Built in: `/code-review`,
`/security-review`, `/simplify`.

1. **Explore** (`feature-dev` code-explorer): read the existing app, `portal/mobile.py`, the APIs and DocTypes the
   item touches. Report file:line facts, not assumptions.
2. **Design** (`feature-dev` code-architect, with `expo-overview` loaded first): one plan with the files, the
   screens, and for every custom feature its **data path** (which API receives it, which DocType stores it, where
   its photos go, how a retry avoids duplicates; section 7). Check current Expo docs for the SDK in
   `package.json`, never memory.
3. **Owner go** on that plan (plain words, numbered questions).
4. **Build** in small commits; tests in the same commit as the code they cover.
5. **Check:** `pr-review-toolkit` (code-reviewer, silent-failure-hunter, type-design-analyzer, comment-analyzer),
   `/code-review`, `/security-review`; fix what they find or say why not.
6. **Test** (`pr-test-analyzer`, `react-native-testing`): unit and component tests; Maestro flows for the main
   paths once they exist; `pnpm typecheck`, `pnpm lint`, `pnpm test`, and the repository's
   `tools/check_repository.py` and `tools/run_unit_tests.py`.
7. **Pull request** with the template filled in (what and why, promotion plan, tests, what the test site must
   check, real devices). The maintainers test on the test site and real phones; the owner merges.

The `code-simplifier` agent may edit code by itself: use it only on code written in the current, approved item,
and this repository's conventions win over its defaults.

## 4. What exists today

App (`mobile/`, Expo SDK 58, Expo Router, TypeScript strict, pnpm):
- **Sign-in (exists, do not replace):** passkey in the phone's system browser at the sign-in server, then
  ERPNext's own OAuth with PKCE S256 (public client, no secret). The ERP token is bound to the browser sign-in on
  the server (`erpnext_drive_integrations/portal/mobile.py`): signing out on the web ends the app's access; the
  site setting `cloud_native_mobile_clients` lists the accepted app clients. The app sends that ERP token as a
  Bearer token; authentik tokens are never sent to ERPNext.
- App lock (Face ID, fingerprint or passcode on start and after 60 s in the background), blank cover in the app
  switcher, sunlight palette with the contrast check, Indian number format, tablet split view, generic lists and
  records from DocType metadata, role-filtered menus from `onboarding/api.py` `bootstrap`.
- Placeholder tabs Home, Approvals, Inbox, Settings (to become Today, Inbox, My HR, Menu).

Server (`erpnext_drive_integrations`):
- **Field attendance (exists):** DocTypes Field Site (with `latitude`, `longitude`, `radius_m`,
  `maximum_accuracy_m`), Field Attendance Entry (with `request_id` against duplicates, photo, location, accuracy,
  check-in, automatic check-out), Field Worker Assignment, Field Shift Allocation, Field Assignment Event,
  Field Site Member, Field Site Asset; whitelisted methods in `field/api.py` (`bootstrap`, `team`, `entry`,
  `approvals`, `save_capture`, `submit`, `review`, `move`, `setup_options`, `create_shifts`, `save_site`,
  `unassigned`, `enroll`, `my_records`).
- Web push for the browser portal (`portal/push.py`, device registry on the server); native push does not exist
  yet.
- Raven is installed on the same ERP site.

## 5. Architecture

- **Layers:** screens (display only) → hooks (one per use case) → one typed ERP client (`src/lib/erp.ts` grows
  into it) → offline queue. Screens never call `fetch` directly. Every server answer is validated against a
  schema before use; a malformed answer is an error shown to the person, never silently ignored.
- **Data loading and caching:** one query library with retries and cache (TanStack Query is the reference choice,
  as in the Bluesky app, which runs on the same SDK); vet the exact package at the Phase 0 PR. No Axios (the
  platform `fetch` is enough).
- **Local storage:** an encrypted database for the offline queue and cached records (for example `expo-sqlite`
  with its SQLCipher option), its key in `expo-secure-store` (Keychain / Keystore). Tokens only in
  `expo-secure-store`. Nothing sensitive in plain files or logs.
- **Folders:** keep the existing `src/app` (routes only), `src/components`, `src/lib`, `src/auth`, `src/theme`;
  add `src/features/<area>` for screens' logic, `src/i18n/en.json`. Do not restructure what works.
- **Forms:** one engine that renders a DocType from its metadata (field types, mandatory, depends-on, read-only,
  child tables, links with search); hand-designed screens reuse its field components.
- **Approvals:** ERPNext's `frappe.model.workflow.apply_workflow` (never write `workflow_state` directly); the
  Inbox lists the person's open Workflow Actions and notifications. Face ID before Approve, Reject, Submit and
  Pay.
- **Native features** (Live Activities, Android Live Updates): config plugins and Expo modules only; never edit
  generated `ios/` or `android/` folders. They need a development build, not Expo Go.

## 6. Product specification (from Master Plan v2, owner-reviewed)

- **Three steps:** entry (functional employee) → verification (next-level incharge, where the department has
  one) → approval (project manager). The same person never does two steps of one document. Head office handles
  procurement and payments. Escalation above limits as ERPNext's workflows define.
- **Departments and roles** (17 project roles): Civil (supervisor → engineer → PM), Survey, Billing & Planning,
  Mechanical (supervisor → engineer → PM), Stores (executive → incharge → PM; fuel logged by a designated
  executive), Accounts (cashier), HR (executive), Field Attendance (supervisor marks team), Self Attendance
  (everyone; PM approves in bulk), Canteen, Safety (incl. permits to work), Quality, Plants (equipment),
  Administration (security supervisor: gate passes, visitors, material exit). Head office: functional managers,
  procurement, finance, HR, VP, CFO, CEO/MD. Role names map to ERPNext roles; the mapping lives on the server,
  not hard-coded in the app.
- **Today:** cards per role (for example a supervisor's team attendance, a PM's approvals waiting by department,
  alerts such as a permit expiring), grouped by department for people with several roles; a common "Waiting to
  send" card.
- **"+" (quick capture):** the person's capture actions across all their roles; the last item is always
  Incident.
- **Inbox:** approvals and verifications waiting, notifications, badge count.
- **My HR:** own attendance, leave balance and applications, expense claims (with photo), payslips.
- **Menu:** search, the person's modules, settings (Outdoor Mode, language, app lock, notification categories,
  version, sign out), help.
- **PM bulk approval:** list with select all and "exceptions only", photo, location and time per entry, one Face ID
  for the selection.
- **Push texts** (generic only): "New approval waiting", "Attendance returned for correction", "Permit expiring in
  1 hour", "3 items waiting to send", "Leave application updated". Tap → app lock → the record. An explanation
  screen before the system permission prompt; per-category switches.
- **Dynamic Island / Live Activities (iOS) and Live Updates (Android 16; ongoing notification on older Android):**
  approvals waiting (count), sending progress, permit-to-work countdown, shift timer. Phones without a Dynamic
  Island show the lock-screen card.

## 7. Data paths: how each feature is received and stored

Nothing is stored only in the app: every record lives in ERPNext, so the web shows the same data and approvals.

| Feature | Received by | Stored in | Photos | Retries / offline |
|---|---|---|---|---|
| Incident → Raven | Raven `raven.api.raven_message.send_message_with_attachments` (files uploaded first) | Raven messages in the ERP database, one per chosen channel; Raven checks membership | ERP files, private | Raven's `client_id` is its idempotency key (one per channel) |
| Supervisor attendance | `field/api.py` (`save_capture`, `submit`, `review`, ...) | Field Attendance Entry (**exists**) | attached | `request_id` (**exists**) |
| Self check-in | new whitelisted method in `field/`: checks the fence of the person's Field Site on the server, refuses outside or with poor accuracy | ERPNext Employee Checkin (verify its location fields in the pinned HRMS) or Field Attendance Entry | optional | client ID |
| Leave, expense claim, payslip | standard REST / methods as the person | Leave Application, Expense Claim, Salary Slip | attached | client ID |
| Stores: request, receipt, issue, count | standard | Material Request, Purchase Receipt, Stock Entry, Stock Reconciliation | attached | client ID |
| Equipment breakdown, maintenance | standard | Asset Repair, Asset Maintenance Log | attached | client ID |
| Quality | standard | Quality Inspection, Non Conformance | attached | client ID |
| Fuel | standard if it fits machines, else custom | Vehicle Log, or a custom Fuel Log | meter photo | client ID |
| Daily progress report, hindrance, permit to work, toolbox talk, gate pass, visitor log, material exit, canteen meals, survey measurement | new whitelisted methods | **new DocTypes in `erpnext_drive_integrations`**, each its own P item, with an ERPNext workflow | attached | client ID |
| Joint measurement, RA bill | later (large module) | new DocTypes | | |
| Any offline create | the queue sends when online | a small server-side log of client IDs → created document, so a retry returns the same record | | |
| Push and Live Activity tokens | new whitelisted method | a "Mobile Device" record per phone (person, platform, tokens, last seen, disabled); disabling it revokes tokens and makes the phone wipe itself | | |
| Today cards, Inbox | server methods reading existing data | nothing new | | |
| Outdoor Mode, lock time, last tab | | the phone only | | |

The standard DocTypes named above are candidates: confirm each against the pinned ERPNext and HRMS before
designing on it, and prefer them over new DocTypes.

**Incident banners:** Raven stores message text as HTML and cleans it. Try on the test site whether colour
survives; otherwise use a severity emoji and a bold first line ("🔴 INJURY · Site 1 · 14:30"), then the
photos. The first line names kind and site only (it appears on lock screens).

## 8. Offline

- Every create is saved locally first (encrypted), with a unique client ID; the queue sends in order when
  online; photos are compressed to about 1 MB; the person sees "Waiting to send" with a count.
- A server change since the local copy is shown to the person as a conflict, never overwritten.
- Local data older than **1 day** is removed; everything is removed at sign-out (with a warning and "send now" if
  items are waiting) and when the server reports the account or device disabled.
- The phone's clock is not trusted: the server stamps times; location comes with its accuracy; on Android, mock
  locations are detected and rejected.

## 9. Security baseline (OWASP MASVS, level 1 plus the parts below)

Encrypted storage with keys in Keychain / Keystore; TLS only; no secrets in the bundle; Face ID per approval with
passcode fallback; screenshots and the app-switcher preview blocked on sensitive screens (payslip, approvals);
permissions only when needed (camera; location while the app is in use); remote wipe; session end when the web
session ends (exists); no personal data in logs; dependencies pinned and reviewed. Certificate pinning and
root/jailbreak detection: decide at the security review before the first release.

## 10. Devices and quality gates

- Real devices before every release: iPhone with and without Dynamic Island, iPhone 11, a recent Android, an older
  budget Android (2-3 GB memory; check battery-saver behaviour of Xiaomi, Oppo, Vivo), an iPad, an Android tablet.
- First screen in under 2 seconds on the budget Android; smooth lists (virtualised); works at 360 dp width and at
  the largest system font size.
- Gates per pull request: `pnpm typecheck`, `pnpm lint`, `pnpm test`, repository checks, the review agents, and
  tests for every behaviour the change adds.

## 11. Phases (each: owner go → branch → PR → test site → merge)

0. **Foundation:** the review and test setup (component tests, the first Maestro flow), the ERP client with schema
   checks, the encrypted store and queue skeleton, `en.json`, pinned `eas-cli`; no new screens.
1. **Shell:** tabs Today, Inbox, My HR, Menu; side rail on tablets; project selector (assigned projects only);
   settings; the generic form engine (web parity).
2. **Server groundwork:** Today cards and Inbox methods, the Mobile Device record and remote wipe, the client-ID
   log.
3. **Pilot, attendance:** supervisor marking (existing field APIs), self check-in inside the fence, PM bulk
   approval with Face ID, offline sending; real devices.
4. **Incident → Raven** (banner check on the test site first).
5. **Push, then Live Activities and Android Live Updates** (needs the development build and, for iPhones, the Apple
   account).
6. **Department modules,** one P item each (Stores, Civil, Safety, Administration, Quality, Plants, Canteen,
   Accounts, HR, Survey, then Billing & Planning), then the management dashboards.

## 12. Acceptance (for the whole app)

Every role sees its own Today, Inbox, My HR and Menu; three-step approvals work through ERPNext's workflows;
offline captures arrive once; the PM's bulk approval works; incidents reach the chosen Raven threads; contrast,
touch targets, Indian money format and dates (21 Nov 2026) everywhere; Face ID on approve, reject, submit and
pay; app lock and blank cover; generic push texts with per-category switches; Live Activities and Android
equivalents; phone and tablet layouts; Outdoor Mode; no real data or company name anywhere; the device list in
section 10 passes.

## 13. Known differences from the externally written guide

That guide is not to be followed where it says: create a new Expo project (build on this module); sign in with
authentik tokens sent to ERPNext (section 4 is how sign-in works); `bench new-app field_operations` or create
DocTypes in the ERPNext UI (section 2); new Field Site / Field Attendance Entry / Batch (they exist, section 4);
its own Quality Inspection or NCR (standard DocTypes exist); `raven.api.send_message` (section 7); approve by
writing `workflow_state` (section 5); WatermelonDB (not encrypted; section 5); a fence warning only (refused,
section 1); Telugu and Hindi now (English only); `bench list-doctypes`, `show-workflow`, `show-permissions` and
API-key logins for checks (they do not exist or do not apply; use the tests and the test site).
