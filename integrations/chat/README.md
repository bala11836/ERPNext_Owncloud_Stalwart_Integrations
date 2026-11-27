# Chat (Matrix: Synapse and its authentication service) (`chat`)

The internal chat server: Synapse with the Matrix Authentication Service, signing in through the sign-in service; its stack and the script that writes both configurations.

## Purpose

The company's own chat (P73; owner, 27 November 2026): a Matrix server that replaces Raven and is used from inside the phone app. People sign in with the same passkey as everywhere else: Synapse hands sign-in to the Matrix Authentication Service (MAS), and MAS sends people to the sign-in service (authentik).

Fixed choices, set in `configure.py`:

- **Sign-in only through the sign-in service.** No passwords, no registration; people cannot change the name or mail address that comes from the sign-in service, or deactivate their account.
- **No federation at first.** No other Matrix server is contacted or answered.
- **Rooms are not encrypted by default,** so the company can keep, search and export them.
- **The server name is permanent.** It is part of every address (`@name:chat.<domain>`) and Matrix does not allow renaming a server. Choose it before the first start.

## Contents

- `integrations/chat/**`
- `deployment/stacks/chat.compose.json`
- `tests/test_chat_stack.py`

Services of the stack:

| Service | What it is | Reachable |
|---|---|---|
| `configure` | runs once before the others; writes both configuration files and, the first time, MAS's signing key | no |
| `synapse` | the chat server | `chat-synapse:8008` on the workspace network |
| `mas` | the sign-in service for chat | `chat-mas:8080` on the workspace network |
| `database-synapse`, `database-mas` | one PostgreSQL each (Synapse needs the `C` locale) | inside the stack only |

## Requirements

Modules: `authentik-identity`.

Two host names (`chat` and `chat-auth` in the profile's `hosts`), and an OAuth2/OpenID provider in the sign-in service for MAS: confidential client, redirect address `https://<chat-auth host>/upstream/callback/<UPSTREAM_ID>`, scopes `openid profile email chat`. The `chat` scope is a scope mapping that returns the person's `chat_name` attribute (`deployment/scope-mappings.example.json`).

## Reuse

Add `chat` to the profile's `projects`, name the two hosts, supply the provider's client secret, render with `tools/prepare_runtime.py` and register the stack like any other (`tools/coolify_native.py`). The proxy sends the chat host's `/_matrix`, `/_synapse/client` and `/_synapse/mas` to Synapse, the three delegated paths `/_matrix/client/*/login`, `logout` and `refresh` to MAS, and the whole `chat-auth` host to MAS (`tools/prepare_ingress.py` does this for a test site). Synapse's admin interface (`/_synapse/admin`) is not routed.

## Configuration

Settings are in `deployment/stacks/inputs.json` as `CI_CHAT_CONFIGURE_*`:

- **Names:** `CHAT_SERVER_NAME`, `CHAT_PUBLIC_URL`, `CHAT_AUTH_URL` (defaults follow the `chat` and `chat-auth` hosts).
- **Sign-in service:** `UPSTREAM_ISSUER`, `UPSTREAM_CLIENT_ID`, `UPSTREAM_CLIENT_SECRET` (required, never generated), `UPSTREAM_ID` (a fixed ULID; it is part of the redirect address), `UPSTREAM_NAME`.
- **`LOCALPART_TEMPLATE`:** how a person's chat name is made from what the sign-in service says about them. It must give a valid Matrix name (lower-case letters, digits and `._=-/+`) that never changes for that person. The default is the `chat_name` claim (owner, 27 November 2026: `firstname.initial`, with a number on a clash, made once at onboarding), because sign-in user names are mail addresses, which Matrix does not accept. A person without a chat name cannot sign in to chat.
- **Secrets made by the renderer:** the two database passwords, the secret Synapse and MAS share, Synapse's macaroon and form secrets, and the secret MAS's encryption key is derived from. Do not change the last one after the first start.

The `configure` service rewrites both files at every deployment and keeps the signing key. Private ports: `CI_CHAT_SYNAPSE_HOST_PORT` (8040) and `CI_CHAT_MAS_HOST_PORT` (8050), on 127.0.0.1 only.

Backups: both databases (`pg_dumpall` in each database container) and the volumes `synapse-data` (media and Synapse's signing key) and `mas-config` (MAS's signing key).

## Tests

- `tests/test_chat_stack.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- Synapse — AGPL-3.0 — https://github.com/element-hq/synapse
- Matrix Authentication Service — AGPL-3.0 — https://github.com/element-hq/matrix-authentication-service

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
