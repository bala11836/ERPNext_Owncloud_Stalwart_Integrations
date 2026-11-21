# Sign-in: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 21 November 2026
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

### P44 — Sign-in (authentik) as a repository stack

**App:** signin · **Also touches:** none · **State:** done

**Status:** done 19 November 2026. The repository `identity` stack (same
pinned images as production) is now proven restorable: the nightly backup
gained the authentik media volume and invitation templates (they were
missing), `tools/restore_identity.py` reuses production's secret key and
passwords from the backed-up Coolify compose, and a renderer defect that kept
the identity stack from rendering (Compose double-dollar escapes) was fixed.
On the old VPS the stack was rendered from release `a2c7fb2`, quarantined (no
e-mail), and loaded from the backup in 1 min 21 s after image downloads:
11 users, 19 applications and 18 OAuth2 providers, identical to production,
and the users' sign-in identifiers match production exactly (fingerprint
compared), so the apps would recognise every user. Production sign-in itself
still runs the pre-repository service; moving it onto this stack is a later,
separate change.

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

**Carry into the repository identity stack (found 20 November 2026):**
PostgreSQL `jit = off` for authentik's database (sign-in step 1.2 s to 0.3 s);
a higher memory limit for the authentik server (3 GB; the host has about 7.5 GB
spare) and a cap on gunicorn worker lifetime/memory, because a worker grew to
1.46 GB over five days; a memory alert; check `AUTHENTIK_CACHE__TIMEOUT_POLICIES=0`
(policy caching is off in the legacy stack since the 14 November move, origin
unknown) and decide whether to keep it. Compare the running environment of old
and new containers when switching (lesson of the Mail move).

### P56 — Logging out of any app lands on the website

**App:** signin · **Also touches:** portal · **State:** done

**Status:** open, owner request 20 November 2026 ("build the new desk portal like
logging out of any app brings the user onto the webpage www"). Starts after the
logo, favicon, landing page and "All apps" job (P55, P47, P52) is merged and on
production, because it needs the landing page to exist. **Today** every logout
(ERP, Drive, Mail, DMS, the portal's own logout, and idle logout) ends on the
ERP's "You're signed out" page: the destination is hard-coded in four scripts
(`public/session.js`, `integrations/drive/workspace.js`,
`integrations/dms/cloud_session/session.js`,
`integrations/mail/overlay/lib/cloud-session.ts`) and in the global-logout
code (`portal/sso.py` `finish_logout`, `www/signed_out.*`). **Target:** after
the global logout has finished (ERP session, authentik session, app sessions)
the browser lands on the website: `https://www.<domain>/` in production,
`https://test.example.com/` on the test site (the landing page is served at
its front path), where the "EMPLOYEE ZONE" text is the way back in (it leads to
the portal and its sign-in). Design: one tenant-neutral setting for the
landing address in the private runtime profile (new `www` host in the
renderer's host map; on test it equals the ERP test host), used by the renderer
to replace the logout destinations in all four scripts, the server-side
redirect and the signed-out page; authentik's allowed post-logout redirect
addresses (blueprint `configuration.json` and the live production providers)
must include the landing address, with a backup of the provider rows first.
Order (owner's rule): branch, deployed to test and validated in a browser for
every app (log out of ERP, Drive, Mail, DMS and the Desk: each must end on the
landing page, with the sign-in session really gone; refreshing the page must
not log back in silently), merge, then production with a rollback point. Keep
the shared-browser logout guard and the idle-logout behaviour working (P01) and
add tests that fail if a logout destination is hard-coded again. Later part of
P47 (not this task): moving the portal shell itself onto `www` with `#erp`,
`#mail` routes.

### P56 — Logout ends on the website; one passkey prompt; portal keeps its name

**App:** signin · **Also touches:** portal · **State:** done

**Status:** **live on production 20 November 2026 (`792cef8`)**, owner browser
test on test passed. Was: branch `p56-desk-logout-signin`: (a) portal
page exactly as before except the logo (title and company name restored; same
logo in the menu's home button); (c) one landing address `sso.LANDING` from the
private profile's `landing_url` (production default https://www.example.com/,
test https://test.example.com/), ERP forwards `/login?logged_out=1` and guest
`/signed-out` there; authentik's logout flow still needs a redirect stage to the
landing address (separate flow for the test providers); (d) sign-in sends
`max_age=600` instead of `prompt=login`/`max_age=0` (cause of the double
passkey prompt), callback accepts an authentication from the last ten minutes.
Owner browser test on test pending (blocked by the proxy `mailprivate`
incident). Then production: one add-on rebuild and ERP swap, authentik brand
logo/favicon and plain sign-in background (`plain-background.svg`), logout
redirect stage, webmail favicon env.
