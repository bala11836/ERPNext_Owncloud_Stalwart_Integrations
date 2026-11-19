# Reconstruction verification

This is a live acceptance record, not a claim that every test has passed.
The persistent test deployment is built from this repository, with its own
databases and application services, and the existing identity service for login.
Application code/images are not copied from production. Private branding,
operator configuration and an explicitly separate one-way data refresh are inputs.

## Findings addressed

| Finding | Repository correction | Evidence / next check |
| --- | --- | --- |
| The addon previously needed a prepared private ERP image | Public-source builder, official recipe/base digest, dependency constraints and nine source pins | Core and addon built; independent core build also completed on the test host |
| The India Payroll pin did not reproduce production | Pin official v16.1.0, commit 495f0202d14eb5aabc90973ee7f1cb6143e4d6c9 | Production code matched this tag; the earlier branch tip differed in 17 tracked files and had three extra files |
| Version labels alone missed that discrepancy | Compare tracked source contents with the running image | Compared code/configuration files for the other eight upstream apps matched their pins; corrected Payroll core also built successfully on the test host |
| Identity setup examples were incomplete | Portable native configuration graph and native test-client installer | Fresh authentik graph validated/applied; five test clients created on the isolated identity rehearsal |
| Configuration contained machine-specific names and duplicated mounts | Explicit project templates, logical aliases and shared persistent-mount manifest | Runtime/ingress acceptance remains in progress |
| Public response routes used an obsolete module path | Route only the consolidated module's explicit guest methods; preserve redirect-only internal service | Offline ingress reference and route checks pass |

Fifteen isolated offline test suites pass, including host/role/request boundaries,
portable runtime generation, archive traversal/link confinement and preservation
of deleted generated shortcuts. Browser and native integration acceptance is
recorded separately below; offline suites do not certify devices/providers.

## Persistent test checkpoint

The old test controller has built the public ERP core and consolidated addon from
Git, prepared the pinned Collabora browser overlays, and compiled Mail from its
pinned upstream plus this repository's overlay. Six native service records sit
under one test project. Fresh ERP installed all ten expected apps with scheduler
disabled. Drive, editor, Mail and DMS started against separate empty stores.

Test HTTPS and portal sign-in were exercised. The existing SSO needed a
source-IP-restricted remote forward-auth context bridge; that recipe is now in
`tools/prepare_auth_bridge.py`. A retired duplicate test gateway was detached
from the outpost without deleting its record or changing production providers.

Fresh schema comparison found 694 Custom Fields versus 727 in production. The
25 non-File differences are supplied by native India HR regional setup, not
missing private app code. Eight legacy File fields have no references in the
current app sources and are not fresh-install dependencies. Property Setter
differences include three legacy File overrides and business feature defaults;
these must be evaluated after the production data refresh, rather than copied
blindly as new customization. The initial fresh test showed native setup wizard
content before its business data restore. A browser check reproduced the
already documented realtime Invalid origin issue; it remains deferred.

## Four-app data refresh checkpoint

An empty-store restore/rollback rehearsal passed. The explicitly approved
production exporter then produced a consistent ERP/Drive/DMS/Mail snapshot in
approximately 38 seconds of selected-app maintenance, with automatic restart
and an independent watchdog. SSO and the controllers remained online. One test
restore exposed deleted generated shortcuts; rollback succeeded and the source
was fixed to preserve deletions. The next source restore passed native business
counts, app health, fresh owner-token enrollment and generated-link retargeting.
No production application code or private base image was used for test builds.

The successful snapshot contained eight ERP users, one company, fourteen File
records (four uploaded files), and thirteen Paperless documents including
soft-deleted records. Browser DMS lists nine active documents. Generated links
and notes were retargeted without changing document sharing or recreating
deleted shortcuts. Matched rollback stores and a hash-verified staged archive
remain private on the test host.

Browser comparison subsequently found and corrected per-client Drive discovery,
locale-aware Mail callback registration, cached native Mail service hostnames,
public feature-policy reads, stale iframe return navigation and the official
ERP image's UID/GID mismatch for status files. All corrections are committed
before being pulled/deployed on test. Native ERP asset validation reports 92
manifest entries, 28 hook assets and no missing files.

The test-only refresh control and five-second root worker timer are enabled
after the successful source receipt. The portal displays the durable successful
date/time. Existing SSO is shared; app databases, native mail/drive stores,
processing state, credentials and application hostnames are separate. Test
egress policy has a persistent system service and protocol listeners/scheduled
business integrations remain disabled. See the [runbook](test-rebuild-runbook.md).

## Accepted deployment and remaining acceptance

The persistent replica, real four-app button refresh, synthetic document/editor
checks and automatic post-refresh SSO recovery have now passed. See the
[dated acceptance matrix](test-acceptance.md) for exact evidence, intentional
differences and remaining provider/device work. The following are the release
gates used by that matrix, not a claim that every future roadmap task is done.

- Build the corrected pins on the test controller, then build each modified
  application from the selected Git commit.
- Initialize fresh databases and install the single consolidated custom app.
- Verify app versions, source hashes, asset availability, permissions, SSO and
  all retained menus against production, recording intentional test differences.
- Exercise Drive editing/picker, Mail/DAV/shared mailboxes, DMS ownership/OCR,
  onboarding/field functions and cross-app session behavior with test records.
- Implement and rehearse four-app production-to-test refresh, failure recovery,
  test configuration/credential isolation and durable successful-refresh time.
- Keep the old repository retirement decision separate from unfinished gates.

Test outbound business integrations, public SMTP delivery and production
scheduled actions must remain disabled. Provider accounts and physical-device
acceptance listed in the roadmap are not implied by a successful image build.
