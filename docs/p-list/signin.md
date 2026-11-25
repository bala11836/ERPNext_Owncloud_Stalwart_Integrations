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

### P76 — Owner's passkey sign-in on the test site

**App:** signin · **Also touches:** test-site · **State:** in progress

**Found 24 November 2026:** after the owner's account
became a native Test Authentik administrator without a production link, its
test passkey (Bitwarden) passed on the normal test sign-in page, but the final
login step admitted only the synthetic accounts, so no session was created.

**Objective:** the owner signs in on test.example.com with the test passkey
alone, as on production. **Scope:** only the `mobile-attendance-qa-eligible`
login policy in `deployment/test-identity/configure.py`. Synthetic accounts,
linked staff, the passkey stage, applications, test ERP and test Drive are
unchanged. **Acceptance:** a policy dry run on test covers the owner with an
approved and a disallowed provider, without a passkey, synthetic, bootstrap
admin and linked staff accounts; then the owner completes a real passkey
sign-in on test.example.com and reaches the ERP.

**Status 25 November 2026:** applied to test; the owner signed in on
test.example.com with the passkey and reached the ERP. The provider list moves
to one setting in P79. Released together with P77 to P79; merged to public `main` 25 Nov (PR #72, `f4a3f37`).

### P77 — First administrator chosen at setup; built-in `akadmin` switched off

**App:** signin · **Also touches:** test-site · **State:** in progress

**Why:** a fresh Authentik setup creates the built-in `akadmin` account with a
generated password nobody uses, and nothing asks who should administer the
system. Upstream's first-time setup page reopens whenever `akadmin` is missing
or has no usable password, so deleting it would expose that page.

**What (owner decisions, 25 November 2026):** the setup asks the person setting
it up for the administrator's email and name (no password). It creates that
administrator and shows a single 24-hour link, only on the operator's terminal,
to register a passkey from an approved provider (P79). The administrator signs
in with the passkey only (no password) and manages other users. Rerunning the
same command on the server issues a new link when the passkey is lost. `akadmin`
is switched off, not deleted: inactive, a random password nobody knows, out of
the admin group, and the bootstrap password file removed. The test invitation
helper uses the configured administrator instead of `akadmin`. On test, the
owner's account becomes passkey-only.

**How it is tested:** a throwaway Authentik from scratch on the test VM (setup
prompt, link, passkey sign-in, setup page stays closed, rerun link, `akadmin`
cannot sign in), then the real test instance with the owner's sign-in checked
again. Production is not touched; whether production has an `akadmin` is a
separate step with its own go.

**Production (25 Nov):** done. `akadmin` recreated switched off via `--akadmin-only`
(PR #73, `0ed08d4`), and the owner's production administrator is passkey-only.
The owner's browser sign-in check is pending.

**Status 25 November 2026:** on test. Public draft PR #72 (module `6586c38`,
CI green), throwaway test passed, Test Authentik switched over (the owner's
account is the passkey-only administrator, `akadmin` off). Merged to public
`main` 25 Nov (PR #72, `f4a3f37`, tree equal to tested `f5b4f89`); production pending.

### P78 — Invitation link attempts chosen by the administrator

**App:** signin · **Also touches:** none · **State:** in progress

**Why:** the invitation form creates single-use links, which Authentik consumes
as soon as the link is opened, even if passkey setup then fails.

**What (owner decisions, 25 November 2026):** the Invite users form asks how
many attempts the link allows, 1 to 5, default 5. Each opening of the link counts
as one attempt. A successful passkey setup ends the link immediately, whatever
attempts remain. The same choice applies to recovery invitations for a lost
passkey. **Tests:** attempts counted per opening, link refused after the last
attempt and after success, existing single-use behaviour at 1.

**Status 25 November 2026:** on test from public `2530a3f` (draft PR #72 with
P77 and P79, CI green). Live links on the test enrollment flow and the shared
policy logic passed; production recovery and first-time flows are not on test.
Merged 25 Nov (PR #72, `f4a3f37`); production needs a separate go.

### P79 — Approved passkey providers as one setting

**App:** signin · **Also touches:** test-site · **State:** in progress

**Why:** the approved-provider list (Apple Passwords and Bitwarden) is copied in
five places, and phones running Android 13 or older cannot use a third-party
passkey app, so their users need Google Password Manager.

**What (owner decisions, 25 November 2026):** one setting lists the approved
providers: Apple Passwords, Bitwarden (also used with Vaultwarden), Google
Password Manager and Chrome's own Mac store. Everything else is refused, including
providers that report no identity. Every check reads that setting, including the
test passkey stage for the synthetic accounts. Chrome's Mac store keeps the passkey
on one Mac only, so a lost Mac needs a recovery invitation. Test first;
production only with a separate go after the upstream advisory check.

**Production (25 Nov):** done with `tools/identity_passkeys_p79.sh` (7 stages, 6
production policies). Rollback point `<rollback folder>`.
Production email wording and P78 on production wait for P49.

**Status 25 November 2026:** on test from public `2530a3f`
(`passkey-providers.json`, `tools/sync_passkey_providers.py`); every Test
Authentik passkey step uses the five providers. Not merged; production needs a
separate go.
