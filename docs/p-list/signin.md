# Sign-in: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 25 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# Sign-in: P items

authentik single sign-on: passkeys, invitations and recovery, global logout, sign-in pages and templates, the identity stack.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P08 — Latest global logout and fresh passkey sign-in

**App:** signin · **Also touches:** portal, erp, drive, mail, dms · **State:** in progress

**Status:** earlier ERP-initiated cross-app logout passed; latest hardening is deployed but not fully accepted end to end.

Verify the final outpost/full-user logout flow ends ERP, Drive, Mail and DMS sessions, reaches the clear signed-out page, and requires a fresh passkey when Sign in is selected. Repeat with each independent app as logout initiator, including multiple open app tabs. Preserve drafts and do not remove authentication protections to make a test pass.

### P25 — Invitation, passkey enrollment and recovery acceptance

**App:** signin · **Also touches:** none · **State:** open

**Status:** native invitation/recovery adapters are retained. Complete real SMTP
and supported-device ceremonies for a fresh user, single-email enrollment,
duplicate/expired invitations, lost-device recovery and account revocation.
Preserve native identity APIs; source tests and an existing administrator's
working passkey do not prove fresh-user enrollment or recovery.

### P49 — Bring production's sign-in pages and templates into the repository

**App:** signin · **Also touches:** none · **State:** open

**Found 20 November 2026:** production's ERP provider mapping sent the legacy
claim `unformat_approved` while the repository ERP requires `cloud_approved`;
new ERP sign-ins failed for days. Emergency fix: the mapping now sends both.
When moving sign-in to the repository build, make the claim name one setting,
add a test that the ERP's required claim is in the provider's mappings, and a
browser sign-in check after every ERP or sign-in deployment.

**Status:** open, found by P45 on 19 November 2026; blocks moving sign-in
(authentik and its support service) onto the repository build. Production's
invitation pages (`<legacy mount: unformat-invitations/public>`, with a stylesheet and
newer admin navigation) and e-mail templates (`unformat-*` names, referenced
by name in authentik's database) are newer than the repository's (`cloud-*`
names, generic branding). Import them into
`integrations/authentik/invite-recovery/`, make the brand name and template
file names profile settings, rehearse on the test site, then switch sign-in
(P45). Also make the webmail product name a setting (production showed
"Unformat Mail"; the repository build shows "Mail").

**24 November progress.** Deployed both administrator entries on the
isolated Test Authentik issuer from public revision `a0541d4`. The test
build takes the companion, stylesheet, admin template and test email template
from the public release commit and requires them at startup. The six
production enrollment and recovery template files match the existing public
templates after applying the deployment brand and template prefix. Production
identity migration and performance settings remain open.

The test companion lists eligible synthetic accounts and links signed-in
administrators to their own native WebAuthn setup. Test invitation email is
disabled because the test sender's SMTP connection closes during authentication.
Browser acceptance intercepts email submission and checks real invitation
creation, listing and cancellation on the isolated issuer.

**Invitation mail follow-up.** The owner approved adding the TrueNAS VM's
single tailnet IP to the dedicated Stalwart test sender. Test Authentik now
submits via a private, recipient-restricted SMTP relay. The live companion
has Send enabled at public revision `7088f51`. Stalwart accepted all three
requested enrollment messages. The owner's external mailbox visibly showed the
supervisor invitation. The other two messages were accepted, with no mail
for the mailbox remaining on the Stalwart queue. The existing single-use
links were retained and expire at 19:44 IST on 24 November.

**PR #63 merged.** The public invitation module and future build checks are
on `main` at `5db9a66`. The merge tree matches the tested TrueNAS revision
`7088f51`. A clean stage from merged `main` included the approved favicon set
and the test invitation mail setting. Production identity reconciliation
and promotion remain open under P49.

**Production cutover preflight.** [PR #67](https://github.com/rdavuluri44/ERPNext_Owncloud_Stalwart_Integrations/pull/67)
updates the affected identity pins and renders both gateway configs. All
GitHub checks and the isolated PostgreSQL 16.15 to 16.16 upgrade rehearsal
passed. A production scratch render preserved the running environment and
external peers, and a verified root-only rollback backup was captured.
Production SMTP already fails authentication from the current Authentik
worker. Resolve its source-IP restriction during the authorized cutover.
See the private cutover runbook (private record).

**PR #67 merged.** Public `main` is `288993c` with the exact tested tree.
The live SMTP connection reaches Stalwart from a shared bridge address
different from the exact address on the production credential. The merge is
complete. A dedicated SMTP route and production cutover still require approval.

**Production deployed.** Both identity stacks are at public `288993c`. A
dedicated worker SMTP route authenticated before and after recreation.
The initial native sign-in and admin HTTP 500 was traced to restrictive
asset file permissions, corrected in the private renderer and verified
over HTTPS and in Chrome. PostgreSQL is 16.16 with JIT off, both companions
are on NGINX 1.30.8, and the server's 3 GB cap and memory alert are active.
Production issuer discovery, signing keys, existing ERP session, both
invitation controls, and JWT rejection at the ERP logout endpoint passed.
P59 marks both identity stacks clean. A fresh physical passkey ceremony
and delivery of a new production invitation were outside this check.

**Carry into the repository identity stack (found 20 November 2026):**
PostgreSQL `jit = off` for authentik's database (sign-in step 1.2 s to 0.3 s);
a higher memory limit for the authentik server (3 GB; the host has about 7.5 GB
spare) and a cap on gunicorn worker lifetime/memory, because a worker grew to
1.46 GB over five days; a memory alert; check `AUTHENTIK_CACHE__TIMEOUT_POLICIES=0`
(policy caching is off in the legacy stack since the 14 November move, origin
unknown) and decide whether to keep it. Compare the running environment of old
and new containers when switching (lesson of the Mail move).
