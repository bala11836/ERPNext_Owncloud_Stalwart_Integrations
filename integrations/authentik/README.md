# authentik identity configuration (`authentik-identity`)

Retained authentik blueprint (providers, applications, scope mappings), test client creation, invitation recovery service and identity-support adapters.

## Purpose

Reproducible authentik setup: a retained blueprint of providers, applications and scope mappings, test client creation that never edits production providers, an invitation recovery service and identity-support helpers.

## Contents

- `integrations/authentik/**`
- `deployment/stacks/identity.compose.json`
- `deployment/stacks/identity-support.compose.json`
- `deployment/scope-mappings.example.json`
- `tools/authentik_blueprint.py`
- `tests/test_invitation_configuration.py`

## Requirements

Modules: none.

authentik (existing instance); run tools under the native `ak shell`.

## Reuse

Apply `configuration.json` through `tools/authentik_blueprint.py`; reuse `invite-recovery/` on its own for single-email invitation recovery (see its README).

## Configuration

Private inputs: template slugs, exact callbacks, approved group and gateway for `configure_test_clients.py`; `deployment/scope-mappings.example.json` for custom scopes. Client secrets stay in authentik.

## Tests

- `tests/test_invitation_configuration.py`
- `integrations/authentik/invite-recovery/test_native.py`
- `integrations/authentik/invite-recovery/test_recovery_guard.py` and `test_invitations.mjs` (run in CI)

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- authentik — MIT (core; enterprise features separately licensed) — https://github.com/goauthentik/authentik

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
