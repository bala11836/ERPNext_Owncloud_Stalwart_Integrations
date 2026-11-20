# ERP add-on shell (`erp-addon-shell`)

The single installed Frappe app: hook composition with per-feature switches (cloud_features), bootstrap, migration, shared role fixtures and app logos.

## Purpose

Installs one Frappe app, `erpnext_drive_integrations`, that composes independent feature fragments (`portal`, `field`, `onboarding`) into Frappe hooks. Each feature can be switched off per site without deleting its data.

## Contents

- `pyproject.toml`
- `MANIFEST.in`
- `erpnext_drive_integrations/__init__.py`
- `erpnext_drive_integrations/hooks.py`
- `erpnext_drive_integrations/bootstrap.py`
- `erpnext_drive_integrations/migration.py`
- `erpnext_drive_integrations/modules.txt`
- `erpnext_drive_integrations/patches.txt`
- `erpnext_drive_integrations/README.md`
- `erpnext_drive_integrations/fixtures/**`
- `erpnext_drive_integrations/public/app-logos/**`
- `erpnext_drive_integrations/public/company-logo-*`
- `erpnext_drive_integrations/public/company-favicon*` (neutral placeholders; the tenant supplies its own through the private profile)
- `tests/test_hook_composition.py`

## Requirements

Modules: none.

Frappe Framework 16, ERPNext and Frappe HR (declared `required_apps`).

## Reuse

Copy this package with only the feature folders you need; `hooks.py` imports only enabled fragments. Remove a feature folder and set it to `false` in `cloud_features` to drop it cleanly.

## Configuration

Site config `cloud_features` (for example `{"field": false}`) disables a feature's hooks. Optional private `cloud_legacy_rpc_aliases` maps old RPC names during migrations. Never uninstall the app to disable a feature: uninstall removes owned DocTypes and data.

## Tests

- `tests/test_hook_composition.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- Frappe Framework — MIT — https://github.com/frappe/frappe
- ERPNext — GPL-3.0 — https://github.com/frappe/erpnext
- Frappe HR — GPL-3.0 — https://github.com/frappe/hrms
- Frappe Suite app logos — per upstream frappe/suite — https://github.com/frappe/suite

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
