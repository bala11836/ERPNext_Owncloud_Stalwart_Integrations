# Test site: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 21 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# Test site: P items

The permanent test site: refresh, branch deploys and the demo.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P33 — Move the permanent test site to a TrueNAS VM and retire the old VPS

**App:** test-site · **Also touches:** none · **State:** done

**Status:** done. Test site on TrueNAS since 17 November 2026; old VPS wiped and
its access revoked on 19 November (migration step 9 (private record));
owner: subscription left to lapse (treated as cancelled) and both tailnet
nodes removed (19 November).

Rebuild the test site from Git on an Ubuntu VM with its own Coolify on the home TrueNAS. Reach it publicly through a TLS-passthrough relay on the production VPS over the tailnet (home is behind CGNAT). Re-point the exporter, auth bridge and egress source-IP restrictions to the VM's tailnet address. Run full acceptance, including a button-triggered four-app refresh. Then revoke the old VPS's keys and cancel that VPS (rollback archives are discarded). Must run from a workstation on the tailnet. Full plan: test-host-migration.md (private record).

### P51 — Data refresh runs at 8 pm, not on demand

**App:** test-site · **Also touches:** none · **State:** open

**Status:** open, owner request 19 November 2026; work on it later, after the
crippled refresh (PR #3 of the public repository) is merged and in use.
Scrambling the production copy is resource intensive, so pressing "Refresh
data" must not start it at once. Instead the request is queued and starts at
**8 pm** (Asia/Kolkata), and the refresh page shows a line saying so, for
example "Data refresh scheduled for 8 pm today". Owner clarification, same
day: the allowed window is **8 pm to 8 am the next morning**. A request made
before 8 pm is scheduled for 8 pm; a request made inside the window may run
at once. My assumptions to confirm when we build it: only "Refresh data" is
scheduled ("Refresh code" stays immediate); a request made between 8 am and
8 pm waits for 8 pm; a run starts only if it is expected to **finish
by 8 am** (owner, same day): the expected duration comes from the previous
successful data refreshes plus a safety margin (a generous default until one
has run), so a request made late at night, too late to finish, waits for the
next 8 pm instead of running into working hours; repeated
presses merge into one queued run; the page shows who requested it, when it
will run, and its progress; a queued request can be cancelled before it
starts. **Code refresh (owner question, same day):** its duration is not
measured (the ERP image rebuild is the slow part; the container swap took
about two minutes on production). Build the scheduling rule once as a setting
per button: on for "Refresh data", off at first for "Refresh code"; measure
real code refreshes and switch it on if they prove heavy (for example over 15
minutes), with the 8 am finish estimate taken from that button's own history.
Never apply it to the colleague's own branch deploys, which must stay
immediate. Where: `test-refresh` module (worker and refresh page).

### P54 — Branch deploy button for the "developer" group on the test site

**App:** test-site · **Also touches:** none · **State:** blocked

**Status:** open, owner decision 20 November 2026. **Blocked until the first crippled refresh passes its audit** (exporter deployed on production 20 November, residual items listed in the release log). The authentik group
"developer" exists (flat, no bindings, one member: the colleague) and is meant
to be allowed to deploy branches to the test site without asking the owner.
The deploy mechanism does not exist yet (PR #3 only adds "Refresh code", which
resets test to `main`). To build in `test-refresh`: a test-site page where a
member of "developer" picks a branch of the public repository or a pull
request, the repository checks run, and the branch is built and deployed to
test, showing who deployed which revision and when; "Refresh code" puts `main`
back. Safeguards to include: only members of the group may use it (checked on
the server, not just hidden in the page); test runs crippled data only (PR #3)
and its outbound-integration guard stays; deploy only from the public
repository; no production credentials on the test host; every deploy logged.
Accepted risk (owner): deploying runs the branch's code on the test VM.
Needs: PR #3 merged and the first crippled refresh done first.

### P63 — Demo mode for the test site (`test.example.com`): neutral brand, no tenant traces

**App:** test-site · **Also touches:** portal, signin · **State:** in progress

**Status:** open, owner request 21 November 2026; not started. No earlier P item covered
this; related: P47 (landing page), P55 (brand mechanism), P51 and P54 (crippled refresh),
P35 (public sharing). The owner wants `test.example.com` usable as a **demo**. Its data is
already crippled (names and identities of non-kept users removed, 60 days only); now every
trace of the tenant goes too.

**Scope**
1. **Remove the tenant everywhere on the test site:** the name <tenant> and the company logo
   from the landing page, portal (eZone), sign-in pages, favicons (ERP, portal, authentik, webmail,
   Drive, push icons), page titles, browser tab and link-preview text, ERP records that carry
   the company name (Company, addresses, letterheads, print and email templates, system and
   website settings), Drive spaces and DMS items where the name appears. The refresh must
   re-apply this after every data refresh (extend the crippling step), and a check must fail
   if the tenant name appears anywhere in the refreshed copy.
2. **Dummy logo:** big letters **UN** in the first row and **format** in small letters in the
   second row, scaled to exactly the width of the first row (as with "EMPLOYEE ZONE" on the
   landing page). **Propose several colour combinations** as mock-ups for the owner to choose
   from (for example dark blue with orange, graphite with teal, deep green with amber, plum
   with coral, black with a single accent). Used for every favicon and the whole site, replacing
   the <tenant> logo; a compact favicon variant for 16 to 48 px.
3. **Demo landing page with line art:** drawn in the style of the owner's sample (black outline
   drawing with a few flat colour accents on a light grey background; sample kept in the
   private assets as `assets/demo-landing/sample-flower-bee-owner-sketch.webp`: a flower with
   orange centre, green stem and leaves, and a small bee). Our own vector artwork, redrawn
   (rights: owner's own sketch and our own drawing), and drawn stroke by stroke like the
   production landing page; keep the "Employee Zone" entry and the typed line.
4. **Mechanism:** tenant branding already lives in the private runtime profile (`company_logo`,
   `company_favicon_dir`, website title and name, landing assets, P55), so the demo brand is
   a second set of private assets selected by the test profile; production keeps its own. The
   public repository stays tenant-neutral; the UN/format logo and demo art may be published
   as the neutral default.

**Open questions for planning:** (a) test and production **share one authentik**, and its brand
is chosen by the request's host name (`sso`), so the sign-in page cannot show the demo logo for test
only without a separate sign-in host name for the demo (or accepting the shared page); (b) who may
see the demo (the Testers group, or public with sample accounts) and whether the TEST SITE
marker stays; (c) demo user accounts and passwords stay out of Git; (d) outbound
mail and integrations stay quarantined as today.

**Progress (21 November 2026): demo logo live on the test site.** Owner chose option **A, navy and orange**
(`#1F3A5F` UN, `#E8731A` format) from five combinations (A navy/orange, B graphite/teal, C green/amber, D
plum/coral, E black/blue; mock-ups and files in the private assets `assets/unformat-demo-brand/`). Logo: "UN" in
heavy type, "format" below stretched to exactly the width of "UN" (SVG `textLength`, so it holds in any font);
favicon: rounded navy tile, white "UN", orange bar. Installed through the test profile (`company_logo`,
`company_favicon_dir`, `website_title`/`website_name` = Unformat; rollback copy of the profile in
`<server path>`). Verified byte for byte: ERP logo and favicons, landing page logo and
favicon; the landing page title is "Unformat" and no longer contains the tenant name. **Still showing the tenant:** the
portal heading (the ERP Company record "<tenant company>", business data in the test copy: rename
or mask it in the refresh's crippling step, not by hand), the sign-in page (shared authentik brand, see open question a),
and anything inside the data (letterheads, print formats, mail). **Not yet:** the line-art landing page, re-applying
all of this after every data refresh, publishing the neutral brand as the repository default. Lesson for P67: the test
deploy skips the ERP image build when an image of the same commit exists, so a brand-only change needed the image tag
removed first; browsers may also keep the old files because the version stamp is the commit.


### P65 — Relayed test sign-in loses the requested page (X-Forwarded-Uri dropped)

**App:** test-site · **Also touches:** signin, general · **State:** blocked

**Status:** owner decision needed (found 21 November 2026, mobile app on test). The test site reaches the sign-in
service through the production proxy's private (tailnet) entry point, which does not trust forwarded headers from the
test VM, so `X-Forwarded-Uri` is dropped and the sign-in gateway returns to `/` after the passkey. Since 20 November `/`
on the test host is the landing page (P47), so the first sign-in lands there; a second tap works because the gateway
session exists. Two weeks earlier the test host had its own public address and `/` was the portal, so nobody saw it.
**Options:** trust forwarded headers on that entry point for the bridge sources only (production proxy setting,
low exposure: tailnet-only entry point, fixed sources); or accept the second tap. A change of the post-sign-in
default page would not help (it changes where you land, not the lost request). Test first where possible; a
production-only setting gets a browser and protocol check right after promotion.

### P66 — Errors on the test site are invisible: Error Log rows stay queued

**App:** test-site · **Also touches:** general, erp · **State:** open

**Status:** open (found 21 November 2026). Frappe writes Error Log rows by a deferred insert that the scheduler
flushes; the business scheduler is deliberately off on the test copy, so every error stays in the Redis cache queue
(`insert_queue_for_Error Log`, 39 records on 21 November) and the Error Log list looks empty. Diagnosis needed reading
the queue by hand. **Fix:** flush the deferred inserts on test on a short timer (only that job, not the business
scheduler), or a small read tool; plus an alarm on new error records (with P61's alarms). Check whether production
flushes them (its scheduler runs).
