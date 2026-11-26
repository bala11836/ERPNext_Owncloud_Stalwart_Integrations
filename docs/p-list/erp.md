# ERP: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 26 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# ERP: P items

ERPNext and Frappe with HRMS, India Compliance, onboarding, field operations, banking and payroll apps, the correspondence register, the AI assistant, WhatsApp and eKYC.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P03 — Employee eKYC India

**App:** erp · **Also touches:** none · **State:** blocked

**Status:** official source staged; app not installed in production. No Digio account is ready.

Confirm compatibility with the running Frappe/ERP versions, install and configure eKYC India, establish the provider account/credentials and any required commercial approval, then verify the employee identity workflow and access controls. Do not describe staged source as an installed or usable integration.

### P04 — WhatsApp onboarding and vendor/PO replies

**App:** erp · **Also touches:** none · **State:** blocked

**Status:** official source staged; WhatsApp app/connector not installed. No Meta WhatsApp Business account or business number is ready.

Set up the provider/business number, deploy/configure the connector, prepare approved message templates and webhooks, and implement authenticated reply-to-record mapping. Verify sending onboarding links and recording vendor yes/no responses against the intended response request or PO with an audit trail. No live sending is currently established.

### P05 — Live GSTIN lookup and form prefill

**App:** erp · **Also touches:** none · **State:** blocked

**Status:** lookup/prefill code exists and calls India Compliance; end-to-end acceptance is incomplete.

- GST API use is enabled, but the configured API secret is absent in the final audit.
- Configure the India Compliance account/API secret and required credits/usage approval.
- Verify successful and invalid GSTIN cases, legal/trade name and address mapping, PAN extraction, error/fallback behavior and lookup limits on an actual vendor form.
- Existing GSTIN format/check-digit validation is not a completed live-lookup acceptance test.

### P06 — PAN verification and automatic constitution deduction

**App:** erp · **Also touches:** none · **State:** open

**Status:** partly implemented, partly outstanding.

Existing checks cover PAN syntax, GSTIN/PAN consistency, and whether the PAN type character matches the selected constitution. Still due:

- Deduce/prefill constitution from the PAN type character, with handling for ambiguous categories and controlled correction.
- Choose/configure an authorized live PAN verification mechanism and test valid/invalid cases.
- Keep local format/type checks visibly distinct from verified identity/status.

### P21 — Client/project correspondence register and DMS integration

**App:** erp · **Also touches:** dms · **State:** open

**Status:** Paperless product selection/deployment is complete; the ERP correspondence register and its integration remain planned. No correspondence DocType was found in the read-only schema audit.

Agree client/project, incoming/outgoing direction, reference/date/subject, responsible employee, response deadline/status, reply chains, transaction/DMS links and physical-original location fields, numbering, workflow and roles. Coordinate with P20, preserve privacy and test an incoming letter/outgoing reply and outstanding-response pilot. Existing vendor response forms and OCR search are not a completed correspondence register. See [register scope](../roadmap.md#7-clientproject-correspondence-register).

### P22 — Permission-controlled ERP AI assistant and business automation (Activepieces)

**App:** erp · **Also touches:** raven, mail, drive, dms, general · **State:** open

**Status:** planned read-only-first evaluation/development; no model, provider data sharing, public tool endpoint or write authority is selected/enabled.

Agree pilot project reports, approvals and attendance summaries; evaluate installed native Frappe tool interfaces; enforce caller-bound native roles/document/field access and a server-side tool allowlist. Require source links, audit/revocation and untrusted-content protections. No shared Administrator, unrestricted database/SQL/shell or arbitrary RPC access. Decide provider/data/cost policy before sending business data. Drafts and consequential writes are later separately controlled phases; DMS/Drive retrieval depends on validated connectors. See [assistant scope](../roadmap.md#8-permission-controlled-erp-ai-assistant).

**Scope added (owner, 22 November 2026): business automation and notifications.**
- **Tool: Activepieces** (owner's preference over n8n): MIT-licensed core (a paid enterprise folder aside), visual
  workflows with AI steps; n8n was set aside because its Sustainable Use License is not open source and restricts
  offering it to other organisations (future tenants). Single sign-on is paid in both, so the Activepieces admin screen
  sits behind the authentik gateway instead.
- **Channels (owner decision): Raven inside the company, WhatsApp for outside vendors.** Activepieces can post to
  Raven through Raven's incoming webhook / REST API (generic HTTP step) and to WhatsApp through the WhatsApp Business
  Cloud API; WhatsApp needs the Meta business number (P04's blocker), approved templates for messages vendors did not
  start, and has per-conversation charges. One sender per event, so vendors never get duplicates (Activepieces or the
  ERP's own WhatsApp connector from P04, chosen per event).
- **Step 1, no new tool:** ERP-native notifications for events inside the ERP: Raven document notifications (for
  example a Purchase Order submitted, posted to a channel with the document linked) and ERPNext Notifications (for
  example a Payment Entry to a vendor: mail now, WhatsApp once P04 is live). Through the test site first.
- **Step 2, pilot Activepieces on the test site** for work that crosses systems or runs on a schedule: supplier
  invoices from mail read by AI, filed in the DMS and drafted in the ERP; weekly overdue-payment summaries; GSTIN checks
  when a vendor is created; Drive folder processing; routing monitoring alerts (P72) to Raven or the phone; human
  approval steps.
- **Rules:** workflows exported to git and promoted test to production like every other change; credentials in the
  secrets manager (P71) and never in workflow exports; AI steps only under the provider and data policy decided in this
  item (business data must not go to an AI provider before that); test-site messages follow the demo safeguards
  (allow list and test marker); every workflow names an owner and has a way to switch it off.


### P24 — Field attendance pilot and correction acceptance

**App:** erp · **Also touches:** none · **State:** open

**Status:** retained field source is packaged; real-worker acceptance remains.
Exercise device/location/geofence behavior, submitted and returned corrections,
void/cancel rules, supervisor roles and payroll/report effects using test workers.
The earlier approved cancellation path remains blocked; a returned correction
path is not proof of cancellation. Agree business rules before changing them.

### P26 — Banking and payroll provider sandbox acceptance

**App:** erp · **Also touches:** none · **State:** blocked

**Status:** upstream integration apps are pinned and installed; provider sandbox
end-to-end acceptance is pending. Configure approved sandbox accounts privately,
test permissions, callbacks/signatures, reconciliation, retries/idempotency and
payroll effects. Do not initiate live transfers, payroll payments or provider
account changes as part of rebuild acceptance.

### P28 — Dual approval for ERP super-administrator access

**App:** erp · **Also touches:** general · **State:** open

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

### P31 — Keyboard-first navigation to nested ERP/Frappe menus

**App:** erp · **Also touches:** portal · **State:** open

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

**App:** erp · **Also touches:** none · **State:** open

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

### P93 — "Request response" button missing on Job Offer

**App:** erp · **Also touches:** general · **State:** in progress

**Why (found 26 November 2026, P89):** `onboarding/hooks.py` loads the "Request response" script on Job Offer from
`client/request_response.js`, which does not exist; Purchase Order uses the real path
`onboarding/client/request_response.js`. Frappe skips a missing file without an error, so the Job Offer button
probably never loads. The script itself already handles Job Offer.

**What (owner go 26 November 2026):** point Job Offer at the real file; add a unit test that fails when any
`doctype_js`, `doctype_list_js` or include hook names a file that does not exist; update the register (HRMS-4).

**Release:** ERP app change: branch, rebuild, test site, owner's browser check (open a Job Offer, the button is
there and opens the request), merge, production. Waits for a free test-site slot (the owner decides when).

**Acceptance:** the button shows on Job Offer on test and production; the new test fails on a wrong path.

**Related:** P89 (register entry HRMS-4).

**Number (26 November 2026):** opened as P90 in this session, but another session had already
recorded P90 (Traefik) on `main`; renumbered P93. Public PR #89, its branch `p90/job-offer-button` and its first
commit still carry the old number.

**Progress (26 November 2026):** public PR #89 (`p90/job-offer-button`), CI passed; the new test fails on the old path.
Waiting for a test-site slot (test ERP runs #77, used by the P74 phone test; owner decides).

### P95 — Face recognition for field team attendance

**App:** erp · **Also touches:** mobile, signin, test-site · **State:** in progress

**Why (owner, 26 November 2026):** field workers often have no phone or app account of their own. The supervisor
should mark the team's attendance just by photographing each person: no selecting the employee first; the app
recognises the face, clears that person's attendance and the supervisor moves on to the next one. Self check-in by
people with the app uses the fingerprint instead (P82), so this item covers only team attendance.

**What (owner decisions, 26 November 2026):**
- **No team faces on the supervisor's phone.** Face data lives on our server only.
- **Bulk onboarding:** HR (or the project manager) enrols each field worker with one good phone, checked against the
  worker's ID: several angles (front, left, right, up, down) on video. True 3D needs a depth sensor, which only
  iPhones have; on Android it is several 2D views. The server keeps encrypted face templates (numbers), not the
  photos (agent recommendation; a model change then needs re-enrolment).
- **Liveness on the phone, matching on the server:** on the supervisor's phone, offline and free, MediaPipe Face
  Landmarker follows the head turn and a blink (its 3D is estimated from the picture, not measured) and a photo and
  screen check (Silent-Face) catches paper and screens on the spot; the phone holds no one's face data. The server
  matches each capture with SFace against the workers rostered on that site and shift only (more accurate than the
  whole company) and re-checks the uploaded frames in case a tampered app fakes the liveness result.
- **Uncertain matches:** with connection, the supervisor picks from the 2–3 closest names on the spot, marked for
  the project manager. **Offline:** the app saves each capture encrypted with GPS and the phone's time and shows
  "queued"; the server recognises it when the phone is back online; uncertain or unmatched captures go to the
  project manager, who clears the offline queue. The existing approval of all attendance by the site's approvers
  (decision of 22 November) stays.
- **Consent:** an agreement is shown and accepted at onboarding: a separate tick box, in a language the worker can
  read, with withdrawal possible. Workers who refuse or withdraw keep an attendance path without a face (the
  supervisor marks them and the project manager approves). Face data is deleted when a worker leaves.
- **Legal:** development goes ahead; a lawyer's opinion under India's DPDP Act (consent, or the employment
  "legitimate use" of section 7; notice; retention; protection) is obtained **before launch**. Build so the face
  store can be moved or switched off if the opinion asks for it. Until launch, test only with synthetic data or
  staff who have signed consent.

**Before adoption (working agreements):** check licence, maintenance and security history of MediaPipe
(reported Apache-2.0), SFace (OpenCV Zoo, reported Apache-2.0) and Silent-Face-Anti-Spoofing (reported Apache-2.0,
not updated for a few years). The best-known free face models (InsightFace) are for non-commercial use only and are
not used. Record the results in the decision log.

**First step:** the licence and maintenance checks above, then a trial on test with synthetic faces: enrolment,
liveness on two phone models, server matching against a small roster, online pick and offline queue.

**Related:** P24 (field attendance pilot), P50 (the app, offline captures), P82 (onboarding, biometric sign-in,
self check-in without a selfie), P96 (SOPs: bulk onboarding, consent, leavers, offline queue).

**Owner, 26 November 2026 (evening):** build now; do not wait for the lawyer's opinion. **Late evening:** the legal
opinion is needed **before the app is connected to production** (that is the gate, not the development).

**SFace (owner, 26 November 2026, late evening):** build on SFace now and ask OpenCV about its training data. Asked
by adding to the existing upstream issue (opencv/opencv_zoo#313, comment https://github.com/opencv/opencv_zoo/issues/313#issuecomment-7193191907; four open issues ask the same, a
maintainer has only answered that the Apache-2.0 licence should be enough). The residual risk is decided before
production, with the legal opinion.

**Adoption check (26 November 2026, agent research, primary sources):**

| Tool | Verdict | Code / weights licence | Version | Note |
|---|---|---|---|---|
| MediaPipe Face Landmarker (Android Tasks) | adopt | Apache-2.0 / Apache-2.0 | tasks-vision 1.2.3 (11 Nov 2026) | blink and head pose for liveness; no advisories |
| Expo wrapper for it | reject | MIT | 1.4.0 | one-person project for an old camera library; write our own Kotlin plugin |
| OpenCV Zoo SFace (fp32) | adopt with caution | Apache-2.0 / Apache-2.0 | model 2021dec | **training data unverified** (paper used research-only datasets); owner decision |
| OpenCV Zoo YuNet face detector | adopt | MIT / MIT | 2023mar | |
| Silent-Face anti-spoofing | adopt with caution | Apache-2.0 | last commit 2020 | unmaintained; one signal only, the head turn and blink are primary |
| UniFace (packages those weights) | adopt with caution | MIT; weights from Silent-Face | 4.3.0 | maintained packaging |
| opencv-python-headless | adopt | Apache-2.0 (+ FFmpeg LGPL-2.1) | 5.1.0, wheel build 95 (17 Nov 2026) | no open advisories |
| onnxruntime | adopt if needed | MIT | 1.32.0 | not needed on the server (OpenCV runs the models); source repo not reachable on the check date |
| InsightFace models | reject | MIT code / **non-commercial** weights | | |

**Progress (26 November 2026):** public PR #94 (`p95/face-attendance-server`): matching rules, encrypted templates
(readable by no role, no history, permanent deletion), consent records, enrol / identify / withdraw, leaver hooks, the
model slot (off); 21 new tests, CI passed. Not yet: the face model (waits for the SFace decision), capture screen and
PM queue, phone liveness (needs a phone), a test-site migrate (needs a slot).

**Face engine (owner's go, 26 November 2026, late evening):** public PR on branch `p95/sface-engine`.
- YuNet and SFace fp32 from OpenCV Zoo at commit `48b10fa`, fetched into the ERP add-on image with a SHA-256 check
  per file (`deployment/face-models.json`, `tools/fetch_face_models.py`, register BUILD-11), run by the OpenCV
  already in the image (version 5.0.0, wheel build 93; OSV: no advisories, also numpy 2.5.4).
- The engine is off until a site names it in site config. The daily watch follows the model pin. The open-source
  list moves OpenCV and OpenCV Zoo to "adopted".
- Engine test here, on OpenCV's sample photos with the image's exact OpenCV version:
  - the same face mirrored, smaller or darker scored 0.93 to 0.97;
  - a different person scored 0.18 (threshold 0.363);
  - a blank photo and a photo with two faces were refused;
  - identification picked the right worker.
- Found: OpenCV 5 ignores `setInputSize` after the detector is made, so the engine makes one per photo size.
  Detection confidence is 0.8, because 0.9 refused a smaller copy of a clear face.
- Not done:
  - an ERP image build with the models (next release build);
  - a trial on the test site with synthetic or consenting faces (needs a test-site slot, owner);
  - tuning on real field photos.

**Capture without choosing the worker, and the project manager's queue (owner's go, 26 November 2026, night):**
public PR #101 (`p95/pm-queue`).
- `face_capture`: a team photograph without a chosen worker is validated once on arrival (place, time, photograph).
  A confident match is recorded and submitted at once in the supervisor's name; everything else waits as "Needs
  review" (uncertain, nobody recognised, no clear face, recognition off, or a rule that needs a person such as a
  machine allocation).
- The project manager's "Face queue" tab on the field team page: pick the worker or reject with a reason. Only
  another approver of the site decides; the chosen worker must be on the capturing supervisor's team.
- Photographs are private; the queue's copy is deleted once recorded; a rejected capture keeps its photograph for 30
  days (confirmed by the owner, 26 November 2026).
- It works with recognition off: every such capture then waits for the project manager.
- Tests: 12 new offline tests; 57 with the HR and face suites pass; CI passed.
- **Not run:** 22 rollback-only live checks (`custom_hr/face_queue_integration_tests.py`); they need a test-site slot
  and are where the database behaviour gets proven.
- Not built: the mobile app's capture screen and the liveness check on the phone.

**Status:** in progress.

### P97 — Uploaded files that can run script are always downloaded (GHSA-94mh-qq29-qwrf)

**App:** erp · **Also touches:** general · **State:** in progress

**Why (found 26 November 2026 by the P91 to P93 session; daily watch baseline, "schedule"):** public attachments are
served from disk under `/files/`. Our ERP web server config (`deployment/erp/frappe.conf.template:68`) forces HTML,
SVG and XML uploads to download, but the rule matched lower-case extensions only. A file named `poc.SVG` or
`poc.HTML` opened in the browser, so any signed-in user who can attach a public file could plant a page that runs
script in the session of whoever opens the link (an administrator included). Published frappe_docker advisory
GHSA-94mh-qq29-qwrf, high, fixed upstream in v4.3.0 (`d34f0f92a1`). Our template replaces upstream's (register
BUILD-2), so a frappe_docker bump alone does not fix it.

**What (owner go 26 November 2026):** carry upstream's rule word for word (any case; 14 file types instead of 4;
anchored at the end of the name); a unit test that fails if the rule becomes case-sensitive again or loses a type;
register BUILD-2 says upstream security fixes in this template are carried by hand and re-checked on every bump.

**Scope decisions (owner go 26 November 2026):** only this rule. Upstream's other template changes since our pin
(trusted HTTPS forwarding, `280fc962eb`; clearing `X-Forwarded-SSL` / `X-Forwarded-Protocol`) stay out: they touch
how proxy headers are trusted and relate to the Origin report still in triage (private companion, BUILD-2). They
have no item yet.

**Release:** an "ERP runtime files" change (promotion map): render the ERP stack and redeploy; no image rebuild, no
migration. Branch, test site, merge, main, production, with a rollback point (the previous mounted file) and a
release record.

**Acceptance:**
1. On test, public uploads `poc.SVG`, `poc.HTML`, `poc.Xml` and their lower-case forms answer with
   `Content-Disposition: attachment`; a `.PNG` and a `.pdf` open as before; private files behave as before.
2. nginx starts with the rendered config; the realtime socket still connects (register BUILD-2).
3. The same header check on production right after promotion; drift check clean for erp.
4. Read-only look on production for existing public files with these extensions in upper or mixed case (file names
   only), result recorded.

**Progress (26 November 2026):**
- Public PR **#103** (`p97/files-forced-download`, fix commit `b7e0b7c`): the rule, `tests/test_files_forced_download.py`
  (6 tests; fails on the old rule), register BUILD-2. Repository check and client identity check passed locally; the
  full unit run cannot run on the Windows PC, CI is the evidence. Advisories checked 26 November 2026: frappe_docker
  advisories and releases against pin `0ad1a1152f93`; one published advisory (this one), fixed by the change;
  latest release v4.3.0.
- Read-only check on the test VM (26 November 2026): the ERP web container mounts the template read-only from
  `<server path>` and renders it at start; the running config has the old
  case-sensitive rule; nginx 1.26.3 with PCRE2 (supports the new pattern); no public file on test has one of these
  extensions in upper or mixed case. The test ERP runs the colleague's PR #77 image (`2a9f149`), used by the P74
  phone test: the fix needs only the mounted file replaced and the web container recreated (seconds), not a new
  image. Not done; waits for the owner's go for the test slot.
- **On test since 26 November 2026, 15:35 UTC (owner's go):** the template of `95f25b9` replaced the mounted file and
  the web container was restarted (about 10 s; image unchanged, `2a9f149`). Before: `.SVG`, `.HTML`, `.Xml` test
  files opened inline (flaw confirmed). After: `.SVG`, `.svg`, `.HTML`, `.html`, `.Xml`, `.xml`, `.MHT` answer
  `Content-Disposition: attachment`; `.PNG` and `.pdf` unchanged; `.html.txt` no longer forced; private files 403
  without a session as before; realtime handshake 200 as before; nginx syntax test passed first; test files removed.
  Receipt `p97-test-erp-files-forced-download-95f25b9`; rollback copy kept on the test VM (in the receipt).
  Limits: checked directly against nginx in the container, not through the ERP upload screen or a signed-in browser.
- **Production look for existing files: not done.** The owner said yes, but the session's permission check refused
  the production connection from this PC; nothing ran on production.
- **Merged, not deployed (26 November 2026, owner's go):** public #103 at `bf8d5c8` (head `af3e6b9`, brought up to date
  with main, CI passed; the template is byte-identical to the tested `95f25b9`), private #10 at `66d0b9f`.
  **Reaches:** the erp stack on production (one mounted file, restart of the web container). The test ERP already
  runs the file.
- **Production look done (read-only, 15:46 UTC):** production runs the old rule (mounted file equal to the template
  before P97). The site has **no public files at all** (0 public, 49 private), so no file with an affected extension
  exists and nothing points to the flaw having been used through a stored file. Until production has the fix, a
  signed-in user could still upload one.
- **Production not changed: stopped.** The look showed the production server had rebooted at 15:30 UTC (16 minutes
  earlier, new kernel) and another key signed in a minute after: another session or the owner is at work there.
  Raised to the owner, who confirmed it and gave the word to continue. One monitoring container (Prometheus, P72) had not come back
  after the reboot (seen 15:46 UTC; not touched).
- **On production since 26 November 2026, 15:51 UTC (owner's go, after the owner confirmed the reboot):** the
  template of main (`bf8d5c8`) replaced the mounted file; web container restarted (11 s); image unchanged
  (`059f8bf`). Flaw confirmed before with harmless files, every header check passed after, test files removed.
  Receipt `p97-production-erp-files-forced-download-bf8d5c8`; release log entry; rollback copy on the VPS.
- **Drift check:** erp is reported behind main (30 files). The check reads the image tag and cannot see a mounted
  file, so it still lists this template; the other 29 files are P95 and P93 (merged, not deployed).
- **Acceptance:** 1, 2 and 4 met; 3 met for the header check, not for "drift check clean" (reason above).
- **Left:** owner's signed-in browser check (a download, realtime); owner decides when P97 is closed. P99 opened so
  the drift check compares mounted runtime files by checksum.

**Related:** P89 (register BUILD-2), P91 (upgrade checks), P62 (daily watch finding
`advisory:frappe_docker@0ad1a1152f93:GHSA-94mh-qq29-qwrf`).

### P98 — ERP web server template: take up upstream's trusted-HTTPS forwarding changes

**App:** erp · **Also touches:** signin, general · **State:** open

**Why (found 26 November 2026, P89 and P97; owner: open an item):** our ERP web server template is a full copy
that replaces frappe_docker's (register BUILD-2), so upstream's changes to it do not reach us. After P97, two
differences from upstream `main` remain besides our own Origin change:
1. **Trusted HTTPS forwarding** (frappe_docker `280fc962eb`, 11 November 2026, "configure trusted HTTPS forwarding for
   OAuth redirects"): the forwarded "https" header is believed only when a new setting
   `TRUST_UPSTREAM_FORWARDED_PROTO` is `on`. Ours believes it from anyone who can reach the web container. The
   commit also changes upstream's entrypoint and compose files, so it is not a one-line copy.
2. **Clearing two forwarded headers** (`X-Forwarded-SSL`, `X-Forwarded-Protocol`) before requests go to the backend
   and to socket.io, so a client cannot set them.

**Not decided, to check first:** whether either difference can be used against us (the web container is reached
only through our proxy; what the proxy strips or sets is not verified); what the setting must be on test and
production so sign-in redirects keep using https; how it interacts with our Origin change and the private report
still in triage (private companion, BUILD-2). No published advisory names these two differences (checked
26 November 2026).

**What (proposal, owner to confirm before work):** read-only check of what reaches the web container on test;
then carry both changes with the right setting in the test and production profiles; tests; register BUILD-2;
through the test site with a sign-in and realtime check; production from main.

**Acceptance:** our template differs from upstream's only by the Origin change; sign-in (redirects stay https),
realtime and file downloads work on test and production; a forged forwarded header from a client is ignored.

**Related:** P97 (same file), P89 (BUILD-2), P91 (upgrade checks: a check that compares this template with
upstream's at the pinned commit would catch the next silent difference), P49 and P82 (sign-in redirects).
