# Field operations (`field-operations`)

Field sites, assets, members, worker assignments, shift allocation, attendance and checkout, with the field team web page.

## Purpose

Field work for construction projects: sites, site assets and members, worker assignments and their events, shift allocation, attendance and a checkout flow, with a mobile-friendly field team page.

## Contents

- `erpnext_drive_integrations/field/**`
- `erpnext_drive_integrations/cloud_field/**`
- `erpnext_drive_integrations/public/field/**`
- `erpnext_drive_integrations/www/field_team.*`

## Requirements

Modules: `erp-addon-shell`.

ERPNext and Frappe HR (employees, projects).

## Reuse

Keep `field/`, `cloud_field/`, `public/field/` and `www/field_team.*`, enable the `field` feature, and migrate to create the DocTypes.

## Configuration

No site-config keys; roles come from the shared role fixtures (`erp-addon-shell`). Permissions are enforced server-side in `field/permissions.py` and `field/guards.py`.

## Tests

- `erpnext_drive_integrations/field/test_checkout.py`
- `erpnext_drive_integrations/field/integration_tests.py` (needs a live test site)

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- ERPNext — GPL-3.0 — https://github.com/frappe/erpnext
- Frappe HR — GPL-3.0 — https://github.com/frappe/hrms

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
