# P list: roadmap and work items

> **Generated file: do not edit by hand.** This is the project's work list (every "P" number used in
> commits, pull requests, READMEs and `docs/decisions.md`) published from the maintainers' private
> list on 21 November 2026, with every line kept. Only these categories are replaced, by placeholders: the
> deploying organisation's name (`<tenant>`), host names (`example.com`), IP addresses
> (documentation ranges), server file paths and rollback folders, mail addresses, names of people and
> of third parties' internal products, business file names, and links to private records
> (marked "private record"). Everything else (scope, status, reasons, design, evidence, priorities)
> is unchanged. Changes are made in the private list and re-published; to propose a change or
> take up an item, open a pull request or an issue that names the P number.

> Sanitized current pending list. Package consolidation does not imply completion of these independent provider/device tasks.

# Pending tasks — current reconciled list

Updated **16 November 2026 (Asia/Kolkata)** after auditing the retained deployment and the repository-built isolated test workspace. See [current retained setup](retained.md) and [test acceptance](test-acceptance.md). Items below distinguish incomplete implementation from unverified acceptance. No dates or automations have been scheduled by this document.

The eight selected topics from the previous repository are reconciled in the [carried-forward roadmap](roadmap.md), including what is already deployed, superseded or still requires a decision.

## How to use this list (owner, 21 November 2026)

A **P item** is one self-contained unit of work with a number, a status and a clear scope
(why, what, how it is tested, what it depends on). The numbers never change and are never
reused; commits, pull requests, release records and handovers refer to them (P58, P60).

- **Related P items are taken up together.** When several items touch the same module,
  stack or decision, they are built on one branch, tested on the test site together and
  merged as one release, so a stack is changed once and not several times. The items stay
  separate in this list (each keeps its own status and history) while the release names
  all of them.
- **Why:** development stays modular (one module, one purpose, reusable on its own), and
  connectivity between sessions is simple: a new session, a new contributor or an AI
  agent reads this file, picks an item or a related group and knows its scope, status and
  dependencies without the earlier conversation. Records need not be re-explained.
- **How a group is chosen:** shared module or stack, shared test, shared production
  promotion, or one depends on the other (the Priority order below shows dependencies).
  Examples, not a plan: P60 with P59 (route files and promotion plan); P49 with P45 and
  P08 (sign-in stack and logout); P13 with P25 (users and enrollment); P12, P15 and P19
  (mail delivery, health and migration); P29, P30 and P48 (mesh, DNS, router); P50 with
  P14 (mobile app and push).
- **Public copy (owner, 21 November 2026):** this list is published in full as `docs/p-list.md` in
  the public repository so the team can see the roadmap. Every time this file changes, regenerate it
  with `tools/publish_p_list.py` (private rules in `tools/publication-rules.private.json`) and open a pull
  request. **Never skip details:** the tool replaces text inside lines only, never removes or summarises a
  line, and writes every substitution to `docs/publication/last-report.md`; only the sensitive categories
  in the rules are replaced; the leak scan must be clean and the report read before the pull request.
- **Rules that stay:** the owner decides what starts and when; every group still follows
  branch, test, merge, `main`, production (`AGENTS.md`), and the release record names
  every P item it carries, the tested commit and the rollback point. When an item is
  done, mark its status here in the same session.

## Priority order (assessed 21 November 2026; the owner adjusts, then we work from the top)

Ranked by: (1) live defect or outage risk, (2) security and data loss, (3) what blocks
people from using the system (user rollout), (4) dated deadlines, (5) dependencies,
(6) effort. Items marked **owner** were prioritised by the owner. Nothing here starts
until the owner says; the table only fixes the order to take them up.

**Tier 0: in flight or owner priority (take up first)**

| Rank | Item | Why now | Depends on / note |
|---|---|---|---|
| 1 | **P61** editor file safety | production business data: a shared workbook became unusable and edits were parked unsaved (20 Nov); owner request | start with the unstick and rescue tool; relates to P57, P59 |
| 2 | ~~PR #12 private sheet views~~ **live 21 Nov (`2c542f0`)**: sheet-view crash guard, repair tool, one-attempt keeper | done; P61 keeps the remaining safeguards | owner to open the the shared workbook files on production |
| 3 | **P60** portal `/ezone` (**owner**, high) | owner priority; plain rename | P59 helps; production-only route files |
| 4 | **P59** promotion plan and drift check | a stack was missed in the 21 Nov promotion; prevents repeats | none; do before the next multi-stack release |
| 5 | **P57** survive reboots (PR #7 open) | production lost Drive editor, proxy entry point and Mail sign-in after one reboot | add the Stalwart reload step; reboot drill on test; no production reboot as a test |

**Tier 1: high (business-critical, next)**

| Rank | Item | Why | Depends on / note |
|---|---|---|---|
| 6 | **P62** daily upstream watch (releases, security flaws, upgrade advice) | security: new flaws and fixes reach us only by chance today; advice only, no automatic upgrades | none; baseline first, dry-run a week; owner may place it higher |
| 7 | **P49** sign-in pages and templates into the repository (finishes P45) | a claim-name mismatch already caused an ERP sign-in outage (20 Nov); authentik settings (JIT, memory, brand, flows) live only in its database | P45 remainder; rehearse on test |
| 8 | **P08** global logout and fresh passkey, end to end | security acceptance; parts verified 21 Nov (logout ends the session; passkey is asked, Bitwarden answers silently) | owner checks each app as initiator |
| 9 | **P13** remaining users, permissions, worker enrollment | adoption: 10 of about 20 users | P25 |
| 10 | **P25** invitation, passkey enrollment and recovery acceptance | needed before more users join; lost-device recovery untested | real SMTP and devices |
| 11 | **P12** PTR and external mail delivery; **P15** SMTP health | mail is live but external delivery is unverified; PTR still the provider's | provider (the hosting provider); blocks P19 |
| 12 | **P11** certificate renewal acceptance | dated: ERP, SSO, Drive, Respond expire **30 Jan 2027**; Office, Mail, DMS in February | do well before January |
| 13 | **P24** field attendance pilot and corrections | real workers waiting on acceptance | business rules for cancellation |
| 14 | **P43** tablet layout and touch check | tablets will be used (ONLYOFFICE touch is view-only) | test site |

**Tier 2: medium (planned, useful, not urgent)**

| Item | Note |
|---|---|
| **P50** native mobile app | strategic; planning only, many open decisions (look, security, notifications, build order); pilot is HR attendance |
| **P63** demo mode for the test site (neutral UN/format brand, line-art landing page, no tenant traces) | owner request 21 Nov; needs colour options chosen; open question on the shared sign-in brand |
| **P05**, **P06** GSTIN lookup and PAN checks | blocked on the India Compliance API secret and a PAN verification source |
| **P03** eKYC (Digio), **P04** WhatsApp | blocked on provider accounts; P04 also needs a Meta business number |
| **P51** data refresh at 8 pm; **P54** branch deploy button | P54 blocked until the first crippled refresh passes its audit; P51 owner said later |
| **P20** Paperless links on ERP transactions; **P21** correspondence register | needs agreed fields and roles |
| **P16**, **P17**, **P18** Raven attachments, Drive links for big mail attachments, mail client policy | P18 is a discussion first |
| **P09**, **P10**, **P14** fullscreen, desktop and phone sync, push acceptance | small to medium acceptance work on real devices; P14 follows P50 |
| **P26** banking and payroll sandbox | needs sandbox accounts; no live transfers |
| **P28** dual approval for super-administrator | owner deferred the model |
| **P31**, **P32**, **P07** keyboard navigation, native-module navigation, UI coverage | usability; P31 and P32 share design |
| **P23** PWA offline | audit first |
| **P41** quarterly recovery check | recurring: next due **18 Feb 2027** |
| **P40** remainder (offline USB copy, test VM settings backup, tailnet rule) | hardening; backups already live |
| **P35** presentation polish and upstream sharing | module READMEs, forum and tracker posts |

**Tier 3: low or later**

| Item | Note |
|---|---|
| **P19** three Google mailboxes to Stalwart | after P12 is resolved |
| **P22** AI assistant | read-only first; provider and data policy undecided |
| **P29**, **P30**, **P48** Headscale, Technitium DNS, branch router | one chain, P48 depends on P29 and P30; nothing is broken today |
| **P46** TrueNAS NVR | hardware and selection first |
| **P53** Desk widgets and universal search | **parked by the owner**: do not start |

**Done or closed (no action):** P02, P27 (obsolete), P33, P34 (superseded), P36, P37, P38
(closed), P39, P42, P44, P47 (live), P52, P55, P56 (live), P58 (live `3a93de8`); P01 is
live since P37 (owner to say if idle freezes come back).

Note: two headings are numbered P56 in this file (the original request and its
implementation); they are the same item.

## Explicitly deferred

### P01 — Idle menus and real-time connection recovery

**Status:** reactivated 16 November 2026 after an owner report (menus freeze after idle/sleep; reload fixes). Likely cause: the 8-hour SSO proxy session lapsing while Frappe's session stays valid. Client recovery committed in `session.js?v=20261116-idle1`; awaiting deployment and long-idle validation on permanent test. Socket.IO origin fix still open.

- Correct Frappe/Raven Socket.IO “Invalid origin” failures without disabling authentication or origin checks.
- Add bounded session validation and recovery on browser resume, network return and portal app reactivation; restore real-time connections and menu handlers as needed.
- Clearly distinguish expired sign-in, offline/network failure and server errors. Preserve unsaved work; avoid unconditional periodic reloads.
- Verify long inactivity, computer sleep and network interruptions across ERPNext, HR, Onboarding, India Compliance, Framework, Raven and Insights.
- Short retained-page tests do not establish overnight reliability. The complete long-idle menu freeze's root cause is not conclusively isolated.

Evidence and proposed implementation: [idle investigation](idle-navigation.md).

### P02 — Off-server backups and restore test

**Status:** done and live since 18 November 2026: nightly encrypted backups, weekly drill, full restore rehearsals (P39, P44) and tamper resistance (P40). History of the setup follows. Scheduled by the owner (18 November 2026) as step 3, before the P37 production ERP move ("backup first"), after the relay and test-site acceptance. Destination confirmed by the owner: the S3-compatible bucket on the home TrueNAS, reached over the tailnet (see test host migration (private record)).

Choose the destination, approve any storage cost, configure encryption/retention, and test recovery of ERP, authentik, Drive, DMS, Mail and custom configurations.

**Live 18 November 2026:** first production backup succeeded (Drive paused
14 s, Mail 5 s) and the restore drill from the test VM passed (ERP 1,055,
DMS 75, identity 230 tables; 54,025 files; about 41 minutes over the
tailnet). Nightly timer on production (02:30 server time, randomized up to
15 minutes), weekly drill on the test VM (Sunday 05:00), daily ZFS snapshot
on TrueNAS (10:00, keep 60). Recovery time from the home NAS is bounded by
the home upload speed; P39 measures it.

**Implemented 18 November 2026:** module `integrations/backup/` (Restic 0.18.0
by digest; online database dumps; brief stop-and-copy for Drive and Mail;
7 daily/4 weekly/6 monthly; weekly `check`; restore drill on the test VM with
a read-only key). To activate: RustFS bucket + read-write key (production)
and read-only key (test VM); encryption password in the owner's password
manager and a root-only file; `init`; first run and drill; then timers. Existing local archives/volumes are rollback material, not off-server backup protection.

## Implementation still due

### P03 — Employee eKYC India

**Status:** official source staged; app not installed in production. No Digio account is ready.

Confirm compatibility with the running Frappe/ERP versions, install and configure eKYC India, establish the provider account/credentials and any required commercial approval, then verify the employee identity workflow and access controls. Do not describe staged source as an installed or usable integration.

### P04 — WhatsApp onboarding and vendor/PO replies

**Status:** official source staged; WhatsApp app/connector not installed. No Meta WhatsApp Business account or business number is ready.

Set up the provider/business number, deploy/configure the connector, prepare approved message templates and webhooks, and implement authenticated reply-to-record mapping. Verify sending onboarding links and recording vendor yes/no responses against the intended response request or PO with an audit trail. No live sending is currently established.

### P05 — Live GSTIN lookup and form prefill

**Status:** lookup/prefill code exists and calls India Compliance; end-to-end acceptance is incomplete.

- GST API use is enabled, but the configured API secret is absent in the final audit.
- Configure the India Compliance account/API secret and required credits/usage approval.
- Verify successful and invalid GSTIN cases, legal/trade name and address mapping, PAN extraction, error/fallback behavior and lookup limits on an actual vendor form.
- Existing GSTIN format/check-digit validation is not a completed live-lookup acceptance test.

### P06 — PAN verification and automatic constitution deduction

**Status:** partly implemented, partly outstanding.

Existing checks cover PAN syntax, GSTIN/PAN consistency, and whether the PAN type character matches the selected constitution. Still due:

- Deduce/prefill constitution from the PAN type character, with handling for ambiguous categories and controlled correction.
- Choose/configure an authorized live PAN verification mechanism and test valid/invalid cases.
- Keep local format/type checks visibly distinct from verified identity/status.

### P07 — Remaining Frappe UI coverage review

**Status:** final shared menu is deployed in native Desk apps; Raven/Insights retain their separate native SPA navigation.

Reconcile the user's “all Frappe apps” request against these separate interfaces. Any equivalent shared-action/module layout for those SPAs needs a per-app mapping; it has not been implemented. Do not treat Desk-hook coverage as proof of identical navigation across every installed Frappe-based app.

## Deployed, but final acceptance still due

### P08 — Latest global logout and fresh passkey sign-in

**Status:** earlier ERP-initiated cross-app logout passed; latest hardening is deployed but not fully accepted end to end.

Verify the final outpost/full-user logout flow ends ERP, Drive, Mail and DMS sessions, reaches the clear signed-out page, and requires a fresh passkey when Sign in is selected. Repeat with each independent app as logout initiator, including multiple open app tabs. Preserve drafts and do not remove authentication protections to make a test pass.

### P09 — Portal fullscreen toggle

**Status:** home-logo toggle is implemented; manual browser acceptance is unconfirmed.

A previous automated click reported fullscreen unavailable. Verify a real user click enters and exits fullscreen in the target desktop browser, then check touch/mobile behavior or provide an appropriate fallback if unsupported.

### P10 — Desktop/iPhone Drive and calendar/contact clients

**Status:** native ownCloud desktop synchronization is available and Drive web/Desktop/iOS SSO clients are configured and display Drive; actual device/folder-sync completion is not established after the hostname changes. A new custom desktop-sync implementation is not pending.

- Verify ownCloud iPhone sign-in, callback and file access using https://drive.example.com/.
- Choose the Desktop local sync folder and verify actual upload/download synchronization; preserve existing local files.
- Check required desktop platforms, shared folders/Spaces, offline conflicts, rename/delete propagation, interrupted transfers and token revocation. Server revocation does not erase local downloaded copies. See [desktop reconciliation](roadmap.md#4-native-drive-desktop-synchronization).
- Verify native CalDAV/CardDAV discovery, authentication and synchronization on the intended devices. Earlier server protocol round trips passed, but device acceptance remains due.

### P11 — Certificate issuance and renewal acceptance

**Status:** current HTTPS validation passes; ERP/SSO automation is configured, but renewal/individual issuance has not been accepted.

ERP, SSO, Drive and Respond currently present certificates expiring **30 January 2027**. Confirm the active renewal mechanism covers all four names, issue/renew through the intended configuration, and verify the served certificate afterwards. Office, Mail and DMS currently have February 2027 expiries. Do this before the January expiry; no reminder has been scheduled.

### P12 — PTR and external mail delivery

**Status:** provider request pending and external deliverability unverified.

The final audit still returned PTR `provider-host.example.net` for 203.0.113.10, rather than mx.example.com. Follow up with the hosting provider, verify matching forward/reverse DNS and mail authentication, then test external reception/sending and delivery results. Earlier internal mail and SMTP envelope tests are not proof of external deliverability.

### P13 — Remaining users, app permissions and worker enrollment

**Status:** ten users are in the shared sign-in group; the intended twenty-user rollout is incomplete.

- Enroll the remaining intended users and verify ordinary-user access in each app.
- Complete first Drive/DMS sign-ins and per-owner document-worker enrollment; only the previously enrolled user/shared Space is verified.
- Assign mailbox membership/read/send access separately. The current personal/shared mailbox mapping is for the existing account, not every group member.
- Verify ordinary users can access shared business files while other users' personal files and private Paperless documents stay private.

### P14 — Retained mobile/browser push acceptance

**Status:** approved-session OAuth/PKCE binding, refresh/revocation and push modules are retained; current-stack native Raven and fresh-device acceptance remain incomplete. Earlier ERP/HR notification receipt is recorded at its earlier deployment checkpoint, not re-certified on the current portal.

Verify the new portal's per-device opt-in controls, ERP/HR notification receipt and tapping, and Raven background delivery from another user on actual devices. Native relay credentials and registrations stay private. Mocked tests and a provider HTTP success do not prove device delivery. No notification test or business approval message was sent during consolidation.

Recheck native Raven login/chat/refresh and revoked-token refusal, and coordinate realtime recovery with P01. Preserve exact validated callbacks and existing workers/drafts. See [push and Raven scope](roadmap.md#1-push-and-session-bound-native-raven).

### P15 — Existing SMTP health alerts

**Status:** pre-existing email-health alerts were visible during browser acceptance; current delivery health was not re-certified by package consolidation.

Inspect the latest native SMTP/queue errors and the hourly monitor, verify the sole integration sender using an authenticated TLS/NOOP test, and distinguish stale alerts from a current failure. Earlier envelope checks and the working web inbox do not prove current outbound mail. Coordinate a real send/receipt acceptance test when scheduled.

## Carried-forward development and decisions

### P16 — Raven attachments and Drive storage integration

**Status:** planned; current Mail picking and Drive-to-Paperless processing do not implement Raven attachment storage.

Audit actual attachment growth and upload paths; design supported single-copy references where feasible, channel/project ownership, native permission enforcement and revocation. Agree quotas/accounting, retention, deletion/shared references, storage and recovery before implementing or migrating data. Keep live chat messages in Raven/Frappe. See [detailed scope](roadmap.md#2-raven-attachment-storage-and-drive).

### P17 — Automatic Drive links for Mail attachments over 200 KB

**Status:** not implemented. The deployed Files picker transfers bytes into an ordinary email attachment, with a 25 × 1024 × 1024 byte limit. It does not enforce a 200 KB threshold or create expiring links.

Carry the earlier requirement for both outgoing and incoming attachments, implemented through supported current Mail/Stalwart and Drive paths. External access uses expiring bearer links without sign-in; forwarded links remain usable until expiry/revocation. Decide expiry, threshold units/per-file versus aggregate sizing, inline/small attachment behavior, access auditing and cleanup. Preserve signed/encrypted incoming originals and agree raw MIME retention/storage accounting. Server-side enforcement, permission/failure/retry tests and external-recipient acceptance remain due. See [Mail scope and evidence](roadmap.md#3-mail-attachments-and-mail-access-policy).

### P18 — Allowed Mail clients and protocol access policy

**Status:** discussion required; the previous “suite-only” wording is not a selected policy for the new stack.

Discuss portal/webmail versus native Mail clients and required JMAP/IMAP/POP/submission/DAV access. Preserve current authenticated public Mail/private administration, SMTP reception, ERP/authentik SMTP sending and required integrations while deciding. Do not disable endpoints or alter exposure from this note. See [access-policy discussion](roadmap.md#access-policy-requiring-discussion).

### P19 — Three Google Workspace mailboxes to Stalwart

**Status:** planned migration; source identities, domain, sizes, destination mappings, tooling and cutover are not yet specified. This is separate from the earlier retired local-server no-migration decision.

Keep email, folders/labels and sent-mail scope; exclude contacts, calendars and Google Drive. Inventory and map source/destination access, plan deduplication and capacity/recovery, preserve source messages and historical MIME, validate initial/catch-up copies, then separately agree mail DNS cutover and rollback. Google Workspace cancellation or other-product changes are not authorized. No mail copying or DNS changes are started. See [migration scope](roadmap.md#5-three-google-workspace-mailboxes).

### P20 — Paperless document links on ERP transactions

**Status:** revised integration work pending; replaces the former direct object-storage/S3 task. Paperless and the Drive processing worker are already deployed, but the read-only ERP schema audit found no DMS/Paperless transaction-link fields.

Keep authoritative scans/OCR in Paperless and associate stable document IDs/links with ERP transactions through permission-checked upload/select/link flows. Agree eligible document classes, fields, shared references, retry/processing status and access/revocation behavior. Preserve historical associations and originals until any migration is copied, verified and accepted. Existing Drive originals are not deleted by this plan. Test previews, exports/printing/email dependencies and consistent ERP+DMS recovery. See [revised transaction design](roadmap.md#6-erp-transactions-reference-paperless-documents).

### P21 — Client/project correspondence register and DMS integration

**Status:** Paperless product selection/deployment is complete; the ERP correspondence register and its integration remain planned. No correspondence DocType was found in the read-only schema audit.

Agree client/project, incoming/outgoing direction, reference/date/subject, responsible employee, response deadline/status, reply chains, transaction/DMS links and physical-original location fields, numbering, workflow and roles. Coordinate with P20, preserve privacy and test an incoming letter/outgoing reply and outstanding-response pilot. Existing vendor response forms and OCR search are not a completed correspondence register. See [register scope](roadmap.md#7-clientproject-correspondence-register).

### P22 — Permission-controlled ERP AI assistant

**Status:** planned read-only-first evaluation/development; no model, provider data sharing, public tool endpoint or write authority is selected/enabled.

Agree pilot project reports, approvals and attendance summaries; evaluate installed native Frappe tool interfaces; enforce caller-bound native roles/document/field access and a server-side tool allowlist. Require source links, audit/revocation and untrusted-content protections. No shared Administrator, unrestricted database/SQL/shell or arbitrary RPC access. Decide provider/data/cost policy before sending business data. Drafts and consequential writes are later separately controlled phases; DMS/Drive retrieval depends on validated connectors. See [assistant scope](roadmap.md#8-permission-controlled-erp-ai-assistant).

### P23 — PWA offline and poor-connectivity behavior

**Status:** planned. Audit retained drafts and existing service workers before
adding any caching or queue. Design user-isolated caches, safe logout/wipe,
idempotent retries, conflict/error visibility and bounded storage. Test browser
and installed iOS behavior, airplane mode and reconnect; do not cache sensitive
business data or replay consequential actions by default.

### P24 — Field attendance pilot and correction acceptance

**Status:** retained field source is packaged; real-worker acceptance remains.
Exercise device/location/geofence behavior, submitted and returned corrections,
void/cancel rules, supervisor roles and payroll/report effects using test workers.
The earlier approved cancellation path remains blocked; a returned correction
path is not proof of cancellation. Agree business rules before changing them.

### P25 — Invitation, passkey enrollment and recovery acceptance

**Status:** native invitation/recovery adapters are retained. Complete real SMTP
and supported-device ceremonies for a fresh user, single-email enrollment,
duplicate/expired invitations, lost-device recovery and account revocation.
Preserve native identity APIs; source tests and an existing administrator's
working passkey do not prove fresh-user enrollment or recovery.

### P26 — Banking and payroll provider sandbox acceptance

**Status:** upstream integration apps are pinned and installed; provider sandbox
end-to-end acceptance is pending. Configure approved sandbox accounts privately,
test permissions, callbacks/signatures, reconciliation, retries/idempotency and
payroll effects. Do not initiate live transfers, payroll payments or provider
account changes as part of rebuild acceptance.

## Audit disposition

The following requests are complete and are **not pending upgrade/implementation jobs**: core Frappe/ERPNext/HR upgrade; production ERP/SSO consolidation on the new controller; old application/test retirement; Onboarding migration/name/O icon; sole noreply integration sender; final portal and native Desk menu layout/alignment/dividers; Drive/Collabora address mapping; compact TXT/Markdown headers; editor button color matching and outside-click dismissal; Microsoft office-format creation choices; public authenticated Mail with private administration; webmail file-storage disablement; common user sign-in group and Drive client display names.

Current production versions: **Frappe 16.56.0, ERPNext 16.55.0, HRMS 16.53.2**. The installed-app table and the retained feature details are in the [current handover](retained.md).

Only the current retained requests are included here; superseded historical proposals are excluded.

### P27 — Collabora Calc search-based AutoFilter

**Status:** closed 19 November 2026, obsolete: Collabora was replaced by
ONLYOFFICE (P42) and retired; its overlays were removed from the repository.
ONLYOFFICE's own filter search is used. Earlier: fix committed 16 November
2026 (editor overlay `integrations/collabora/autofilter-search.js`, served
inside `cloud-ui.js`). Production reports
Collabora 26.04.6.1. No Collabora image or core change.

Root cause, confirmed in the pinned image's browser bundle: the AutoFilter
search box only hides list rows in the browser (`filterEntries` adds a
`hidden` class). The search text is never sent to the document, so with "All"
ticked Search → OK applies nothing, and ticking "All" during a search sends a
toggle for every value. Individual row ticks send correct row numbers in this
build.

Fix (owner-approved Excel behavior): with search text and at least one match,
OK (or Enter in the search box) clears all ticks through the "All" control,
ticks exactly the visible matches, then sends OK, so only matching rows show,
replacing earlier ticks. "All" during a search ticks or unticks only the
visible matches. Without search text, or with no matches, native behavior is
unchanged. It applies to spreadsheet AutoFilters in any format (.xlsx, .ods,
.xls, .csv); text documents have no AutoFilter. Simulated-editor check:
`tests/browser/autofilter-search.check.js` (7 scenarios pass). Remove the
overlay once the upstream issue is fixed in the pinned build. Not addressed:
the reported missing search box on some columns (decided by the core). Date
tree filters (`check_tree_box`) keep native behavior.

Acceptance on permanent test: Search → OK and Enter with All ticked and with
earlier ticks; Search → All; no-search OK; no-match OK; already-filtered
column; a long list (hundreds of values); the result after save/reopen through
Drive and the portal; inside a P34 sheet view; and no change in Writer and
Impress. Promote the exact tested revision only after these pass.

Searching narrows displayed values, but Search → OK leaves unrelated rows
visible. Related upstream issue: https://github.com/CollaboraOnline/online/issues/16276
(read 16 November 2026). A referenced patch improved client filtering/row indices;
comments still report Search → OK failing on 26.04.5.1. This does not establish
that a newer build fixes the installed version's behavior.

Workarounds: clear All before searching, explicitly tick the required matching
values, then OK; alternatively use Standard Filter with Contains/Begins with.
Do not assume All applies only to the currently searched results.

Reproduce using a synthetic XLSX on permanent test, record image/build and
compare the stock editor with custom JS/CSS excluded. Test unfiltered and
already-filtered columns, multiple matches, manual selection/reset and
save/reopen through direct Drive and the portal. Inspect selection/dialog events
if needed. Evaluate a newer pinned upstream build or narrow source fix only on
test; promote the exact tested revision after regression acceptance. CSS cannot
repair filter selection/submission logic. Submit a sanitized upstream reproduction
if the issue persists; do not upload business spreadsheets.

### P28 — Dual approval for ERP super-administrator access

**Status:** planned assessment/design; owner deferred the choice of approval
model until implementation. No authentication or privilege changes authorized
by this planning entry.

Investigate passkey-based independent approval by two named people before ERP
super-administrator access or sensitive modifications. Decide whether approval
is required once for a short-lived privileged session, whether both people must
remain signed in, or whether selected actions require individual approval.
Two open sessions or two authenticators on one identity do not establish
independent two-person approval.

At implementation, agree eligible requesters/approvers, self-approval prevention,
request binding, reason/audit records, session duration, expiry/revocation,
recovery/emergency access and concurrent-request handling. Assess direct
Administrator login, API tokens, impersonation and existing sessions, plus the
separate authority of Coolify/SSH/database administrators. Do not claim an
ERP-only gate controls infrastructure administrators. Preserve ordinary named
user access and validate bypass/denial/recovery cases on the permanent test
site before any production promotion. Final scope and design require the
owner's decision at that time.

### P29 — Self-hosted mesh VPN with Headscale and Headplane

**Status:** planned; replace hosted Tailscale coordination for business scale.
Assume the requested UI is Headplane (confirm if a different project was meant).
Deploy pinned Headscale and compatible Headplane as versioned VPS/Coolify
services. Assess authentik OIDC, ordinary users, administrator isolation, ACLs,
server tags, branch/subnet routing, device approval/expiry/revocation, supported
Windows/iOS/router clients and DERP/STUN requirements. Headscale replaces the
coordination server; compatible Tailscale clients may still be used. Do not
assume hosted-service feature parity or subscription seat limits apply unchanged.

Design administrative recovery independent of the mesh being migrated. Test on
isolated clients first, preserve existing management connectivity during staged
migration, and explicitly verify both Coolify controllers, SSH, inter-server
refresh and application access before retiring the old control plane. Avoid
DNS/SSO bootstrap dependencies that require an already-working new mesh.
Choose VPS placement and recovery/backup arrangements before rollout; do not
expose the administration UI publicly by default. Repo → test → production applies.
References: https://github.com/juanfont/headscale and https://github.com/tale/headplane

### P30 — Technitium filtered DNS for mesh devices and branch routers

**Status:** planned; depends on P29's tested connectivity and routing design.
Deploy a pinned Technitium DNS service on VPS as a versioned Coolify project.
Provide caching/recursive or forwarded DNS with agreed ad/tracker blocklists,
allowlisting and internal split DNS to approved mesh devices. Branch routers
will forward client DNS over the mesh to this resolver; assess native router
client support or a branch gateway where required. Agree whether branches use
router DNS proxying or routed client subnets, including IPv6 and source ACLs.

Keep DNS UDP/TCP 53 and administration restricted to approved mesh/branch
sources; no public recursive resolver. Preserve public authoritative DNS and
mail records at the existing DNS provider unless separately decided. Coordinate
Headscale/MagicDNS internal zones and conditional forwarding without loops.
DNS filtering cannot remove every advertisement, especially first-party content.

Decide upstream resolver/privacy policy, query-log retention/access, blocklist
updates, branch caches and resolver redundancy/failover. A public fallback may
bypass filtering; explicitly select behavior during VPS/mesh outages. Verify
branch latency, resolution after reboot, DNSSEC behavior, internal/public names,
allowlisting, outage recovery and bootstrap without a working mesh resolver.
Reference: https://technitium.com/dns/help.html

### P31 — Keyboard-first navigation to nested ERP/Frappe menus

**Status:** planned usability work. Owner reports mouse navigation through two
menu levels is slow; provide direct keyboard access to nested destinations.

Audit installed Frappe v16 Awesomebar/Global Search shortcuts and the retained
portal/Desk adapters first. Prefer native permission-filtered navigation search
rather than duplicating a global command engine. Current upstream documentation
distinguishes Ctrl/Cmd+K (Awesomebar menus/actions) from Ctrl/Cmd+G (Global Search);
verify actual installed behavior before choosing bindings.

Provide discoverable shortcut hints, keyboard access to module dropdown and
second-level items (arrows, Enter, Escape and correct focus return), and direct
searchable destinations with their module/path labels. Assess optional user
favorites/recent destinations and configurable direct shortcuts for frequent
screens during design. Exact key assignments remain to be agreed after checking
browser, OS, native Frappe and editor conflicts.

Respect effective user permissions; navigation shortcuts never grant additional
access. Preserve text-entry shortcuts, form edits and unsaved work, and ensure
portal iframe focus/app switching does not swallow keys or invoke commands in
an inactive app. Validate ERP, other native Desk apps, Windows/macOS browsers,
logout/session expiry and keyboard accessibility on permanent test before
production promotion. This improves navigation effort; backend/network latency
and P01's idle freeze remain separate issues.
References: https://docs.frappe.io/framework/keyboard-shortcuts and
https://frappe.io/blog/product-updates/product-updates-for-may-2026

#### P31 extension — Transaction-code navigation

Evaluate an SAP-like transaction-code entry window as an alternative/complement
to keyboard shortcuts and native Awesomebar search. A user types a memorable
code and optional validated record/field argument to navigate directly to an
allowed list, new form, existing document, report, section or field.
Illustrative syntax only (not selected bindings): PO = Purchase Order list;
PO.NEW = unsaved Purchase Order form; PO <record> = existing permitted order;
PO <record> supplier = reveal its section and focus the permitted Supplier field.

Use a versioned, modular allowlisted registry of codes/aliases and native Frappe
routing/new-document APIs. No arbitrary JavaScript, SQL, Python or RPC execution
from the command window. Provide autocomplete, descriptive destination/path
labels, discoverable code hints and clear unknown/ambiguous-code errors. Decide
shared versus personal aliases and registry editing rights during design.

Enforce native create/read/report permissions and document/field restrictions;
never reveal inaccessible record titles or hidden fields through suggestions.
Field targeting needs a loaded form and a selected document or new-form context;
handle collapsed tabs/sections, read-only fields and child tables explicitly.
Navigation must not save, submit, approve, cancel or delete automatically.
Preserve unsaved-change prompts and portal iframe focus. Compare usability with
native Awesomebar before choosing the minimum custom implementation. Keep exact
codes, activation keys and command grammar undecided until the test pilot.
References: https://docs.frappe.io/framework/user/en/api/js-utils and
https://docs.frappe.io/framework/user/en/api/dialog

### P32 — Native-module integration and reversible add-on navigation

**Status:** planned architecture/navigation policy and Onboarding refactor.
Prefer Frappe add-ons that extend native forms/modules without a standalone
portal/apps-screen icon, wherever functionally appropriate. Installed package
registration/dependencies remain distinct from user-facing launcher visibility.
Do not assume every marketplace app can safely adopt this without review.

First application: retain Onboarding inside erpnext_drive_integrations but
remove its standalone launcher from the portal, apps screen and equivalent
navigation. Integrate its relevant links/forms/actions into CRM and HR as
requested. Inventory all existing onboarding/vendor/KYC/response/schedule pages
and agree the destination of each; flag procurement-specific or cross-functional
items for placement decisions rather than silently dropping them. Preserve
existing URLs or compatible redirects, records, permissions, APIs and guest
response links. Coordinate permission-filtered menu/Tcode discovery with P31.

Source audit found explicit Onboarding add_to_apps_screen hooks plus custom
access/boot handling, so removing one visible icon alone is insufficient.
Use supported native workspaces/sidebar/form hooks and addon-owned idempotent
migrations rather than editing upstream ERP/HR files. Future installations,
upgrades and migrations must preserve the selected integrated presentation.

Provide an ownership/change ledger for added menu rows, field/property changes,
fixtures and other configuration. On feature removal, detach only owned entries,
restore prior values only if they still match the addon's applied value, and
report later user/third-party edits for review instead of overwriting them.
Preserve shared links, unrelated customizations and business records. Test
install/repeat-migrate/upgrade/disable/re-enable/remove cycles and rollback.

Non-destructive removal requires a supported feature-disable/detach operation
and documented data retention/export/dependency handling. Native bench
uninstall can delete app-owned DocTypes and records: do not represent it as
safe data-preserving removal or run it as the default cleanup path. Full package
uninstall needs a separately tested preservation/migration plan; disabling
Onboarding must not uninstall the consolidated app's other features. Returning
the navigation/configuration to its previous state must not undo legitimate
business transactions or later independent changes. Validate on permanent test
before promoting the same revision to production.
Reference: https://docs.frappe.io/framework/user/en/python-api/hooks

### P33 — Move the permanent test site to a TrueNAS VM and retire the old VPS

**Status:** done. Test site on TrueNAS since 17 November 2026; old VPS wiped and
its access revoked on 19 November (migration step 9 (private record));
owner: subscription left to lapse (treated as cancelled) and both tailnet
nodes removed (19 November).

Rebuild the test site from Git on an Ubuntu VM with its own Coolify on the home TrueNAS. Reach it publicly through a TLS-passthrough relay on the production VPS over the tailnet (home is behind CGNAT). Re-point the exporter, auth bridge and egress source-IP restrictions to the VM's tailnet address. Run full acceptance, including a button-triggered four-app refresh. Then revoke the old VPS's keys and cancel that VPS (rollback archives are discarded). Must run from a workstation on the tailnet. Full plan: test-host-migration.md (private record).

### P35 — Public release and upstream sharing

**Status:** **published 19 November 2026.** Public repository
`rdavuluri44/ERPNext_Owncloud_Stalwart_Integrations` (AGPL-3.0-or-later,
copyright "Unformat and contributors", fresh history: one commit `eb887b7`,
authored with the owner's GitHub no-reply address; tree identical to the
tested private release `bd78277`). `main` protected (pull requests, no force
push or deletion). Operations records (this file, release log, runbooks)
kept in the old private repository, renamed `the private operations repository` and
now the internal operations repository (full history kept; deploy keys
removed). Artwork audit: company logo not published (placeholder), app icons
from frappe/suite (AGPL-3.0) attributed. Test and production fetch the public
repository. Still open: (a)–(d) presentation polish per module, upstream
sharing (bug reports, forum posts). Owner, 19
November 2026: before publishing, the repository must present itself as
(a) modular, each module explaining what it set out to achieve, (b) the open
source tools that made it possible, (c) the decisions taken and the
integrations built, and (d) how it was done (process, tests, rehearsals).
Builds on P36 (`modules.json`, module READMEs) and `docs/decisions.md`.

Share what we build and fix (AGENTS.md principles 3-5): choose an open-source
license for this repository (owner decision), complete the artwork/branding
and third-party license audit noted in LICENSES.md, remove private
deployment-specific values, then publish. Keep upstream bug reports and fixes
flowing (for example the Collabora AutoFilter search findings, issue
CollaboraOnline/online#16276) with an AI-assistance disclosure.

Shared 17 November 2026: findings and the workaround posted upstream
(https://github.com/CollaboraOnline/online/issues/16276#issuecomment-6947112394),
including that the search field only appears for lists longer than 25
entries, with an AI-assistance credit.

### P36 — Modular repository layout at the TrueNAS rebuild

**Status:** module manifest and READMEs done 17 November 2026 (`modules.json`,
13 modules, enforced by `tests/test_module_manifest.py`); the TrueNAS test site
is rebuilt from this layout (P33). File moves were deliberately avoided so
paths used by running servers stay stable.

Before or during the P33 rebuild, review the layout so each integration
(portal/SSO, field operations, onboarding, Drive, Collabora overlays, Mail,
DMS, document worker, authentik, deployment tooling) is a self-contained
module with its own README, tests, configuration example and license notes,
reusable on its own, while staying in this single repository.

### P34 — Automatic private sheet views in Collabora Calc

**Status:** closed 19 November 2026, superseded: automatic private sheet
views now come from the ONLYOFFICE start page (P42,
`integrations/onlyoffice/`), live in production. Earlier Collabora
implementation (`integrations/collabora/private-sheet-views.js`) removed with
Collabora. Production reports Collabora
26.04.6.1, which includes Calc Sheet View.

Problem: with several users in one workbook, AutoFilter and sort are shared;
one user's filter replaces everyone else's. Collabora's Sheet View gives each
user an independent filter/sort/hidden-row view, but entering one is manual.

Agreed behavior:
- When a user opens a spreadsheet tab, put them in their own sheet view
  automatically (`.uno:NewSheetView`), on **every tab** they open.
- Before creating one, reuse the user's own existing view for that file and
  tab if it still exists (`.uno:SelectSheetView` with its ID). Create a new view
  only when none is recorded or the recorded view no longer exists.
- Ownership is recorded per **signed-in editor user** (the WOPI identity passed
  by Drive), file and tab, never per browser alone: computers and browsers are
  shared. Read the current user at each open; never reuse another user's view.
- View names stay Collabora's automatic names ("Temporary view N"); there is no
  rename command and a core patch is not wanted. Show a small label such as
  "Private view: <login>" so users know which view they are in.
- The user may leave with Collabora's Exit sheet view
  (`.uno:ExitSheetView`). Do not re-enter automatically for the rest of that
  visit; the next open returns them to their own view.
- First implementation keeps the ownership record in the editor origin's
  browser storage, keyed by user ID, file ID and tab. Store only IDs and view
  names, never document content; remove a user's entries on editor sign-out if
  the editor exposes it. A server-side record (follows the user across devices,
  nothing left in shared browsers) is a later option if extra views from new
  devices become a nuisance.

Known limits to tell users:
- Private means personal, not secret: views do not restrict data access, and
  other users can select someone else's view. Access control remains Drive
  file permissions.
- People sharing one login share one view; each person needs their own login.
- A new device or cleared browser data creates one more view for that user.
- Users outside a sheet view (after Exit, or in desktop/mobile apps) still
  share the default filter.

Implementation: a new editor overlay script next to
`integrations/collabora/header-ui.js`, added by `tools/prepare_editor.py`
(cool.html and its mount list). No Collabora image or core change. Confirm
from the pinned image's browser bundle how the client reports document type,
current part/tab, current user ID, sheet-view state and the list of existing
views; the public CollaboraOnline GitHub mirror did not contain the browser
source when checked. Command definitions verified in LibreOffice core
`sc/sdi/scalc.sdi` (NewSheetView, RemoveSheetView, SelectSheetView with
SheetViewID, ExitSheetView).

As implemented (client model confirmed in the pinned image's `bundle.js`):
- Each sheet view is a hidden part in the document status JSON with
  `sheetviewid >= 0` and `defaultviewhash` equal to the source tab's `hash`.
  The overlay reacts to the client's `docloaded`/`updateparts`/
  `updatepermission` events and reads `app.map._docLayer`.
- Current user: `app.map._viewInfo[viewId].userid` (WOPI `UserId` from Drive)
  and `username` for the label. File: last path segment of the WOPI source.
  Tab: one-way hash of the tab name, so tab names are not stored in clear;
  renaming a tab therefore starts a new view for it.
- On a normal tab in edit mode: reuse the recorded view only if a view with the
  same ID **and** name still exists for that tab (`.uno:SelectSheetView`,
  `SheetViewID`), else `.uno:NewSheetView` and record the view the client lands
  in. One attempt per tab per visit, with a 4-second limit; no retry loop.
- Any sheet-view command the user issues (Exit, choosing another view or the
  default view, New, Remove) is detected at the client socket and respected
  for that tab until the next open. Read-only sessions and Writer/Impress are
  left alone. Records unused for about six months are dropped.
- There is no editor sign-out event in the pinned client, so entries are not
  removed at sign-out; they hold only IDs and view names.
- Built into `cloud-sheet-views.js` by `tools/prepare_editor.py` and mounted
  read-only (`editor_collabora_6`). Existing editor build directories must be
  regenerated with `prepare_editor.py` before rerendering, or the new mount
  source is missing.

Validate on permanent test with at least two users (including two users on
one shared browser, one after the other) on the same .xlsx and .ods workbook:
independent filters and sorts on every tab; reuse of the user's own view on
reopen and reload; no cross-user reuse; Exit and next-open behavior; label
shows the current user; save/reopen through Drive and the portal; whether
sheet views are written into saved .xlsx/.ods files and whether views
accumulate; desktop/mobile and Writer/Impress unaffected; P27 AutoFilter search
behavior inside a sheet view. Promote the exact tested revision only after
these pass.

### P38 — Colleague's mobile app: test-only access and safe contributions

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

### P42 — Replace Collabora with ONLYOFFICE

**Status:** done. **Production switched 18 November 2026, 19:00 UTC** (release `a135fd4`,
production releases (private record)); owner browser check on
production done (owner, 19 November). Collabora retired on 19 November from
production and the repository.
P39 part 1 (data restore) passed before the switch; part 2 remains.
Layout and private sheet views agreed and approved by the owner on test on
18 November 2026 (release line, details in `integrations/onlyoffice/README.md`).
Next: mobile check, then steps (2) to (4). Decided by the owner on 18 November 2026
(see [decisions](decisions.md)). Sequence: (1) replace Collabora with ONLYOFFICE
on the test site completely, with automated saving (periodic save to Drive,
forced save, watcher for documents left open) and theming; validate with the
the shared register workbook (open time, co-editing, saves reaching Drive while open, abrupt
close), (2) back up, (3) P39 full restore onto the old VPS using the
ONLYOFFICE stack, (4) switch production.

### P39 — Full restore rehearsal on the old VPS (done)

**Status:** requested by the owner on 18 November 2026, while the old VPS
hosting plan lasts. Restore the latest production backup onto the idle old
VPS, start ERP, Drive, DMS and Mail from it on private names only (outbound
mail, jobs and integrations quarantined as on test, no public DNS), verify
sign-in data, documents and mail, and record the recovery time. Proves the
backups are dependable, beyond the weekly database drill.

**Part 1 done 18 November 2026 (data restore, timed):** fresh production
backup at 17:52 UTC (Drive stopped 14 s, Mail 3 s). On the old VPS (4 vCPU,
16 GB, LXC without TUN, so Tailscale runs in userspace mode with a local HTTP
proxy that restic uses): read-only key, latest snapshot `b9d18d4e` restored
in **10 min 28 s** (9.26 GiB, 68,895 files, from TrueNAS over the tailnet);
all three database dumps imported into throwaway pinned databases in **26 s**.
Counts matched live production exactly: ERP 10 users and 14 files (no
transactions yet), DMS 324 documents, sign-in 12 users, Drive 3,836 files.
About 12 minutes from start to verified data. The retired old test stack was
stopped (not deleted; list in `<server file>`).

**Part 2 done 18 November 2026 (full stack from backup):** on the old VPS
the six test-tier stacks (ERP, Drive, ONLYOFFICE, Mail, DMS, processing) were
rendered and registered from release `e70548e`, and the backup was loaded
through the tested refresh loader via the new `tools/backup_to_snapshot.py`.
Loader result: counts verified, 16 generated Drive links and 23 notes
retargeted, ONLYOFFICE registered with verified origin, document worker
re-enrolled and healthy; quarantine applied (no outgoing ERP mail). Checked in
the running copy: ERP 10 users, 14 files, 1 company; DMS 324 documents; Mail
store present; Drive offers ONLYOFFICE; every service healthy.

Timings: download 10 min 28 s, snapshot conversion 2 min 25 s, stack start
about 8 min, data load 3 min: **about 24 minutes of machine time**. The ERP
and Mail images were copied from the test host (8 min) instead of rebuilt;
rebuilding them from the repository is not yet timed.

Incident during the rehearsal: the old VPS still forwarded the test hostnames
to the live test site (left from the P33 move), and its own stack had no local
routes, so the first load attempt's enrollment check and the old document
worker's polling reached the live test site: 11 read requests, all refused
(401), nothing changed. The loader rolled the old VPS back. The forward was
removed and local routes rendered with `tools/prepare_ingress.py`; the second
load ran fully locally. Lesson recorded in the disaster-recovery guide.

Remaining gaps (follow-ups): the sign-in service (authentik) is not a
repository stack, so it can only be restored as a database today (P44); time
an image rebuild from the repository. The restored copy stays on the old VPS,
private and quarantined, until the VPS is retired.

### P45 — Production Drive, DMS, Mail and sign-in on the repository build

**Status:** started 19 November 2026 (owner). Plan, order and the Drive
comparison: P45 runbook (private record). Renderer gained
`existing_mounts` to reuse production data folders; Drive route file added.
Each app switches in a short planned pause with a rollback point.
**Drive done 19 November 2026** (13 s pause; release `0cfa9c1`; owner
confirmed opening and editing a spreadsheet on production). **DMS and
document processing done 19 November 2026** (2 min 17 s pause; release
`24eb5dd`). **Private DNS and Mail done 19 November 2026** (seconds and 10 s;
release `593d8c8`). Remaining: sign-in and its support service, after P49. Next: DMS, then Mail, then
sign-in.

### P49 — Bring production's sign-in pages and templates into the repository

**Found 20 November 2026:** production's ERP provider mapping sent the legacy
claim `unformat_approved` while the repository ERP requires `cloud_approved`;
new ERP sign-ins failed for days. Emergency fix: the mapping now sends both.
When moving sign-in to the repository build, make the claim name one setting,
add a test that the ERP's required claim is in the provider's mappings, and a
browser sign-in check after every ERP or sign-in deployment.

**Status:** open, found by P45 on 19 November 2026; blocks moving sign-in
(authentik and its support service) onto the repository build. Production's
invitation pages (`<legacy mount: unformat-invitations/public>`, with a stylesheet and
newer admin navigation) and e-mail templates (`unformat-*` names, referenced
by name in authentik's database) are newer than the repository's (`cloud-*`
names, generic branding). Import them into
`integrations/authentik/invite-recovery/`, make the brand name and template
file names profile settings, rehearse on the test site, then switch sign-in
(P45). Also make the webmail product name a setting (production showed
"Unformat Mail"; the repository build shows "Mail").

**Carry into the repository identity stack (found 20 November 2026):**
PostgreSQL `jit = off` for authentik's database (sign-in step 1.2 s to 0.3 s);
a higher memory limit for the authentik server (3 GB; the host has about 7.5 GB
spare) and a cap on gunicorn worker lifetime/memory, because a worker grew to
1.46 GB over five days; a memory alert; check `AUTHENTIK_CACHE__TIMEOUT_POLICIES=0`
(policy caching is off in the legacy stack since the 14 November move, origin
unknown) and decide whether to keep it. Compare the running environment of old
and new containers when switching (lesson of the Mail move).

### P50 — Native mobile app for phones and tablets (module `mobile-app`)

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

### P51 — Data refresh runs at 8 pm, not on demand

**Status:** open, owner request 19 November 2026; work on it later, after the
crippled refresh (PR #3 of the public repository) is merged and in use.
Scrambling the production copy is resource intensive, so pressing "Refresh
data" must not start it at once. Instead the request is queued and starts at
**8 pm** (Asia/Kolkata), and the refresh page shows a line saying so, for
example "Data refresh scheduled for 8 pm today". Owner clarification, same
day: the allowed window is **8 pm to 8 am the next morning**. A request made
before 8 pm is scheduled for 8 pm; a request made inside the window may run
at once. My assumptions to confirm when we build it: only "Refresh data" is
scheduled ("Refresh code" stays immediate); a request made between 8 am and
8 pm waits for 8 pm; a run starts only if it is expected to **finish
by 8 am** (owner, same day): the expected duration comes from the previous
successful data refreshes plus a safety margin (a generous default until one
has run), so a request made late at night, too late to finish, waits for the
next 8 pm instead of running into working hours; repeated
presses merge into one queued run; the page shows who requested it, when it
will run, and its progress; a queued request can be cancelled before it
starts. **Code refresh (owner question, same day):** its duration is not
measured (the ERP image rebuild is the slow part; the container swap took
about two minutes on production). Build the scheduling rule once as a setting
per button: on for "Refresh data", off at first for "Refresh code"; measure
real code refreshes and switch it on if they prove heavy (for example over 15
minutes), with the 8 am finish estimate taken from that button's own history.
Never apply it to the colleague's own branch deploys, which must stay
immediate. Where: `test-refresh` module (worker and refresh page).

### P52 — "All Apps" menu item keeps coming back (bake the removal into the repository)

**Status:** open, owner request 19 November 2026; do later, not now. The
"All Apps" item in the menu of the four apps ERPNext, HRMS, Onboarding and
India Compliance was removed earlier but reappeared after the repositories
were switched (the removal lived in a runtime patch, not in the repository).
Make the removal part of the repository's own build or migration so it is
reproducible and verified by a test and by the browser check, on test first
and then production, and so it is never redone by hand. Check every other
runtime patch for the same weakness.

### P53 — Desk: day-planning widgets and dashboards from all apps

**Status:** parked, owner request 20 November 2026; **do not start now**, take up later when the owner says (planning not started). After
sign-in the portal's Desk becomes the user's quick day-planning page:
widgets and dashboards with data from all apps (for example approvals waiting,
today's assignments and tasks, unread mail, chat mentions, recent Drive files,
DMS items to act on, key ERP figures). Apps connect to the Desk rather than to
the public landing page (P47). Rules: each widget calls the app's API with the
person's own session, so the server decides what they may see; widgets differ
by role; the phone's "Today" dashboard (P50) should use the same data sources
so both devices agree. To settle with the owner: which widgets first, layout,
refresh behaviour, and how widgets are added per module.

**Additional scope (owner, 20 November 2026):**
- **Universal alerts:** collect alerts and notifications from all apps (ERP,
  HR, Drive, Mail, DMS, chat, sign-in) into one place on the Desk, per person
  and permission-filtered, with read/unread and a link to the item.
- **Universal search:** one search box that searches across all installed apps
  (ERP records, Drive files, mail, DMS documents, chat) with the person's own
  access, and shows results in one list with the source app.
- **One ecosystem:** instead of going into each app to find something, the
  person sees and acts on the important things from the Desk (dashboard
  widgets, alerts, search), so the apps behave like one system. Same data
  sources for the phone app's Today screen (P50).

**Additional scope (owner, 21 November 2026): one universal sign-out on the ezone
page.** The portal page (now called **eZone**, see P60) gets a single **Sign out**
control that ends the user's single sign-on session everywhere, and the sign-out items are
**removed from every individual app** (ERP Desk user menu, Drive, Mail, DMS, Raven and
Insights menus, and the editor). Design notes to settle at planning:
- The control runs the existing global logout (`finish_logout`, authentik logout flow,
  then the landing page, P56) so it ends the sign-in service session and every app session
  (ERP, Drive, Mail, DMS, ONLYOFFICE); the next sign-in needs a fresh passkey (P08).
- Removing the per-app items hides the UI (overlay scripts and settings, in the repository);
  the apps still obey a sign-out coming from the single sign-on side, so the shared-browser
  guard and the idle logout keep working.
- Apps opened outside the portal (direct links, desktop and phone clients) have no sign-out
  item: show a way back to eZone, keep session expiry, and give the mobile app (P50) its own
  universal sign-out. Decide the behaviour for unsaved work in open frames (warn before
  signing out), for shared computers, and for audit (who signed out, when).
- Sits with the alerts, universal search and widgets of this item; stays **parked** until
  the owner says to start.


### P54 — Branch deploy button for the "developer" group on the test site

**Status:** open, owner decision 20 November 2026. **Blocked until the first crippled refresh passes its audit** (exporter deployed on production 20 November, residual items listed in the release log). The authentik group
"developer" exists (flat, no bindings, one member: the colleague) and is meant
to be allowed to deploy branches to the test site without asking the owner.
The deploy mechanism does not exist yet (PR #3 only adds "Refresh code", which
resets test to `main`). To build in `test-refresh`: a test-site page where a
member of "developer" picks a branch of the public repository or a pull
request, the repository checks run, and the branch is built and deployed to
test, showing who deployed which revision and when; "Refresh code" puts `main`
back. Safeguards to include: only members of the group may use it (checked on
the server, not just hidden in the page); test runs crippled data only (PR #3)
and its outbound-integration guard stays; deploy only from the public
repository; no production credentials on the test host; every deploy logged.
Accepted risk (owner): deploying runs the branch's code on the test VM.
Needs: PR #3 merged and the first crippled refresh done first.

### P55 — Replace the old logo everywhere with the approved one

**Status:** **done 20 November 2026 (`792cef8`)**: logo, favicons (ERP, portal, authentik, webmail, push), no "All apps" (P52), landing page on www (P47). Was: open, owner request 20 November 2026 ("replace all older logos
with this: sso, place holder, etc."). Approved logo saved in
`assets/brand/` (private). Survey of the code (public repository, `main`):
one shared file feeds almost everything: `company-logo-approved-v6.svg`, copied
into the ERP's public assets at build from the private runtime profile's
`company_logo` (`tools/render_runtime.py`). It is used by the portal
place-holder and signed-out pages, push-notification icons, authentik's
branding logo and favicon (they point at the ERP URL) and the webmail login
logo and favicon (built from the same URL). So the plan is mostly to swap the
private file and rebuild the ERP image, test first, then production (ERP
downtime about two minutes, as in P37). To check besides: Drive's web theme,
DMS (Paperless), Raven and the app menu for their own copies of the old
logo; browser caching (the file name stays the same: use the existing
`asset_version` or a `?v=` parameter so people see the new logo at once); a
smaller file for favicons and push icons (the SVG embeds a 540 px picture,
about 500 KB). **Favicons (owner, 20 November 2026: "change the favicons also"):** the
approved logo is too detailed at 16-32 px, so a compact favicon was designed:
the blue and orange squares with a light panel, a stone arch with dashed
tunnel lines and an orange cross. Files in `assets/brand/favicons/`
(`favicon.svg`, PNG 16, 32, 48, 180, 192, 512; `preview.png`). Replace the
old favicon everywhere: ERP and portal (Website Settings / `app_include`
link), authentik brand favicon (`branding_favicon`, today the old logo file),
webmail `FAVICON_URL`, Drive (oCIS theme), DMS (Paperless), Raven, and the
landing page; use PNG and SVG with a version parameter so browsers refresh.
**Portal page (owner, 20 November 2026):** the portal page ("place holder")
is renamed **Desk** because widgets and dashboards will live there later
(P53); for now it stays as it is, with only the new logo at the top-left. In
this repository's page the browser title becomes "Desk" and the text beside the
logo changes from the company name to "Desk" (the logo itself already says
<tenant>); the route stays `place_holder` because `/desk` is Frappe's own
admin route in this version. The company icon in the auto-hiding app menu (its
"home" button, 44 px) uses the same logo file; consider a compact version
(arch and tools without text) for that small size. Look-and-feel mock:
`assets/desk-mock/`. Order (owner's rule): any code change on a branch, deployed to
test and validated, then merged, then production; for a private-file-only swap
the test deployment is the same rebuild with the new file. Queued behind the
crippled-refresh leak fix, so two jobs do not deploy to the test site at once.

### P56 — Logging out of any app lands on the website

**Status:** open, owner request 20 November 2026 ("build the new desk portal like
logging out of any app brings the user onto the webpage www"). Starts after the
logo, favicon, landing page and "All apps" job (P55, P47, P52) is merged and on
production, because it needs the landing page to exist. **Today** every logout
(ERP, Drive, Mail, DMS, the portal's own logout, and idle logout) ends on the
ERP's "You're signed out" page: the destination is hard-coded in four scripts
(`public/session.js`, `integrations/drive/workspace.js`,
`integrations/dms/cloud_session/session.js`,
`integrations/mail/overlay/lib/cloud-session.ts`) and in the global-logout
code (`portal/sso.py` `finish_logout`, `www/signed_out.*`). **Target:** after
the global logout has finished (ERP session, authentik session, app sessions)
the browser lands on the website: `https://www.<domain>/` in production,
`https://test.example.com/` on the test site (the landing page is served at
its front path), where the "EMPLOYEE ZONE" text is the way back in (it leads to
the portal and its sign-in). Design: one tenant-neutral setting for the
landing address in the private runtime profile (new `www` host in the
renderer's host map; on test it equals the ERP test host), used by the renderer
to replace the logout destinations in all four scripts, the server-side
redirect and the signed-out page; authentik's allowed post-logout redirect
addresses (blueprint `configuration.json` and the live production providers)
must include the landing address, with a backup of the provider rows first.
Order (owner's rule): branch, deployed to test and validated in a browser for
every app (log out of ERP, Drive, Mail, DMS and the Desk: each must end on the
landing page, with the sign-in session really gone; refreshing the page must
not log back in silently), merge, then production with a rollback point. Keep
the shared-browser logout guard and the idle-logout behaviour working (P01) and
add tests that fail if a logout destination is hard-coded again. Later part of
P47 (not this task): moving the portal shell itself onto `www` with `#erp`,
`#mail` routes.

### P57 — The platform survives restarts and reboots without an outage

**Status:** approved by the owner 20 November 2026 ("take precautions that all
systems come up without the outage we faced today"); in progress. Background:
production rebooted unexpectedly at 10:34 IST (provider question open); 33
containers returned by themselves, tailnet ports came back, but the Drive
editor bridge (collaboration) crash-looped because Drive's oCIS advertises one
of its five internal addresses at random after each start (emergency fix: the
bridge was attached to the `coolify` network, a runtime patch).
**Precautions to build (all in the repository, test first):**
1. **Bridge on every oCIS network** in the Drive stack and production profile
   (`extra_networks`), so any advertised address is reachable; start it after
   oCIS is healthy (depends_on healthy, retry on failure).
2. **Docker after Tailscale** on the hosts (systemd drop-in for docker.service:
   After/Wants tailscaled), so containers bound to tailnet addresses (private
   DNS, Mail 465/587/993/8020/8030) never start before the address exists.
3. **Post-boot check with self-repair** (a systemd unit after docker): waits for
   the containers, checks the editor bridge is stable and registered (restarts
   it once if not), checks ERP, sign-in, Drive, Mail, DMS and the editor host,
   checks the tailnet ports, writes a status file/log and fails loudly if
   anything stays wrong; alert for "container restarting".
4. **Longer shutdown time for databases** (stop grace period) so a reboot never
   cuts a database off mid-write.
5. **Reboot drill on the test VM** (planned, night or when the VM is free):
   reboot it and prove that every test host comes back, the Drive editor opens
   an .xlsx, sign-in and Mail work, and the backup timer is intact; repeat after
   restarting oCIS several times.
6. **Checklist and planned reboots:** a post-reboot checklist in
   `docs/production-moves.md`; kernel-update reboots planned for the night
   window, announced, followed by the check; ask the provider (owner raised the
   10:34 IST reboot with them, answer awaited) to give notice of maintenance.
7. **Stalwart after a reboot (found 21 November 2026):** after the 20 November
   reboot production Mail sign-in returned a Stalwart 500 until its settings were
   reloaded (see the 21 November release entry). The post-boot check must run
   `ReloadSettings` through the admin API and then a real sign-in check; Stalwart's
   tracer must also write somewhere that exists (stdout or a mounted folder).
8. Do NOT reboot production as a test; after the drill on test passes and the
   provider answers, the owner decides whether to schedule a planned production
   reboot.
Order (owner's rule): branch, test (drill), merge, production with a rollback
point (the production changes are small: recreate the editor bridge with the
extra network, install the drop-in and the check unit; none restarts Docker).
Coordination: the test VM must be free of the first crippled refresh before the
drill.

### P56 — Logout ends on the website; one passkey prompt; portal keeps its name

**Status:** **live on production 20 November 2026 (`792cef8`)**, owner browser
test on test passed. Was: branch `p56-desk-logout-signin`: (a) portal
page exactly as before except the logo (title and company name restored; same
logo in the menu's home button); (c) one landing address `sso.LANDING` from the
private profile's `landing_url` (production default https://www.example.com/,
test https://test.example.com/), ERP forwards `/login?logged_out=1` and guest
`/signed-out` there; authentik's logout flow still needs a redirect stage to the
landing address (separate flow for the test providers); (d) sign-in sends
`max_age=600` instead of `prompt=login`/`max_age=0` (cause of the double
passkey prompt), callback accepts an authentication from the last ten minutes.
Owner browser test on test pending (blocked by the proxy `mailprivate`
incident). Then production: one add-on rebuild and ERP swap, authentik brand
logo/favicon and plain sign-in background (`plain-background.svg`), logout
redirect stage, webmail favicon env.

### P58 — Next ERP release: favicon B in the ERP image; two-column app menu

**Status:** **done 21 November 2026, live as `3a93de8`** (favicon B in the ERP image, app menu in two columns with the home button alone in the first row, vertically centred). Was: open (20 November 2026). (1) The ERP still serves the old favicon
from its image; the brand folder already holds favicon B (the approved logo,
padded). (2) Owner: the auto-hiding app menu on the portal should become two
vertical columns when it holds more than five icons (portal page CSS, in the
ERP image). Both go into the next ERP add-on rebuild (branch, test, merge, one
swap of about a minute).

### P59 — Promotion plan and drift check: no stack left behind

**Status:** open, owner request 21 November 2026 ("add a P for this and we'll do it
again"); not started. **Why:** on 21 November the production ERP swap for `3a93de8`
missed the website stack (Employee Zone single-click fix): the test deploy script
re-renders every stack, but production stacks are promoted by hand from separate
profiles (ERP in `p37`, website, Drive, Mail, DMS and identity in `p45`), and nothing
says which stacks or live settings a merged change reaches. It was caught only because
the assistant checked afterwards, and an earlier statement that one ERP swap carried the
fix was wrong. The same release also had manual pieces outside the image (bootstrap
step, live authentik brand), and PR #12 adds an ONLYOFFICE restart.

**To build (branch, test, merge, production):**
1. `tools/promotion_plan.py <from> <to>`: from `modules.json` and the stack ownership,
   list every stack, bootstrap step, live setting (authentik brand, flows) and restart
   that the changed files reach, and what cannot be covered by test. The pull request
   must carry this list before merge.
2. Drift check on production (`tools/` plus a nightly timer, like the host checks in
   P57): compare the commit each stack runs (ERP image tag, website/Drive/Mail/DMS/
   identity profile commits and registered definitions) with `main` for the files it
   owns; report any stack that is behind, and fail loudly. Run it after every promotion
   and nightly. Include a check that served content matches (for example the landing
   page script and the ERP favicon hash).
3. `AGENTS.md`: a promotion is not finished until the drift check is clean, plus a
   `docs/decisions.md` entry (what and why).
4. Keep the nightly image cleanup from deleting `erp-core` (a rebuild costs about 20
   minutes at every ERP release): tag-protect it or build the add-on from a pinned
   copy.
Related: P57 (reboot and post-boot checks), the release checklist in
`docs/production-moves.md`.

### P60 — Portal address `/ezone` instead of `/place_holder`

**Status:** open, owner request 21 November 2026; **name changed the same day:** the
owner first asked for `/desk`, which is impossible (it is Frappe's own admin route,
every ERP page is under `/desk/...`), so the owner chose **eZone** ("place_holder looks
ugly"). Address `/ezone`; nothing else uses it, so this is a plain rename. Not started. **Priority: high (owner, 21 November 2026); the owner will say when to start.**

**Design (to confirm):** the portal page is served at `/ezone` (`#erpnext`, `#drive` and
so on); `/place_holder` stays as an alias that redirects to `/ezone`, so bookmarks, old
sign-in links and pushed notifications keep working. Page title and the text beside the
logo: to confirm with the owner ("Cloud" today; "Desk" was proposed earlier, now
presumably "eZone"). A bare top-level `/desk` keeps redirecting to the portal as today.

**Places that name `/place_holder` and must move together:** sign-in return and
callback targets, logout and signed-out hand-overs, the Employee Zone link on the
landing page (test: `/place_holder`; production: `https://erp.<domain>/`), the
`?open=` deep-link handler, `www/place_holder.*` and `home_page` in Website Settings,
the push-notification and mobile links, tests (`test_portal_deep_link`,
`test_logout_and_signin`, `test_app_menu_link`), the module README, and the
production-only proxy route file `place-holder-frames.yaml` plus the
`onboarding-response` route (they match the path; production-only, so test cannot
cover them: browser and protocol check right after promotion).

**Order (owner's rule):** branch, test (every app opens from the portal, logout from
each app, deep links, old `/place_holder` links redirect, the ERP frame at `/desk/...`
still works), merge, production with a rollback point and the route-file change
recorded. Do it with P59's promotion plan so no stack is missed.

### P61 — Editor file safety: a document is never left unusable or its edits lost

**Status:** open, owner request 21 November 2026 ("account for all scenarios that
happened and might happen and make sure that a file is never left in this position");
**priority: highest (production business data).** Not started. Incident record:
21 November shared-workbook incident (private record).

**What happened (evidence, UTC, 20 November):** `<shared register workbook>` (Drive
space Acts) worked until about 16:00 IST. 10:46:54 last good save of the old copy. At
11:03:55 ONLYOFFICE's save to Drive (WOPI PutFile) returned HTTP 500 (the cause is
unknown: the Drive and collaboration logs of that hour were erased when those
containers were recreated at 12:17 for the P56 release) and the unsaved edits were parked as
"forgotten". From 11:07 the editor failed to apply stored edits (`changesError: Cannot
read properties of null`), again at 11:35, 11:57 to 12:00 and 12:54 to 13:15. The file
was deleted and re-uploaded at 11:05:59 and again at 11:33:53 (each upload made DMS link
files), saves worked 11:06 to 12:56, and nothing was saved after 12:56:45, so the owner's
manual deletion of views never persisted and the views "came back". The 40 empty
"Temporary View" entries are old (present in the first saved version of 18 November
09:39, before ONLYOFFICE went live, so Collabora-era leftovers) and did not grow in the
ONLYOFFICE period; they are not the cause. A second parked file (a different small
workbook, 3 sheets) holds edits that never reached Drive: copy in
`<rollback folder>` on production, owner to say whose it is.

**Scenarios (seen = happened to us) and the safeguard for each**

| # | Scenario | Seen | Safeguard |
|---|---|---|---|
| 1 | Save to Drive fails (PutFile 500, proof keys, WOPI lock conflict, oCIS busy), edits parked in "forgotten" | yes | alarm within minutes on `PutFile error` / `storeForgotten`; **rescue job** copies every forgotten file to a recovery folder and tells the owner; root cause logged |
| 2 | Editor cannot apply stored edits (`changesError` null reference), file cannot be opened or edited | yes | `editor_unstick` tool: force save, rescue forgotten, drop the stuck document key through ONLYOFFICE's command service (JWT), reopen check; runbook for people |
| 3 | Edits made but never saved, so deletions "come back" | yes | save-health probe (below) and a visible "not saved" alert path; document the symptom |
| 4 | Diagnosis impossible because container logs vanish on recreate | yes | archive logs before any recreate (P59 promotion plan pre-step) and keep rotated logs on disk for 30 days |
| 5 | Users re-upload or delete the file as a workaround (duplicates, DMS link files, lost history) | yes | runbook "file will not open: do not delete"; versions are restored from Drive's version list; rescue tool covers the rest |
| 6 | Planned or unplanned restart of ONLYOFFICE, the editor bridge, Drive or the host with people editing | yes (reboot 20 Nov) | pre-restart **force save** of every open document; P57 post-boot check also opens and saves a probe document; Stalwart/editor bridge checks already in P57 |
| 7 | Silent breakage of saving after a release, certificate, proof-key or network change | partly | **synthetic save probe** (headless browser opens a probe workbook through Drive, edits, saves, checks that a new version appears) after every promotion and every 15 minutes; failure pages the owner |
| 8 | Private sheet views multiply in a shared workbook (old automation could loop) | no evidence on this file; reproduced in simulation | PR #12 (one attempt per person and sheet), plus a cap: never create when a sheet already has many views; one-off cleaner for legacy "Temporary View" shells (done by hand for the shared workbook) |
| 9 | Disk or cache full on the ONLYOFFICE or Drive volumes (document cache was 255 MB and is never pruned) | no | disk and cache alert at 80 percent, scheduled cache prune of closed documents |
| 10 | File corruption, bad macro or manual edit, huge file slowness | no | Drive keeps every save as a version (27 in two hours here) and the nightly backup covers Drive; restore drill already passes (P39); runbook for restoring one file |
| 11 | Two editors with different page versions (browser cached the old start page) | possible | versioned start-page URL and a restart of the editor with every promotion (P59 plan step) |
| 13 | Stored sheet views the editor cannot read (empty filters in a Private view): blank grid, `changesError` null reference, file cannot be used | yes (the shared workbook, 20-21 Nov) | sanitiser that strips unreadable view data (part of the unstick tool and run before each file is opened by the automation); decide with the owner whether the private-view automation stays on, is limited, or is paused until the cause is proven; test on the test site with two users and filters |
| 12 | Changes to sheet-view or sheet structure by one person break the other person's open session | suspected (null reference on views) | after the legacy views are cleaned, repeat the two-person test on test; keep the editor start page minimal |

**Build order (each item is a normal branch, test, merge, production):** (a) the
unstick-and-rescue tool and runbook; (b) log archiving before recreation (with P59);
(c) alarms on the editor and Drive logs plus the forgotten-file rescue job (systemd
timer, like the P57 host checks); (d) the synthetic save probe; (e) pre-restart force
save; (f) cache and disk alerts; (g) PR #12 and the view cap. Related: P57, P59, P42.
**Honest limit:** nothing guarantees that a save never fails; the aim is that a failure
is seen within minutes, no edit is lost, and a stuck file is recoverable without deleting
it.

### P62 — Daily upstream watch: new releases, security flaws, patches, upgrade decisions

**Status:** open, owner request 21 November 2026; not started. **Why:** the whole stack is
open source and pinned (ERP core and apps, authentik, Drive, ONLYOFFICE, Stalwart, Bulwark
webmail, Paperless, Coolify, Traefik, databases, backup tools, the host operating systems).
New releases, security advisories and upstream fixes reach us only by chance; the ONLYOFFICE
sheet-view crash of 20 to 21 November is an example of a defect that a watch would have
connected to a fix or a workaround.

**Build:** a daily job that (1) reads the inventory of pinned versions and image digests from
the repository (`deployment/` locks, stack definitions and `inputs.json`, each module's
`upstream.json`) plus the components that are not in it (Coolify, Docker, Tailscale,
TrueNAS, the Ubuntu hosts and kernels, restic, RustFS); (2) asks the public sources for
what is new: releases and changelogs, security advisories (GitHub advisories, OSV.dev,
NVD, vendor notices) and open upstream issues that match our versions; (3) writes a short
**daily digest** to the private repository (`docs/upstream-watch/YYYY-MM-DD.md`, only when
something changed, plus a weekly roll-up) and sends the owner a message; a critical,
actively exploited flaw on an internet-facing component is flagged the same day.

**For each finding:** component and our pinned version; what changed; severity and whether
our version is affected; exposure here (public, tailnet only, test only); whether a fixed
version or a workaround exists; compatibility and breaking-change notes; licence changes
(P35 principle 2); and a recommendation: ignore, schedule, or upgrade now, with the reason.
Findings that retire one of our own workarounds are linked (for example the ONLYOFFICE sheet-view
guard, to be removed once the pinned build no longer needs it).

**Rules:** the watch never upgrades anything. Every upgrade is a normal branch, test,
merge, production change with a rollback point, taken up by the owner, ideally together
with related P items. The recommendations are written by an AI agent and are advice: the owner
decides. Run it where it holds no production credentials (for example the test VM or a
scheduled agent), reading only public sources and this repository's pins. First run is
a baseline report of everything that is behind its latest stable release; dry-run for a
week before any message is sent; keep a short false-positive list. Related: P59 (drift
check), P57, P61, P42.

### P63 — Demo mode for the test site (`test.example.com`): neutral brand, no tenant traces

**Status:** open, owner request 21 November 2026; not started. No earlier P item covered
this; related: P47 (landing page), P55 (brand mechanism), P51 and P54 (crippled refresh),
P35 (public sharing). The owner wants `test.example.com` usable as a **demo**. Its data is
already crippled (names and identities of non-kept users removed, 60 days only); now every
trace of the tenant goes too.

**Scope**
1. **Remove the tenant everywhere on the test site:** the name <tenant> and the company logo
   from the landing page, portal (eZone), sign-in pages, favicons (ERP, portal, authentik, webmail,
   Drive, push icons), page titles, browser tab and link-preview text, ERP records that carry
   the company name (Company, addresses, letterheads, print and email templates, system and
   website settings), Drive spaces and DMS items where the name appears. The refresh must
   re-apply this after every data refresh (extend the crippling step), and a check must fail
   if the tenant name appears anywhere in the refreshed copy.
2. **Dummy logo:** big letters **UN** in the first row and **format** in small letters in the
   second row, scaled to exactly the width of the first row (as with "EMPLOYEE ZONE" on the
   landing page). **Propose several colour combinations** as mock-ups for the owner to choose
   from (for example dark blue with orange, graphite with teal, deep green with amber, plum
   with coral, black with a single accent). Used for every favicon and the whole site, replacing
   the <tenant> logo; a compact favicon variant for 16 to 48 px.
3. **Demo landing page with line art:** drawn in the style of the owner's sample (black outline
   drawing with a few flat colour accents on a light grey background; sample kept in the
   private assets as `assets/demo-landing/sample-flower-bee-owner-sketch.webp`: a flower with
   orange centre, green stem and leaves, and a small bee). Our own vector artwork, redrawn
   (rights: owner's own sketch and our own drawing), and drawn stroke by stroke like the
   production landing page; keep the "Employee Zone" entry and the typed line.
4. **Mechanism:** tenant branding already lives in the private runtime profile (`company_logo`,
   `company_favicon_dir`, website title and name, landing assets, P55), so the demo brand is
   a second set of private assets selected by the test profile; production keeps its own. The
   public repository stays tenant-neutral; the UN/format logo and demo art may be published
   as the neutral default.

**Open questions for planning:** (a) test and production **share one authentik**, and its brand
is chosen by the request's host name (`sso`), so the sign-in page cannot show the demo logo for test
only without a separate sign-in host name for the demo (or accepting the shared page); (b) who may
see the demo (the Testers group, or public with sample accounts) and whether the TEST SITE
marker stays; (c) demo user accounts and passwords stay out of Git; (d) outbound
mail and integrations stay quarantined as today.

### P46 — TrueNAS as network video recorder (NVR)

**Status:** planned, owner request 19 November 2026. Besides the test VM and
the backup storage, the TrueNAS server records IP cameras that stream over
the internet. Scope: choose the recorder (Frigate is the first candidate:
open source under the MIT licence, so commercial use is allowed; its paid
Frigate+ model service is optional; to be re-verified at selection), object
detection on a Coral TPU, secure ingest of remote camera streams (no camera
exposed publicly; over the tailnet or an authenticated relay), retention and
storage sizing, and the hardware: larger disks, more RAM, Coral. Keep it
isolated from the backup storage and the test VM (separate dataset, quotas,
no access from production), and include the recorder configuration in this
repository as its own module.

### P47 — Company website as the front door of the app portal

**Status:** planned; scope widened by the owner on 19 November 2026 (first
version was "a minimal website on the VPS and test"). Desktop and laptop
only; mobile devices are handled separately (P50, and its own portal rules).

**Scope (owner):**
- `www.example.com` is the place everyone opens first. It is **always
  reachable, whether signed in or not**.
- Signed out: the public page, with an **Employee Zone** button. Clicking it
  completes single sign-on and shows the portal's auto-hiding app menu.
- Signing out of any app brings the Employee Zone button back.
- Apps open inside the same site like today's portal: ERPNext at
  `www.example.com/#erp`, then Drive, Mail, DMS and the rest, each on its own
  hash route.
- **First version:** very basic: the company logo, a decent background image
  and a banner saying "Launching soon".
- Same site on the test host first (with the TEST marker), then production
  (code → repository → test → production). Content and code as a module in the
  public repository; the real logo and background image are deployment
  assets kept outside the public repository (as the company logo already is).

**Technical notes (mine, to settle when we build it):**
- The portal shell moves from the ERP host to `www`. Every app's allowed
  frame ancestors and parent origin (Drive, Mail, DMS, the editor, ERP) must
  then name `www.example.com`; the Mail move showed what happens when one is
  missed, so each app is checked in the browser, not just by headers.
- The public page is static (own small pinned web container and route file,
  HTTPS through the existing proxy, no access to business data); the portal
  shell loads only after sign-in.
- **Landing page design (owner, 20 November 2026):** the tunnel photo with a
  faded grey overlay as the background; logo, "Launching soon" banner and the
  Employee Zone button on it. Photos from Unsplash (free licence, not open
  source: kept out of the public repository; credit the photographers in the
  footer: grey texture by Mariola Grobelska, tunnel by Ricardo Gomez Angel).
  Apps connect to the **Desk** (the portal after sign-in, P53), not to the
  landing page.
- **Logo (owner):** keep the current logo (the one on authentik) and frame it
  with two L-shaped corner brackets, each its own colour, with gaps between
  them; one bracket orange, the second colour suggested by me. Style modern and
  minimal, black/white plus accents. Mock-ups made 20 November (orange with
  the logo's blue, with teal, with graphite); my recommendation is orange with
  the logo blue (graphite disappears on dark backgrounds). The current logo
  is a raster picture inside an SVG, so a crisp vector redraw is a separate
  option for later. **Owner decision, 20 November 2026 (final after six changes the same
  day): two complete rounded squares behind the white logo panel, in the
  style of the owner's reference icon: blue up-left and orange down-right,
  each a soft vertical gradient (blue `#4FA0E3` to `#0E4A8C`, orange
  `#EE9234` to `#C45E06`), sticking out about 32 px (8 percent of the logo
  width) on two sides, touching the panel with no gap, logo on top. Mock-up
  `mock_G_blue_orange_thinner` (not in Git). The blue echoes the lettering of
  the logo. Earlier variants (orange/teal, purple/orange, graphite) dropped.** **Name:** the landing page shows **<tenant>**. "Unformat" is the
  repository (the product); <tenant> is the tenant using it. So the tenant's
  name, logo and images are deployment settings kept outside the public
  repository, and the public code stays tenant-neutral.
- **Landing page final design (owner, 20 November 2026, after four rounds the
  same day):** white page with an **original pencil drawing** of a tunnel
  construction site (tunnel lining rings, scaffolding gantries, rails and
  sleepers, lamps, hook and workers with hard hats; vector, with a hand-drawn
  wobble), drawn stroke by stroke in four batches over about 18 seconds so the
  page fills progressively. It replaced the photo-derived line art (unclear and
  fuzzy), so the Unsplash photo and its credit are **no longer used**; the
  drawing is our own artwork and may live in the public repository. The
  approved logo; "Launching soon..." in **bold**, sentence case, logo orange,
  **typed letter by letter** (fast: about 0.13 s per letter, done in about
  4 seconds; smaller than first drafted, clamp 15 to 27 px); the pencil is a
  lighter grey (`#9199a1`); "EMPLOYEE" / "ZONE" in
  **capitals**, two lines, borderless, top-left, the logo's blue (`#1F72C4`),
  with "Employee" condensed to the width of "Zone" (Zone keeps natural
  spacing); reduced-motion fallback. Prototype, screenshots and the generator
  are in `assets/landing-prototype/` (private; `index.html` opens in any
  browser). Build the real page from it.
- **DNS (checked 20 November 2026):** `www.example.com` and the bare
  `example.com` have **no records** and there is no wildcard. The owner adds at
  the registrar's DNS (the registrar): `www` A 203.0.113.10 and, optionally, `@` A
  203.0.113.10 to redirect the bare domain to www; short TTL (300). The proxy
  then issues the HTTPS certificates itself. **No `test-www` (owner, same
  day):** on the test site the landing page is served by `test.example.com`
  itself at the front path `/`, in front of the existing test portal (every
  other path unchanged); "Employee Zone" leads to the portal sign-in. This
  matches the end design where one host is both landing page and portal.
- **Scheduled (owner, 20 November 2026):** P55 then P47 start at 05:40 IST on
  20 November without asking again (session-scheduled; if the session was not
  running, it did not fire). P47 goes to production only if the `www` record
  resolves.
- Tools: nothing to install to manage it. The site is plain files in the
  repository, edited with any text editor and an image editor, and deployed
  like the other modules. A content-management system would only be added if
  non-technical people must edit pages later.
- Owner to supply: logo file and background image (or tell me to pick a
  licence-free one).

### P48 — Remote branch router and gateway firewall

**Status:** planned, owner request 19 November 2026; depends on P29
(Headscale) and P30 (Technitium DNS). Find or build a branch router that joins
the mesh, sends local DNS to the Technitium server over Headscale, and acts
as the branch gateway firewall: user-activity logging (kept for legal
reasons) and restriction of streaming to save bandwidth. Compare hardware and
operating systems (for example OpenWrt, OPNsense, pfSense) on mesh support,
logging, filtering, licence and cost. Activity logging must follow the
applicable law (for example India's IT Act and the Digital Personal Data
Protection Act: notice to users, purpose, retention, access control); define
that policy with the owner before enabling it.

### P44 — Sign-in (authentik) as a repository stack

**Status:** done 19 November 2026. The repository `identity` stack (same
pinned images as production) is now proven restorable: the nightly backup
gained the authentik media volume and invitation templates (they were
missing), `tools/restore_identity.py` reuses production's secret key and
passwords from the backed-up Coolify compose, and a renderer defect that kept
the identity stack from rendering (Compose double-dollar escapes) was fixed.
On the old VPS the stack was rendered from release `a2c7fb2`, quarantined (no
e-mail), and loaded from the backup in 1 min 21 s after image downloads:
11 users, 19 applications and 18 OAuth2 providers, identical to production,
and the users' sign-in identifiers match production exactly (fingerprint
compared), so the apps would recognise every user. Production sign-in itself
still runs the pre-repository service; moving it onto this stack is a later,
separate change.

### P43 — Tablet layout and touch check (all apps)

**Status:** open, added by the owner on 18 November 2026. The apps will be used
on tablets, so every app must work well there, in portrait and landscape.
Check the ONLYOFFICE part on the test site **before** the P42 production
switch; the rest can follow.

Scope (test site, owner's tablets plus browser emulation of common sizes,
e.g. iPad 768 to 1024 px and 10 to 11 inch Android, both orientations):
- **Portal:** login, home, left-edge app menu (it opens by hover on desktop;
  on touch it must open by swipe or tap), deep links, opening apps in tabs.
- **ERP desk, Raven, Insights:** layout, menus, tables and forms usable by
  touch, on-screen keyboard not covering inputs.
- **Drive and ONLYOFFICE:** the P42 layout at tablet widths. Our phone rules
  start at 768 px and below, so an iPad in portrait sits on the edge: decide
  per width whether tablets get the desktop or phone status bar (sheet tabs,
  zoom). Also check: the ✕ ⋮ buttons, the side-menu hamburger, the About
  card, the private sheet views, the filter drop-downs and the pivot field
  list by touch, and the on-screen keyboard while editing cells. Tablets use
  the desktop editor (ONLYOFFICE's touch editor is view-only in the free
  edition).
- **Mail and DMS:** reading, composing, attachments, document viewing.

Done when each app passes on at least one iPad-size and one Android tablet in
both orientations, defects are fixed in the repository through the normal
test-first flow, and the tablet rules are recorded in the module READMEs.

### P40 — Backup hardening against ransomware

**Status:** owner approved ZFS snapshots on 18 November 2026. See
[disaster recovery](disaster-recovery.md).

- Daily ZFS snapshots of the backup storage on TrueNAS, kept 60 days, by a
  root cron job (`integrations/backup/zfs-snapshot-guard.sh`), because
  TrueNAS snapshot tasks refuse internal app storage. TrueNAS time zone set
  to India. Done 18 November 2026; first production backup and restore drill
  passed the same day (ERP 1,055, DMS 75, identity 230 tables; 54,025 files).
- Tamper resistance for production's key: versioned bucket (hidden versions
  kept 30 days) and a key policy without version deletes or versioning,
  lifecycle and policy changes. Tool `integrations/backup/harden_storage.py`
  added 19 November 2026. **Done 19 November:** owner applied versioning
  with the admin key and attached the policy to `backup-production`;
  `harden_storage.py verify` from production: writes versioned, a delete only
  hides, old versions survive and cannot be deleted, versioning cannot be
  switched off; restic check with the restricted key clean. Lifecycle rule
  set (hidden versions expire after 30 days, so pruning still frees space).
- Periodic offline copy to a USB disk kept away from the servers.
- Back up the test VM's own settings (`<test host secrets folder>`, profiles).
- Tailnet access rule: production may reach only the backup storage port on
  TrueNAS.

### P41 — Owner recovery essentials (recurring)

**Status:** guideline added 18 November 2026 (`AGENTS.md`,
[disaster recovery](disaster-recovery.md)). Every three months the owner
checks that the encryption password, TrueNAS admin access, SSH keys and the
provider, registrar, GitHub, Tailscale, Meta and authentik logins with
recovery codes are in the password manager, with an offline copy of the
first three.

### P37 — Move production ERP onto the repository-built deployment

**Status:** **done 18 November 2026** (release `3a92645`, about two minutes of ERP downtime); P01 is now live in production. Details and rollback point in the P37 plan (private record).

Production ERP still runs the pre-repository image `erp:0.1.0-release6` with
mounted legacy adapters (`<legacy mount: frappe-netbird-auth-deploy>`,
`<legacy mount: unformat-payments>`, `<legacy mount: unformat-unified>`, `<legacy mount: unformat-integration>`)
and a crash-looping `collab` service. Prepare a production private runtime
profile, map each legacy mount to its repository equivalent or retire it,
build the pinned core and add-on on production, save the current images to
files (nightly image cleanup), back up the site, and switch in a planned
maintenance window with a tested rollback. Then production runs the same
reproducible build as test, including P01.
