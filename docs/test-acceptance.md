# Repository-built test acceptance — 16 November 2026

The persistent test workspace was built on a separate existing Coolify host
from this repository plus pinned public upstream sources. Production application
directories, private ERP base images and the previous private repository were
not used as build inputs. Existing authentik supplies sign-in through separate
test web providers. Branding, hostnames, credentials and business data remain
private operator inputs outside Git.

## Accepted checks

| Area | Result and evidence |
| --- | --- |
| Public ERP core | Nine upstream app sources built from their locked Git commits; the build wrapper verifies every expected app directory. The official `apps_json` mount and input-bound `CACHE_BUST` prevent a cached Frappe-only build from passing. |
| Installed apps | Frappe 16.56.0, ERPNext 16.55.0, HRMS 16.53.2, India Compliance 16.11.0, Raven 3.2.0, Insights 3.15.1, payment utilities 16.0.0-dev, RazorpayX 16.0.0-dev and India Payroll 16.1.0; only one custom app, ERPNext_drive_integrations 0.1.0. |
| Fresh initialization | Empty ERP databases initialized and all ten apps installed before production business data was imported. Empty-store restore/failure rollback rehearsed separately. |
| Native deployment | Six native Coolify services for ERP, Drive, editor, Mail, DMS and processing; separate test stores/configuration and trusted HTTPS hostnames. |
| SSO | Existing identity service, exact test callbacks/shared ordinary-user group and separate test web credentials. Native retained identity blueprint dry-run/application passed in an isolated rehearsal; two stock native Drive client registrations prepared from pinned public source. |
| Portal/native Desk | ERPNext, HR, Onboarding, India Compliance and Framework opened with retained module dropdowns/submenus and helper placement. Raven and Insights opened using their native SPA navigation. Insights dashboards compared with production after its declared source adapter was compiled. |
| ERP assets | 92 manifest entries and 28 hook assets checked, with no missing assets. |
| Drive/Collabora | Native registration exposes DOCX/XLSX/PPTX creation and hides ODF creation. A synthetic DOCX was created, edited and saved in the browser; downloading its stored DOCX confirmed the entered text. |
| Drive → DMS | A synthetic personal PDF was uploaded to test Drive, automatically processed and text extracted. Native DMS owner/object permissions and its test-only generated link were verified. |
| Mail | Restored inbox, calendar and contacts opened. Shared noreply identity was present. Files navigation was hidden through native feature policy. No test message was sent. |
| Attachment picker | The owner confirmed files are selectable in an ordinary browser. The automated popup had a rendering/control limitation; this is not a real send/receipt or large-link acceptance test. |
| Fresh four-app snapshot | Real home-page button queued the root worker. A fresh consistent production snapshot completed with 38.16 seconds of selected-app maintenance; all production roles resumed before transfer. Native test business counts, fresh owner enrollment, generated-link retargeting and editor registration passed. |
| Data replacement | Snapshot ERP counts: eight users, one company, fourteen File records including four uploaded files. DMS had thirteen records including soft-deleted records; browser shows nine active documents. Synthetic test additions were removed by refresh, without any reverse write to production. |
| Session recovery | A target-side rehearsal reused the verified retained snapshot, without another production pause. Progress stayed visible while ERP sessions were replaced; ordinary SSO renewed the session automatically and the durable completion time appeared on Home. A subsequent health-gated rehearsal also confirmed the worker restarts only after fresh credential enrollment. |
| Persistent operation | Five-second request timer and test egress service active. Business scheduler and copied outbound configuration remain disabled; short/default and long report queue workers start only after verified quarantine. Separate enrolled document worker healthy. Local rollback/staged archives retained privately. |
| Source checks | Fifteen isolated suites plus source/schema/privacy and JavaScript syntax checks pass. No live provider/device delivery claim is inferred from these checks. |

Both ERP report queues completed native timestamp-only smoke jobs after
quarantine; no business records or messages were created by those queue checks.
The runtime ERP image was compiled from application source at `064228f`, with
the public core verified by the input-bound build wrapper. Later repository
commits record the acceptance/runbook and host-side activation checks; they do
not replace application code with a production image or uncommitted test patch.

The data snapshot used for the final recovery rehearsal was captured at
**02:17:18 UTC** on 16 November; the final health-gated rehearsal completed at
**03:10:52 UTC** (08:40:52 Asia/Kolkata). The timestamp below the button is successful restore
completion time. Root-private receipts also preserve source capture time and
snapshot identity. Normal button operation always requests a fresh source
snapshot; retained-archive retry is a root-only recovery/rehearsal option.

## Setup cleanup

After acceptance, remove the temporary setup SSH key and temporary SSH tunnel
without removing the private Coolify endpoint. Retain only the explicitly
approved repository read-only deployment key and restricted production-export
key needed by future refreshes. Temporary privileged controller API tokens are
not needed by the local native-model deployment tools. Dispose of isolated
identity rehearsal containers/volumes after recording native validation.

## What remains separate

The previous private repository is no longer an input to this tested deployment.
Its retired Suite integration/history is deliberately excluded; retained source,
provenance, modular adapters and the reconciled roadmap are here. The owner may
retire it without losing a build dependency of this workspace. It has not been
deleted by this work.

This acceptance does not complete physical desktop/iPhone sync, native mobile
push, global logout from every device/app, long-idle recovery, live banking/KYC/
WhatsApp/GST/PAN/delivery checks or off-server recovery. Those distinctions and
future features remain in the maintainers' task list (private operations repository). Raven/Insights keep their
native SPA navigation. Test sends and live external integrations stay disabled.
Cloning supplies code, pinned recipes and instructions, not private data,
provider accounts, DNS ownership or production credentials.

See [the rebuild/refresh runbook](test-rebuild-runbook.md) and
[native SMTP setup](mail-smtp.md) for reproduction and future deployment.

# P01 idle menu recovery — test deployment, 17 November 2026

Tested commit: **`95d2f17`** (branch `claude/p01-idle-menu-recovery`), deployed
to the current permanent test site on the old Coolify host. ERP add-on only;
Drive, editor, Mail, DMS, processing and production were not changed.

## Deployment

| Step | Result |
| --- | --- |
| Source gates | `tools/check_repository.py` passed (296 files). `tools/run_unit_tests.py` passed all 16 isolated suites in the ERP core Python environment, with no network and no live database. |
| Render | Private profile `commit` and `erp_image` updated, then `tools/prepare_runtime.py` rerendered. Asset stamps are rendered from the profile commit, so the page loads `session.js?v=95d2f17` (the source's `?v=20261116-idle1` is replaced at render time). |
| Image | `erp-test:95d2f17-runtime` built from `deployment/erp/Dockerfile.addon` on the same verified core `erp-test-core:2ded77c` as the previous `064228f` runtime. |
| Registration | `tools/coolify_native.py` re-registration returned the same ERP service UUID; the rendered controller Compose differs from the previous one only in the ERP image tag. The controller team must be passed explicitly (`--team-id`, plus server and destination) on this host; the default team does not match. |
| Rollout | Only the running app roles (backend, websocket, frontend, short and long queues) were recreated; databases, caches and the configurator were untouched and the business scheduler stays off. Cache cleared; the same ten apps remain installed. No migration: the change has no DocType or patch. |
| Rollback point | Previous profile, rendered runtime and controller Compose retained privately on the test host; the `064228f` runtime image remains available. |

## Browser validation (owner, signed-in Chrome)

| Check | Result |
| --- | --- |
| Asset loaded | `session.js?v=95d2f17` loaded. **Pass.** |
| Proxy session lapsed, SSO still signed in | Only the `authentik_proxy_*` cookie for the test ERP host was deleted; after switching tabs and back, without reload, menus worked and no notice appeared. **Pass** (silent renewal). |
| After SSO sign-out | No Reload notice appeared; the tab went to SSO sign-in. Sign-out sets the explicit logout signal, which the existing logout guard handles before the new proxy probe, by design. The tab correctly ended at sign-in, but this did **not** exercise the new notice path. |
| Native menus | ERPNext, HR, Onboarding, India Compliance, Framework, Raven and Insights menus all worked after sign-in. **Pass.** |

## Limitations and remaining checks before production

- The "Reload" notice (SSO session expired without an explicit sign-out) was
  verified only in the earlier local Chromium simulation, not on test. To see it
  on test, let the SSO session expire (or end it from the SSO admin rather than
  signing out in the browser) and then delete the proxy cookie.
- Real long idle (beyond the 8-hour proxy refresh validity) and computer sleep
  were not tested; the proxy lapse was simulated by deleting its cookie.
- The Socket.IO "Invalid origin" realtime defect is separate and unchanged.
- Production has not been changed. Promotion of `95d2f17` should follow the
  remaining checks above, with a production rollback point.

# P34 private Calc sheet views — test deployment, 17 November 2026

Tested commit: **`ebd3fdd`** (branch `claude/p34-calc-private-sheet-views`),
deployed to the current permanent test site on the old Coolify host. Editor
stack only. ERP keeps running the P01 build `95d2f17` (unchanged by this
deployment); Drive, Mail, DMS, processing and production were not changed.

## Deployment

| Step | Result |
| --- | --- |
| Source gates | `tools/check_repository.py` passed (299 files). All 17 isolated suites passed in the ERP core image, including the 10 controller rules in `tests/collabora/private_sheet_views_test.js` under Node 24. |
| Editor overlay | `tools/prepare_editor.py` regenerated from the pinned Collabora digest into a new build directory; `cloud-sheet-views.js` matches `integrations/collabora/private-sheet-views.js` byte for byte. |
| Render | Private profile `editor_artifacts` and `commit` updated and the runtime rerendered. ERP mount files and ERP Compose were checksummed before and after: unchanged. The existing WOPI proof key was preserved. |
| Registration | `tools/coolify_native.py` returned the same editor service UUID; the controller Compose differs only by the new read-only `cloud-sheet-views.js` mount. |
| Rollout | Only the Collabora container was recreated; healthy. Discovery returns 200 and `cool.html` loads `cloud-ui.js?v=ebd3fdd` and `cloud-sheet-views.js?v=ebd3fdd`. |
| Drive registration | `tools/verify_test_collaboration.py`: registered, Microsoft-format creation available, ODF creation hidden, editor origin verified. |
| Rollback point | Previous profile, editor mounts and controller Compose retained privately on the test host; the previous editor build directory is kept. |

The rendered ERP build context on the test host now reflects `ebd3fdd`.
That does not affect the running ERP image; any later ERP build rerenders from
its own commit as the runbook requires.

## Browser validation

Pending: the two-user checks listed under P34 in the maintainers' task list (private operations repository).
Not production-ready until they pass.

# P27 + P34 combined editor — test deployment, 17 November 2026

Tested commit: **`d704195`** (branch `claude/p27-p34-editor`), a merge of the
P27 AutoFilter search fix (`b9edd28`) into P34 private sheet views
(`ebd3fdd`). Both change `tools/prepare_editor.py`; the owner chose to test
them together on the permanent test editor rather than drop P34 from test.
Editor stack only. ERP keeps running the P01 build `95d2f17`; production was
not changed. This supersedes the editor deployed for `ebd3fdd` above; the P34
browser checks now run on this build.

## Deployment

| Step | Result |
| --- | --- |
| Source gates | `tools/check_repository.py` passed (301 files); all 17 isolated suites passed in the ERP core image; P27 overlay passes `node --check`. |
| P27 simulated editor | `tests/browser/autofilter-search.check.js` in the official Playwright 1.49.1 container (headless Chromium): all 7 scenarios pass (Search→OK with All ticked, Search→Enter, Search→OK replacing earlier ticks, native OK without search, native OK with no matches, Search→All unticks and ticks only matches). |
| Editor overlay | Regenerated from the pinned Collabora digest; `cloud-ui.js` contains header-ui plus the P27 overlay, `cloud-sheet-views.js` matches the P34 source. |
| Render | ERP mount files and ERP Compose checksummed before and after: unchanged. WOPI proof key preserved. |
| Registration | Same editor service UUID; controller Compose unchanged from the P34 deployment. |
| Rollout | Only Collabora recreated; healthy. `cool.html` loads `cloud-ui.js?v=d704195` and `cloud-sheet-views.js?v=d704195`; the served `cloud-ui.js` contains the P27 overlay. |
| Drive registration | `tools/verify_test_collaboration.py`: registered, Microsoft-format creation available, ODF creation hidden, editor origin verified. |
| Rollback point | Previous profile, editor mounts and controller Compose (the `ebd3fdd` editor) retained privately on the test host. |

## Real-editor acceptance

Pending, owner browser: the P27 acceptance list in the maintainers' task list (private operations repository)
(including "inside a P34 sheet view") and the P34 two-user checks. Not
production-ready until they pass. The simulated-editor check models the popup
DOM from the pinned bundle; it does not replace the real-editor checks.

# Release `7b49aa5` — permanent test validation, 17 November 2026

Branch `claude/release-2026-11-17`: `main` plus project principles, P01 idle
menu recovery with the realtime resume fix, the Socket.IO origin fix, and the
P27 + P34 editor build (AutoFilter search with second-search and Lock
handling, batched dialog events, diagnostics off by default; automatic private
sheet views with ribbon-green headers). P03 eKYC is deliberately excluded
(deferred by the owner). Owner acceptance for these items is recorded in the
test-integration history: P01 60-minute sleep test, realtime/Raven, P27 first
and second searches, P34 two-person test.

Deployed to the permanent test site exactly as built from this revision:
- eKYC India uninstalled from the test site first (database backed up; it had
  no configuration or request logs).
- New 9-app core `erp-test-core:7b49aa5` (all 9 sources verified), add-on
  `erp-test:7b49aa5-runtime`, editor rebuilt from the pinned digest, ingress
  re-rendered (the Digio webhook route is removed).
- ERP mounts unchanged; ERP Compose changed only in image tags and the
  configurator app list (no `ekyc_india`); editor Compose unchanged; proof key
  preserved; same service UUIDs; configurator rerun (exit 0).
- Gates: 302 files checked, 18 suites passed; simulated AutoFilter check
  20/20.

| Check on test | Result |
| --- | --- |
| Installed apps | Nine upstream apps plus erpnext_drive_integrations; no ekyc_india. |
| P01 resume fix served | Present. |
| SSO gate | ERP API and the former Digio webhook path redirect to SSO (302). |
| Realtime | Browser-like Socket.IO handshake accepted. |
| Drive editor registration | Registered; Microsoft creation; ODF hidden; origin verified. |
| AutoFilter, real editor | First search 2 of 60; second search 10 of 60; with Lock 12 of 60. |

Ready for production promotion of exactly `7b49aa5`, with a production
backup and saved rollback images first (nightly Coolify image cleanup).

## TrueNAS test VM — automatic acceptance (18 November 2026, release `7a395f7`)

Host: TrueNAS VM, built from the repository (core `a95ddc9`, ERP add-on
`a2bbaf7`, Mail `a95ddc9`), refreshed from production at 03:11 UTC
(pause 44.5 s, counts verified), served publicly through the production
relay after the DNS switch.

| Check | Tool | Result |
|---|---|---|
| ERP queues | `tools/verify_test_queues.py` | short and long finished |
| Drive office registration | `tools/verify_test_collaboration.py` | registered; Microsoft creation; editor origin verified (ODF creation off, as before) |
| Drive → DMS processing | `tools/verify_test_processing.py` | passed: text extracted, owner and personal privacy verified, test link verified |
| ERP assets | `tools/verify_erp_assets.py` | 92 manifest entries, 28 hook assets, none missing |
| Document worker | refresh-managed | healthy after enrollment |
| App OAuth client | bootstrap | test redirect URIs restored; production copy blocked |

Remaining owner browser checks: sign-in and menus, Collabora AutoFilter
search/second search/Lock (P27), private sheet views (P34), refresh button
and last-refreshed time, idle menus after sleep (P01).

# P37 rehearsal — existing volumes reused, 17 November 2026

Revision `9eb77ce` (branch `claude/p37-production-erp-move`). On the permanent
test site the ERP stack was re-rendered with `existing_volumes` mapping
`erp-db-data`, `erp-sites` and `erp-redis-queue-data` to the site's own
current volumes, and re-registered (same UUID). The controller Compose
changed only in its volume block (now external, same names); ERP mounts were
unchanged. Database, Redis and every running ERP role were recreated.
Record counts before and after were identical (User 8, Company 1, File 14,
others 0); 11 apps listed; the site answered through SSO. Test database was
backed up first. This rehearses the mechanism production will use to keep
its data when moving to the repository-built deployment (P37).
