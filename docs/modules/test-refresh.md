# Permanent test site and one-way refresh (`test-refresh`)

Restricted production snapshot export, test-side restore with quarantine of outbound integrations and credentials, refresh button and progress, test profiles, egress policy and the verification tools used for acceptance.

## Purpose

Keeps a permanent test site that mirrors production data one way only: a restricted export on production, a root-only worker on test that validates, restores and quarantines (outbound email, webhooks, schedulers, API keys, sessions, provider credentials), a refresh button with progress, test profiles, egress policy and the verification tools used for acceptance.

## Contents

- `erpnext_drive_integrations/operations/**`
- `erpnext_drive_integrations/portal/test_refresh.py`
- `erpnext_drive_integrations/public/test-refresh.*`
- `deployment/test-refresh-worker.*`
- `deployment/test-runtime.example.json`
- `tools/export_snapshot.py`
- `tools/snapshot_archive.py`
- `tools/test_refresh_worker.py`
- `tools/restore_test_data.py`
- `tools/activate_test_refresh.py`
- `tools/prepare_test_profiles.py`
- `tools/rehearse_empty_test.py`
- `tools/test_egress.py`
- `tools/verify_test_collaboration.py`
- `tools/verify_test_queues.py`
- `tools/verify_test_processing.py`
- `tests/test_refresh_boundary.py`
- `tests/test_refresh_status_files.py`
- `tests/test_restore_boundaries.py`
- `tests/test_snapshot_archive.py`

## Requirements

Modules: `deployment`, `erp-addon-shell`.

Module `deployment`; SSH from test to production limited by a forced command and source address; a test host with Docker.

## Reuse

Install `tools/export_snapshot.py` on the source host and `tools/test_refresh_worker.py` on the test host with root-private profiles; activate with `tools/activate_test_refresh.py` after a verified first restore. See docs/test-rebuild-runbook.md.

## Configuration

Profiles: `deployment/test-runtime.example.json`; systemd examples `deployment/test-refresh-worker.*`. Site config on test: `cloud_test_copy`, `cloud_test_refresh_enabled`, `cloud_test_refresh_users`. Never restore test data into production.

## Tests

- `tests/test_refresh_boundary.py`
- `tests/test_restore_boundaries.py`
- `tests/test_snapshot_archive.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- No upstream product is bundled or adapted.

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
