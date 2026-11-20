# ERP portal, SSO session and mobile (`portal-sso`)

Portal home, authentik SSO sign-in and global logout, shared-browser logout guard, idle proxy-session recovery (P01), native mobile login binding, web push, module header and placeholder/signed-out pages.

## Purpose

Turns ERPNext into the office portal behind authentik SSO: sign-in and global logout across apps, a shared-browser logout guard, recovery of menus after the SSO proxy session lapses while idle (P01), native mobile login binding, web push and the portal module header.

## Contents

- `erpnext_drive_integrations/portal/*`
- `erpnext_drive_integrations/public/session.js`
- `erpnext_drive_integrations/public/push-client.js`
- `erpnext_drive_integrations/public/push-worker.js`
- `erpnext_drive_integrations/public/module-header-*.js`
- `erpnext_drive_integrations/www/signed_out.*`
- `erpnext_drive_integrations/www/place_holder.*`
- `erpnext_drive_integrations/www/__init__.py`
- `tests/portal/**`

Excluded (owned by another module): `erpnext_drive_integrations/portal/test_refresh.py`

## Requirements

Modules: `erp-addon-shell`, `authentik-identity`.

authentik with an ERP proxy provider (forward auth) and an OIDC provider; Frappe Social Login Key for authentik.

## Reuse

Reusable for any Frappe 16 site behind an authentik forward-auth proxy: keep `portal/` plus `public/session.js` and `public/module-header-*.js`, and enable the `portal` feature.

## Configuration

Site config keys: `cloud_sso_enforced`, `cloud_sso_auto_provision`, `cloud_oidc_issuer`, `cloud_combined_site`, `cloud_dashboard_host`, `cloud_default_app`, `cloud_cookie_host_only`, `cloud_native_mobile_clients`, `cloud_raven_mobile_enabled`, `cloud_raven_mobile_client`, `cloud_push_enabled`, `push_relay_server_url`, `host_name`. Asset URLs are versioned by the runtime renderer.

## Tests

- `tests/portal/test_mobile.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- Frappe Framework — MIT — https://github.com/frappe/frappe
- authentik — MIT (core) — https://github.com/goauthentik/authentik

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).

Test-site marker: on hostnames starting with `test.` or `test-` (enforced by the renderer) this module shows the shared TEST SITE marker, a 3px striped top line with a small tab, top window only, no layout space. Portal and Frappe apps: `session.js` (Desk, Raven, Insights) and `www/place_holder.html`.

## Desk and branding

The portal page is called **Desk** (title and the text beside the logo); the route stays `place_holder` because `/desk` is Frappe's own route. The logo and favicons come from the tenant's private runtime profile (`company_logo`, `company_favicon_dir`); the repository ships neutral placeholders. The menu's home button uses the compact favicon, the brand at the top left the full logo.
