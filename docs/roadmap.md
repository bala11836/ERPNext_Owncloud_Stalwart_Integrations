# Carried-forward roadmap

Reconciled **15 November 2026 (Asia/Kolkata)** against the previous planning documents, current source, deployment notes and read-only production checks. These are work items to schedule, not instructions to deploy, copy mail, change protocol access, expose links or connect an AI provider now.

This document preserves the useful requirements from the previous repository without requiring that repository to remain available. Product references have been updated to the retained ownCloud Drive, Stalwart/Bulwark Mail and Paperless stack. The the maintainers' task list (private operations repository) remains the operational task index.

## Status map

| Requested item | Current disposition | Task |
| --- | --- | --- |
| 1. Push and session-bound native Raven | Session-binding and push source retained; current-stack device/realtime acceptance remains due | P14, P01 |
| 2. Raven attachment storage and Drive | Planned integration; native chat storage is not replaced | P16 |
| 3. Drive-linked Mail attachments over 200 KB | Existing picker attaches file bytes; automatic expiring-link handling is not implemented | P17 |
| 3. Mail-only access restriction | Reopened for discussion on the current Mail stack; no endpoint restriction selected | P18 |
| 4. Desktop folder sync | Native ownCloud capability/client SSO available; actual selected-folder and device acceptance remain due | P10 |
| 5. Three Google Workspace mailboxes | Planned mail-only migration to Stalwart and the current Mail UI | P19 |
| 6. ERP transaction scans | Revised to authoritative Paperless documents referenced by ERP links; replaces direct object-storage work | P20 |
| 7. Client/project correspondence | Paperless is selected and deployed; the ERP correspondence register/integration remains planned | P21 |
| 8. Permission-controlled ERP assistant | Planned read-only first phase; no model/tool access enabled by this plan | P22 |

## 1. Push and session-bound native Raven

Retain `erpnext_drive_integrations/portal/mobile.py`, `portal/push.py`, their hooks and public push assets. The native OAuth bridge requires approved browser/identity sessions and PKCE S256, binds refresh/access tokens to those sessions, and checks revocation and user/client identity. Native Frappe token/resource checks and the validating ingress routes remain necessary. A Bearer header alone does not authorize access.

Earlier recorded ERP/HR phone notification tests belong to the previous deployment checkpoint. They are useful evidence, but do not establish current-portal or upgraded-client acceptance. Raven background delivery from another user was not established by same-user message synchronization or a relay HTTP success.

Schedule:

- Recheck native Raven login, boot/chat access, refresh, expiry, logout and revoked/invalid-token refusal on the current deployment.
- Resolve the separately recorded realtime/idle issue in P01 while preserving origin and authentication checks.
- Verify the portal's per-device opt-in controls, ERP/workflow and native HR notification receipt and tapping, and Raven other-user background delivery on actual supported devices, including a closed iPhone app/PWA as applicable.
- Preserve encrypted private device/session state and opt-out/logout behavior. Keep callbacks exact and challenge-validated. Preserve unrelated workers, drafts and offline data.

Use controlled test identities and messages when this work is scheduled; this documentation update sends none. See P14 and [source review](source-review.md).

## 2. Raven attachment storage and Drive

Keep live chat messages in Raven/Frappe's database. Optional history export to Drive is an archive, not a replacement live chat database. Current Mail picking and Drive-to-Paperless processing do not implement Raven attachment integration.

- Audit the installed Raven attachment/File hooks and web/mobile/API upload paths, present usage and monthly growth. Budget ERP files, Mail, databases, DMS and backups separately; do not treat an illustrative usage rate as measured capacity.
- Design a supported single-copy attachment/reference flow where feasible. Do not move raw private-file directories or assume Drive quotas already cover Raven uploads.
- Prefer channel/project ownership for shared attachments rather than assigning every shared item to one user's folder.
- Preserve channel/message permissions, Drive authorization, previews, search, download and access revocation. A link or folder must not disclose a private conversation or retain access after membership is removed.
- Agree quota ownership, enforcement on every upload route, usage alerts, retention, versioning, deletion/shared-reference behavior, storage location and backup policy before implementation. No quota or automatic deletion duration is selected.
- Validate migration by manifest/checksum and permission tests, interrupted transfer/retry handling and rollback before changing references or removing copies. Use supported hooks in this addon rather than vendor core changes.

## 3. Mail attachments and Mail access policy

### Implemented picker

`integrations/mail/overlay/components/email/owncloud-attach-button.tsx` accepts an ArrayBuffer from the authenticated Drive picker and constructs a `File` for the Mail composer's normal attachment flow. `integrations/drive/mail-picker.js` downloads the selected file inside Drive and transfers its bytes, not its OIDC token, to the matched Mail window.

The current limit is **25 × 1024 × 1024 bytes**, labelled 25 MB in the UI. This is convenient selection from Drive, not automatic public sharing, automatic link insertion, single-copy Mail storage or the old 200 KB rule. The retained production picker source agrees with this implementation. No mail was sent for this audit.

### Planned automatic link handling

The earlier accepted requirement covers **both outgoing and incoming attachments larger than 200 KB**. Reimplement that requirement for current Mail/Stalwart and ownCloud Drive, rather than reviving the former mail client.

- Store eligible attachment content in Drive and present/send links through a supported server-side ingestion/send path. A composer-only control cannot enforce a rule for all supported sending clients or incoming messages.
- External recipients are to use expiring bearer links without signing in. Anyone receiving a forwarded bearer link can use it until expiry/revocation; sharing must not expose sibling files/folders.
- The expiry duration is still undecided. Define revocation, download auditing, recipient/forwarding behavior, retention, quota accounting, deduplication, orphan cleanup and failure/retry handling.
- Confirm whether KB means decimal or binary bytes, whether the threshold is per-file or aggregate, and how inline images, signatures, existing drafts and smaller attachments behave. Do not silently remove an attachment when link creation fails.
- Preserve signed/encrypted incoming originals and historical MIME. Decide raw-message retention and resulting storage duplication/accounting explicitly; do not silently rewrite signed mail or historical imports.
- Test internal/external recipients, access expiry and revocation, shared send-as, drafts/retries, forwarding, incoming extraction and unsupported/encrypted formats before acceptance.

### Access policy requiring discussion

The historical “only the suite client may access Mail” wording no longer defines the current architecture. Discuss allowed use through the portal/current webmail and native clients, and decide which JMAP, IMAP, POP, submission and DAV endpoints are needed.

The current authenticated public Mail UI/API and private administration remain the recorded baseline. Do not shut endpoints or change network exposure from this planning note. Preserve public SMTP reception and required ERP/authentik SMTP sending. Calendar/contact clients, integrations and recovery access must be considered before limiting protocols. Hiding an endpoint does not prove an authorized request came from one official UI, or prevent a user copying data they can access.

## 4. Native Drive desktop synchronization

The old proposal to assess/build synchronization for the retired Drive product is superseded by **ownCloud's native desktop synchronization capability**. The desktop client and separate SSO registration already exist; web/desktop/iOS display names are Drive. No new custom sync client is a current task.

Actual folder selection and upload/download synchronization were not confirmed after the hostname/client changes. Keep those checks in P10, alongside mobile and DAV acceptance without calling the capability undeployed.

- Agree the required desktop operating systems and local selected/shared folders, without overwriting existing local files.
- Verify initial upload/download, offline editing and conflict copies, rename/move/delete propagation, interrupted and large transfers, quotas and shared-Space permissions.
- Verify passkey/OIDC callback and refresh/revocation behavior with the installed client versions. Revoking server access does not erase already downloaded local copies.
- Use supported file APIs/client sync, not raw server directories or direct storage credentials. Keep browser/PWA offline caching a separate concern.

## 5. Three Google Workspace mailboxes

Keep the confirmed **email, folders/labels and sent-mail** scope, now targeting Stalwart and current Mail. Contacts, calendars and Google Drive data are not included. This is separate from the earlier decision not to migrate the retired local mail server. No three source addresses, domain or source-account credentials are assumed.

1. Inventory the three source identities, aliases/groups/forwarding, sizes/counts, Gmail label/archive behavior, flags and special folders. Agree destination mailbox ownership/shared access and authentik mappings; preserve the current integration sender and personal mailbox.
2. Identify the actual authoritative DNS and account access. Changing mail DNS is not approval to transfer registration or all DNS hosting.
3. Choose installed-version-compatible import/export tooling after review. Obtain source read/export access privately; preserve originals. Plan label mapping/deduplication and trash/spam handling.
4. Prepare destination capacity, quotas and recovery, then initial copy while Google still receives mail. Validate counts with an agreed label interpretation, dates, sent mail, flags, representative attachments and permissions.
5. Agree cutover/rollback, catch-up copying and mail DNS/authentication changes. Validate inbound/outbound delivery and all three users' access, with PTR/SPF/DKIM/DMARC as applicable. Avoid conflicting SPF records and retain any still-needed Google authorization.
6. Obtain acceptance before retiring Google mail service. Google Workspace cancellation, other Google products and retention/billing are separate decisions.

Do not apply the new link-attachment policy to historical MIME as an implicit part of this migration. Import tool, addresses/mappings, date, retention and cancellation remain undecided. No source data, mailbox or DNS is changed by this plan.

## 6. ERP transactions reference Paperless documents

The current decision **replaces the former direct S3/object-storage implementation task**. Paperless holds the authoritative transaction scan and OCR/search derivatives; ERP transactions reference the Paperless document's stable ID/link rather than keeping another attachment copy for each association.

Paperless and the owner-aware Drive processing worker are already deployed. That worker processes Drive uploads and adds DMS links/tags; it does not add transaction associations to ERP. The read-only schema audit found no DMS/Paperless custom-link fields or correspondence register. Existing worker behavior preserves Drive originals; this plan does not authorize deleting them.

- Agree the eligible ERP document classes, link fields/reference model, ownership and supported upload/scan workflow. Distinguish relevant business scans from avatars, application assets and unrelated file types.
- Add a permission-checked select/upload-to-Paperless and link flow using supported APIs and addon hooks. Track pending OCR/ingestion, failures/retries and stable document identity; do not leave a broken URL on a transaction when processing fails.
- Support one DMS document referenced by several appropriate transactions. Preserve native ERP document/field permissions and DMS document access; a URL must not grant new rights or expose private document titles/previews.
- For existing eligible attachments, inventory hashes/shared references and associations, copy and verify before updating links, and retain rollback/originals until explicit acceptance. Do not blindly rewrite URLs or remove private files.
- Test PDF/image preview/download, OCR/search, denied/revoked access, duplicate/shared references, edits/deletes, imports/API routes and any printing/export/email use that previously relied on a byte attachment.
- Back up/restore ERP link metadata and corresponding DMS originals/derivatives consistently. Storage backend selection is separate from this link integration; native direct-S3 support is not assumed.

## 7. Client/project correspondence register

Paperless selection, deployment and SSO are complete prerequisites, not future product evaluation. The remaining work is the ERP-side incoming/outgoing correspondence register and its Paperless/client/project/transaction integration. Existing vendor response forms or a searchable PDF archive are not that register.

Confirm the fields, numbering, workflow and roles before building. Candidate fields retained from the earlier discussion:

- Client and Project, incoming/outgoing direction, internal/external reference numbers, letter date and received/dispatched dates.
- Subject, responsible employee, response deadline/status, related letter/reply and related ERP transactions.
- Authoritative Paperless document IDs/links and physical-original office/cabinet/file location.

Track the correspondence chain, outstanding responses and responsibilities; provide client/project filters and appropriate searches. Coordinate metadata/permission synchronization and shared-document links with P20. Define deletion/revocation, retention and recovery explicitly. No link should expose another client's/project's correspondence.

Pilot an incoming letter, outgoing reply, transaction links, response tracking, OCR/search, physical-original retrieval, revoked access and restore. Keep native document/identity permissions and central logout requirements. Paperless is not by itself a completed drafting, approval or legal-records workflow.

## 8. Permission-controlled ERP AI assistant

Retain the accepted read-only-first direction, implemented as a modular addon panel plus a separately scoped agent service using approved native Frappe interfaces. No model provider, public MCP endpoint, credential, model data sharing or write permission is enabled by this entry.

- Investigate the installed Frappe release's native MCP/API facilities and maintained UI/agent options when scheduled; do not enable general method access or dynamic client registration as a shortcut.
- Agree a pilot for project reports, pending approvals and attendance summaries, with source-record links and explicit missing/inaccessible-data handling. Example: pending approvals for an example project, monthly project expenses and attendance awaiting approval.
- Use each caller's effective native roles, document/field and client/project permissions. Enforce server-side tool/action allowlists and authorization at execution time. Do not use a shared Administrator identity, direct database credentials, unrestricted SQL, shell/Python execution or unrestricted RPC.
- Later draft replies/transactions may be reviewed previews. Posting, payments, attendance approval, deletion and other consequential writes require separately approved controls; do not enable them automatically.
- Add permission-filtered Paperless/Drive retrieval only after those connectors and access models are validated. Preserve permissions/revocation in indexes, previews, caches, history and conversation/session cleanup. Treat retrieved mail/documents/records as untrusted references, not tool authorization.
- Choose hosted/local model, provider, capabilities, costs/rate limits and data handling/retention/logging before sending business data. Keep keys server-side. Raven is an optional future entry point, not a required AI foundation or proof that the assistant exists.
- Test usefulness, citations, permission isolation, prompt-injection resistance, logout/revocation, auditing, cost limits, failures and upgrades before expanding scope.

## Provenance and scheduling

The retained intent was recovered from the previous repository's `push-support.md` and the seven planning documents for Raven/Drive storage, Mail/Drive links, desktop sync, Google mailbox migration, transaction object attachments, DMS correspondence and the ERP AI assistant. Their November 2026 text has been reconciled here with the current owner's revisions; obsolete product-selection and deployment assumptions are not instructions for the new stack.

These eight topics record future work and its current acceptance boundaries. No dates, automations, provider purchases, data migration or live application changes are scheduled by this document.
