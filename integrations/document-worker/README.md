# Drive to DMS document worker (`document-worker`)

Moves new Drive uploads into Paperless with owner-preserving permissions and generated links; enrollment and link retargeting tools.

## Purpose

Processes new Drive uploads into Paperless-ngx for OCR and search while preserving each owner's permissions, and writes generated links back; includes owner enrollment and link retargeting for refreshed test copies.

## Contents

- `integrations/document-worker/**`
- `deployment/stacks/processing.compose.json`
- `tools/enroll_worker.py`
- `tools/retarget_worker.py`
- `tests/test_retarget_worker.py`

## Requirements

Modules: `drive`, `dms`.

Modules `drive` and `dms`; Apache Tika and Gotenberg for extraction and conversion.

## Reuse

Run `integrations/document-worker/document-worker.py` with a configuration like `config.example.json`; enroll owners with `tools/enroll_worker.py`.

## Configuration

`integrations/document-worker/config.example.json` lists every setting; per-owner Drive and Paperless tokens are enrolled privately.

## Tests

- `tests/test_retarget_worker.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- Apache Tika — Apache-2.0 — https://github.com/apache/tika
- Gotenberg — MIT — https://github.com/gotenberg/gotenberg

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
