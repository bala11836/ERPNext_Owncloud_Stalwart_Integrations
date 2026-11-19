# Vendor onboarding and response links (`onboarding`)

Vendor onboarding with KYC and amendments, single-use device-bound response links (yes/no, documents) with audit trail, WhatsApp consent capture, construction schedule page and monitoring.

## Purpose

Vendor onboarding with KYC documents and amendments, and single-use, device-bound response links for vendors and recipients (yes/no answers, document review) with a full audit trail; WhatsApp consent capture for future messaging (P04); a construction schedule page and monitoring.

## Contents

- `erpnext_drive_integrations/onboarding/**`
- `erpnext_drive_integrations/www/respond.*`
- `erpnext_drive_integrations/www/link-help.*`
- `tests/onboarding/**`

## Requirements

Modules: `erp-addon-shell`.

ERPNext (Supplier, Purchase Order); India Compliance for GST data; outgoing email configured in Frappe. A separate response host (`respond.*`) serves the public links.

## Reuse

Keep `onboarding/`, `www/respond.*` and `www/link-help.*`, enable the `onboarding` feature, migrate, and route the response host to the ERP frontend.

## Configuration

Site config keys: `hov_respond_url` and `hov_respond_host` (public response host), `cloud_test_copy` (set by the test runtime; `onboarding_test_copy` is still honoured): test copies do not send email and give the link to the sender's bell, unless `cloud_test_form_smtp` (`host`, `port`, `user`, `password`, `sender`; private profile `site_settings`, never in Git) names a dedicated account. Then form emails, and only those, are sent with a `[TEST]` subject and a test-system banner. Response rules per DocType are records (`Response Rule`).

## Tests

- `tests/onboarding/test_onboarding.py`
- `tests/onboarding/test_respond.py`
- `tests/onboarding/test_kyc.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- ERPNext — GPL-3.0 — https://github.com/frappe/erpnext
- India Compliance — GPL-3.0 — https://github.com/resilient-tech/india-compliance

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
