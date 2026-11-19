# Decision log

What we decided and why, for anyone building a similar setup from scratch.
Newest first. Each entry: **decision**, **why**, and where it lives. The
discussion that led to a decision is not repeated here.

## 2026-11-19

### Public repository under AGPL-3.0, operations records private (P35)
- **Decision:** publish the code as a new public repository,
  `ERPNext_Owncloud_Stalwart_Integrations`, under AGPL-3.0-or-later, starting
  from a clean snapshot with fresh history. Dated operations records (release
  log, task list, migration runbooks with real addresses and service IDs) move
  to a private operations repository; the earlier private repository is
  archived with its full history. The company is credited by name; the
  company logo is not published (a neutral placeholder ships, each deployment
  supplies its own). Test and production fetch the public repository.
- **Why:** sharing what we build (owner principle 3) and letting
  contributors work by fork and pull request with branch protection, which a
  free private repository lacks. AGPL keeps changes to network-served
  versions shared, matching the AGPL parts we modify (ONLYOFFICE, Bulwark,
  frappe/suite icons). Fresh history, because the old history contains
  personal e-mail addresses, host names and infrastructure details that a
  scrub of the current files would not remove.
- **Where:** `LICENSE`, `LICENSES.md`, `README.md`, `CONTRIBUTING.md`,
  [method for moving services](production-moves.md).

## 2026-11-18

### Office editor: ONLYOFFICE replaces Collabora (P42)
- **Decision:** replace Collabora Online with ONLYOFFICE Docs (Community
  Edition) as the Drive editor, completely. Order: switch the test site, back
  up, restore production data onto a stack built with ONLYOFFICE on a spare
  machine (P39), then switch production.
- **Why:** Collabora (LibreOffice) converts Excel workbooks to its own model
  and renders on the server: a real 1 MB register took 20 to 40 seconds to
  open, filled sheets slowly and misbehaved with rows; heavy files hit its
  100-second load limit. ONLYOFFICE edits OOXML natively and renders in the
  browser: the same original register opened in 3 to 5 seconds (Collabora 42).
  Its default saving behaviour (changes written to Drive only after everyone
  closes) is handled by its built-in auto-assembly (interval 2 minutes): on the
  test site Drive received an edit about 3 minutes later while the editor
  stayed open, and the final save 7 seconds after closing. No extra watcher is
  needed. ONLYOFFICE 10 calls only WOPI hosts named in its `ipfilter` rules,
  so Drive's WOPI bridge is named explicitly.
- **Layout (owner, final 18 November 2026, for working space):** one header
  row (logo, tabs, file name) with Drive's ⋮ and ✕ placed in it; avatar,
  header search, Share and open-location removed; one always-visible side
  strip on the right in header grey holding both former strips (the pivot
  field list and object settings exist only there; auto-hide was tried and
  rejected); darker row/column headers (#D9D9D9, selected #A6A6A6) because the
  row-number width cannot be changed; Drive's file menu styled like
  ONLYOFFICE's and closed by a click in the editor; square edges. After the
  phone check: ✕ and ⋮ moved to the top left (reachable with a thumb) and
  ONLYOFFICE's logo to the far right in exchange; always
  the light theme (dark mode hid the strip's icons and clashed with the grey
  headers). Final strip: a status-bar button (bottom right, like the sheet
  list) opens it over the sheet on desktop and phones, replacing the
  always-visible strip and a phone edge handle; phones use the desktop editor
  because the free edition's touch editor is view-only. Tabs take priority
  over file name and logo (both shrink); filtered row numbers blue. The strip
  button is a hamburger at the far right of the status bar; on phones sheet
  tabs and zoom are removed (sheets via ONLYOFFICE's sheet list); the editor
  frame fills the window edge to edge for a native-app look. The owner asked
  to remove About; it stays because it is the only place the licence notices
  appear (additional term 3), but it now always closes (✕, Esc, hamburger). Details and
  exact values: `integrations/onlyoffice/README.md`.
- **Private sheet views by default:** every person works in their own view
  per sheet ("Private - <name>", reused), shown without the green sheet-view
  headers, so filters and sorting do not change what others see.
- **How:** ONLYOFFICE Community ignores layout options, so a patched copy of
  its WOPI start page (Apache-2.0) applies the layout in the editor frame,
  using only official API calls and theme tokens, pinned to the image by
  fingerprint.
- **Licence:** the logo stays (not linked); About keeps ONLYOFFICE's notices
  and states that this is a modified version based on ONLYOFFICE by Ascensio
  System SIA (additional terms 1 to 3).
- **Reliability:** the container removes a stale supervisord PID file before
  starting; otherwise a restart could leave ONLYOFFICE down (502).
- **Trade-offs:** Collabora-specific additions (P27 filter search fix, P34
  private sheet views, header theming) are retired; ONLYOFFICE's native sheet
  views and filter search replace them. Community
  Edition is AGPL v3; connection and mobile-editing limits are verified
  against the pinned version.
- **Production:** switched 18 November 2026 after the owner set the tablet
  check (P43) aside; mapped onto production's pre-repository Drive stack
  ([method](production-moves.md)).
- **Collabora retired (19 November 2026):** removed from production through
  Coolify's own delete (configuration archived in the P42 rollback folder) and
  from the repository (module, stack, tests, build tool, renderer branches);
  ONLYOFFICE is the renderer's only editor and its default.
- **Where:** P42, `integrations/onlyoffice/`, `integrations/drive/workspace.js`.


### TEST SITE marker in every app
- **Decision:** every app on the test site shows the same marker (orange
  striped 3px top line with a small TEST SITE tab, overlaying, top window
  only). Apps decide by hostname; the renderer enforces that test hostnames
  start with `test.` or `test-` and production ones never do.
- **Why:** the owner entered real rows on the test site by mistake (19
  November 2026); test data is overwritten at every refresh and never flows
  back to production, so the two sites must be told apart at a glance.
- **Where:** `session.js`, `place_holder.html`, Drive `workspace.js`, the
  ONLYOFFICE start page, the DMS adapter, the Mail overlay; `prepare_runtime.py`.

### Sign-in rebuilt from the repository with production's secret key (P44)
- **Decision:** after a loss, rebuild authentik from the repository
  `identity` stack and reuse production's `AUTHENTIK_SECRET_KEY` and database
  password, read from the backed-up Coolify compose; back up authentik's media
  volume and invitation templates too.
- **Why:** authentik derives users' sign-in identifiers from the secret key;
  a new key would make every app treat each user as new. Proven on the old
  VPS: same users, applications, providers and identifiers as production.
- **Where:** `tools/restore_identity.py`, `deployment/stacks/identity.compose.json`,
  [disaster recovery](disaster-recovery.md), P44.

### Backups: Restic to S3 storage on a home NAS, protected by ZFS snapshots
- **Decision:** nightly Restic backups of production (databases dumped
  online; Drive and Mail stopped for seconds and copied) to RustFS (S3) on the
  owner's TrueNAS, RAID10 pool, over the tailnet. Retention 7 daily, 4 weekly,
  6 monthly. Weekly restore drill on the test VM with a read-only key. Daily
  ZFS snapshots of the backup storage, kept 60 days.
- **Why:** off-server, encrypted and deduplicated, no cloud storage cost;
  Restic runs from a digest-pinned container so nothing is installed on the
  host; a drill that imports every dump proves restorability. ZFS snapshots
  protect the backups from a compromised production server, which has no
  TrueNAS login. TrueNAS's snapshot tasks refuse its internal app storage, so
  a TrueNAS cron job running as root (`integrations/backup/zfs-snapshot-guard.sh`)
  snapshots the RustFS dataset in place daily and removes only its own
  snapshots beyond 60; no data move or RustFS downtime needed.
- **Where:** `integrations/backup/`, [disaster recovery](disaster-recovery.md), P02, P40.

### Recovery essentials kept by the owner
- **Decision:** encryption password, TrueNAS admin, SSH keys and the
  provider/registrar/GitHub/Tailscale/Meta/authentik logins with recovery
  codes are kept outside the servers and reviewed quarterly.
- **Why:** everything else is reproducible from Git and the backups; these
  are the only things that are not. **Where:** [disaster recovery](disaster-recovery.md), `AGENTS.md`, P41.

### Full restore rehearsal on a spare machine
- **Decision:** restore production from backup onto the idle old VPS on
  private names, quarantined, and time it.
- **Why:** a database drill proves dumps import; only a full restore proves
  the business can be recovered and how long it takes. **Where:** P39.

### Portal deep links: app pages always open inside the portal
- **Decision:** Desk, Raven and Insights pages opened on their own (new tab,
  pasted link) reopen inside the portal at the same page: a server redirect
  for whole-tab requests (`Sec-Fetch-Dest: document`) plus a client-side
  check in `session.js`.
- **Why:** the left-edge app menu belongs to the portal frame. Raven's service
  worker fetches navigations itself without that header, so the server alone
  cannot tell; the page checks `window.top` instead. Frames and installed app
  windows are never redirected. **Where:** `portal/sso.py`, `public/session.js`, `www/place_holder.html`.

### Test site on a home server behind the production proxy
- **Decision:** the permanent test site runs in a VM on the owner's TrueNAS.
  Public test hostnames resolve to production, whose proxy terminates TLS for
  them (its wildcard certificate covers them) and forwards each request over
  HTTPS to the test VM through the tailnet, verifying the VM's certificate per
  hostname; the VM trusts the relay's X-Forwarded-For. HTTP/3 is off on both
  proxies. SSO for test is reached over the tailnet through a private entry
  point.
- **Why:** no extra hosting cost and no fixed public address needed at home.
  A plain TCP pass-through by SNI was tried first and failed in browsers:
  with a wildcard certificate on production, browsers reuse ("coalesce") an
  open production connection for any covered hostname, so test requests
  arrived inside connections opened for other names and production answered
  them itself (503). HTTP/3 (UDP) likewise reached production's own 503 page.
- **Where:** `tools/prepare_test_relay.py`, `tools/coolify_proxy_hosts.py`,
  `tools/coolify_proxy_http3.py`, `tools/prepare_auth_bridge.py`.

### Production ERP built from the repository (P37)
- **Decision:** production ERP runs the image built from a tested release on
  production itself, reusing the existing data volumes and keeping legacy
  network names as aliases; later updates recreate only app containers.
- **Why:** reproducible from Git, same code as validated on test, about two
  minutes of downtime, data untouched. **Where:** [method](production-moves.md).

### Short production pause for test refreshes
- **Decision:** the export copies files while production runs, then only the
  changes during a bounded pause; dumps are compressed after resuming.
- **Why:** the store grew and the old exporter exceeded its 100-second
  consistency limit; the pause is now about 45 seconds. **Where:** `tools/export_snapshot.py`.

### Test-only app access and safe contributions (P38)
- **Decision:** an app under test is blocked on production (unusable OAuth
  redirect URIs) and re-enabled on test after every refresh; the developer
  contributes by fork and pull request, only the owner merges, production
  changes only after test validation and owner confirmation.
- **Why:** forks keep write access with the owner; since the public release
  (P35) the main branch is also protected on GitHub. **Where:** `CONTRIBUTING.md`, P38.

### WhatsApp through frappe_whatsapp with signature checks
- **Decision:** use frappe_whatsapp (MIT) with Meta's Cloud API, wrapped to
  verify Meta's webhook signature (fail closed), with test copies limited to
  allowed recipient numbers.
- **Why:** the upstream webhook accepts unsigned posts; refreshed test data
  holds real contacts. **Where:** `erpnext_drive_integrations/whatsapp/`, P04.
