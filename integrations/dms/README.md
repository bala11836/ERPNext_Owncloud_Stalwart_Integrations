# DMS (Paperless-ngx) adapters (`dms`)

Paperless-ngx session adapter for portal SSO and the Django-shell bootstrap for approved roles and worker enrollment.

## Purpose

Connects Paperless-ngx to the portal: a session adapter so the DMS follows the portal sign-in and logout, and a Django-shell bootstrap for approved roles, groups and the document worker's enrollment.

## Contents

- `integrations/dms/**`
- `deployment/stacks/dms.compose.json`

## Requirements

Modules: `authentik-identity`.

Paperless-ngx; module `authentik-identity` for the portal sign-in.

## Reuse

Mount `integrations/dms/cloud_session` as a Django app in Paperless-ngx and run `bootstrap.py` under the native Django shell with a private enrollment profile.

## Configuration

Enrollment profiles are private JSON outside Git; returned tokens are captured privately and never displayed or committed.

## Tests

- `tests/test_rebuild_templates.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- Paperless-ngx — GPL-3.0 — https://github.com/paperless-ngx/paperless-ngx

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).

Test-site marker: on hostnames starting with `test.` or `test-` (enforced by the renderer) this module shows the shared TEST SITE marker, a 3px striped top line with a small tab, top window only, no layout space. DMS: in the injected `cloud-session.js` (signed-in pages).
