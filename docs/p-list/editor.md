# Editor: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 21 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# Editor: P items

ONLYOFFICE Docs: the document and spreadsheet editor behind Drive, private sheet views, file safety.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P27 — Collabora Calc search-based AutoFilter

**App:** editor · **Also touches:** none · **State:** closed

**Status:** closed 19 November 2026, obsolete: Collabora was replaced by
ONLYOFFICE (P42) and retired; its overlays were removed from the repository.
ONLYOFFICE's own filter search is used. Earlier: fix committed 16 November
2026 (editor overlay `integrations/collabora/autofilter-search.js`, served
inside `cloud-ui.js`). Production reports
Collabora 26.04.6.1. No Collabora image or core change.

Root cause, confirmed in the pinned image's browser bundle: the AutoFilter
search box only hides list rows in the browser (`filterEntries` adds a
`hidden` class). The search text is never sent to the document, so with "All"
ticked Search → OK applies nothing, and ticking "All" during a search sends a
toggle for every value. Individual row ticks send correct row numbers in this
build.

Fix (owner-approved Excel behavior): with search text and at least one match,
OK (or Enter in the search box) clears all ticks through the "All" control,
ticks exactly the visible matches, then sends OK, so only matching rows show,
replacing earlier ticks. "All" during a search ticks or unticks only the
visible matches. Without search text, or with no matches, native behavior is
unchanged. It applies to spreadsheet AutoFilters in any format (.xlsx, .ods,
.xls, .csv); text documents have no AutoFilter. Simulated-editor check:
`tests/browser/autofilter-search.check.js` (7 scenarios pass). Remove the
overlay once the upstream issue is fixed in the pinned build. Not addressed:
the reported missing search box on some columns (decided by the core). Date
tree filters (`check_tree_box`) keep native behavior.

Acceptance on permanent test: Search → OK and Enter with All ticked and with
earlier ticks; Search → All; no-search OK; no-match OK; already-filtered
column; a long list (hundreds of values); the result after save/reopen through
Drive and the portal; inside a P34 sheet view; and no change in Writer and
Impress. Promote the exact tested revision only after these pass.

Searching narrows displayed values, but Search → OK leaves unrelated rows
visible. Related upstream issue: https://github.com/CollaboraOnline/online/issues/16276
(read 16 November 2026). A referenced patch improved client filtering/row indices;
comments still report Search → OK failing on 26.04.5.1. This does not establish
that a newer build fixes the installed version's behavior.

Workarounds: clear All before searching, explicitly tick the required matching
values, then OK; alternatively use Standard Filter with Contains/Begins with.
Do not assume All applies only to the currently searched results.

Reproduce using a synthetic XLSX on permanent test, record image/build and
compare the stock editor with custom JS/CSS excluded. Test unfiltered and
already-filtered columns, multiple matches, manual selection/reset and
save/reopen through direct Drive and the portal. Inspect selection/dialog events
if needed. Evaluate a newer pinned upstream build or narrow source fix only on
test; promote the exact tested revision after regression acceptance. CSS cannot
repair filter selection/submission logic. Submit a sanitized upstream reproduction
if the issue persists; do not upload business spreadsheets.

### P34 — Automatic private sheet views in Collabora Calc

**App:** editor · **Also touches:** none · **State:** closed

**Status:** closed 19 November 2026, superseded: automatic private sheet
views now come from the ONLYOFFICE start page (P42,
`integrations/onlyoffice/`), live in production. Earlier Collabora
implementation (`integrations/collabora/private-sheet-views.js`) removed with
Collabora. Production reports Collabora
26.04.6.1, which includes Calc Sheet View.

Problem: with several users in one workbook, AutoFilter and sort are shared;
one user's filter replaces everyone else's. Collabora's Sheet View gives each
user an independent filter/sort/hidden-row view, but entering one is manual.

Agreed behavior:
- When a user opens a spreadsheet tab, put them in their own sheet view
  automatically (`.uno:NewSheetView`), on **every tab** they open.
- Before creating one, reuse the user's own existing view for that file and
  tab if it still exists (`.uno:SelectSheetView` with its ID). Create a new view
  only when none is recorded or the recorded view no longer exists.
- Ownership is recorded per **signed-in editor user** (the WOPI identity passed
  by Drive), file and tab, never per browser alone: computers and browsers are
  shared. Read the current user at each open; never reuse another user's view.
- View names stay Collabora's automatic names ("Temporary view N"); there is no
  rename command and a core patch is not wanted. Show a small label such as
  "Private view: <login>" so users know which view they are in.
- The user may leave with Collabora's Exit sheet view
  (`.uno:ExitSheetView`). Do not re-enter automatically for the rest of that
  visit; the next open returns them to their own view.
- First implementation keeps the ownership record in the editor origin's
  browser storage, keyed by user ID, file ID and tab. Store only IDs and view
  names, never document content; remove a user's entries on editor sign-out if
  the editor exposes it. A server-side record (follows the user across devices,
  nothing left in shared browsers) is a later option if extra views from new
  devices become a nuisance.

Known limits to tell users:
- Private means personal, not secret: views do not restrict data access, and
  other users can select someone else's view. Access control remains Drive
  file permissions.
- People sharing one login share one view; each person needs their own login.
- A new device or cleared browser data creates one more view for that user.
- Users outside a sheet view (after Exit, or in desktop/mobile apps) still
  share the default filter.

Implementation: a new editor overlay script next to
`integrations/collabora/header-ui.js`, added by `tools/prepare_editor.py`
(cool.html and its mount list). No Collabora image or core change. Confirm
from the pinned image's browser bundle how the client reports document type,
current part/tab, current user ID, sheet-view state and the list of existing
views; the public CollaboraOnline GitHub mirror did not contain the browser
source when checked. Command definitions verified in LibreOffice core
`sc/sdi/scalc.sdi` (NewSheetView, RemoveSheetView, SelectSheetView with
SheetViewID, ExitSheetView).

As implemented (client model confirmed in the pinned image's `bundle.js`):
- Each sheet view is a hidden part in the document status JSON with
  `sheetviewid >= 0` and `defaultviewhash` equal to the source tab's `hash`.
  The overlay reacts to the client's `docloaded`/`updateparts`/
  `updatepermission` events and reads `app.map._docLayer`.
- Current user: `app.map._viewInfo[viewId].userid` (WOPI `UserId` from Drive)
  and `username` for the label. File: last path segment of the WOPI source.
  Tab: one-way hash of the tab name, so tab names are not stored in clear;
  renaming a tab therefore starts a new view for it.
- On a normal tab in edit mode: reuse the recorded view only if a view with the
  same ID **and** name still exists for that tab (`.uno:SelectSheetView`,
  `SheetViewID`), else `.uno:NewSheetView` and record the view the client lands
  in. One attempt per tab per visit, with a 4-second limit; no retry loop.
- Any sheet-view command the user issues (Exit, choosing another view or the
  default view, New, Remove) is detected at the client socket and respected
  for that tab until the next open. Read-only sessions and Writer/Impress are
  left alone. Records unused for about six months are dropped.
- There is no editor sign-out event in the pinned client, so entries are not
  removed at sign-out; they hold only IDs and view names.
- Built into `cloud-sheet-views.js` by `tools/prepare_editor.py` and mounted
  read-only (`editor_collabora_6`). Existing editor build directories must be
  regenerated with `prepare_editor.py` before rerendering, or the new mount
  source is missing.

Validate on permanent test with at least two users (including two users on
one shared browser, one after the other) on the same .xlsx and .ods workbook:
independent filters and sorts on every tab; reuse of the user's own view on
reopen and reload; no cross-user reuse; Exit and next-open behavior; label
shows the current user; save/reopen through Drive and the portal; whether
sheet views are written into saved .xlsx/.ods files and whether views
accumulate; desktop/mobile and Writer/Impress unaffected; P27 AutoFilter search
behavior inside a sheet view. Promote the exact tested revision only after
these pass.

### P42 — Replace Collabora with ONLYOFFICE

**App:** editor · **Also touches:** drive · **State:** done

**Status:** done. **Production switched 18 November 2026, 19:00 UTC** (release `a135fd4`,
production releases (private record)); owner browser check on
production done (owner, 19 November). Collabora retired on 19 November from
production and the repository.
P39 part 1 (data restore) passed before the switch; part 2 remains.
Layout and private sheet views agreed and approved by the owner on test on
18 November 2026 (release line, details in `integrations/onlyoffice/README.md`).
Next: mobile check, then steps (2) to (4). Decided by the owner on 18 November 2026
(see [decisions](../decisions.md)). Sequence: (1) replace Collabora with ONLYOFFICE
on the test site completely, with automated saving (periodic save to Drive,
forced save, watcher for documents left open) and theming; validate with the
the shared register workbook (open time, co-editing, saves reaching Drive while open, abrupt
close), (2) back up, (3) P39 full restore onto the old VPS using the
ONLYOFFICE stack, (4) switch production.

### P61 — Editor file safety: a document is never left unusable or its edits lost

**App:** editor · **Also touches:** drive · **State:** in progress

**Status:** open, owner request 21 November 2026 ("account for all scenarios that
happened and might happen and make sure that a file is never left in this position");
**priority: highest (production business data).** Not started. Incident record:
21 November shared-workbook incident (private record).

**What happened (evidence, UTC, 20 November):** `<shared register workbook>` (Drive
space Acts) worked until about 16:00 IST. 10:46:54 last good save of the old copy. At
11:03:55 ONLYOFFICE's save to Drive (WOPI PutFile) returned HTTP 500 (the cause is
unknown: the Drive and collaboration logs of that hour were erased when those
containers were recreated at 12:17 for the P56 release) and the unsaved edits were parked as
"forgotten". From 11:07 the editor failed to apply stored edits (`changesError: Cannot
read properties of null`), again at 11:35, 11:57 to 12:00 and 12:54 to 13:15. The file
was deleted and re-uploaded at 11:05:59 and again at 11:33:53 (each upload made DMS link
files), saves worked 11:06 to 12:56, and nothing was saved after 12:56:45, so the owner's
manual deletion of views never persisted and the views "came back". The 40 empty
"Temporary View" entries are old (present in the first saved version of 18 November
09:39, before ONLYOFFICE went live, so Collabora-era leftovers) and did not grow in the
ONLYOFFICE period; they are not the cause. A second parked file (a different small
workbook, 3 sheets) holds edits that never reached Drive: copy in
`<rollback folder>` on production, owner to say whose it is.

**Scenarios (seen = happened to us) and the safeguard for each**

| # | Scenario | Seen | Safeguard |
|---|---|---|---|
| 1 | Save to Drive fails (PutFile 500, proof keys, WOPI lock conflict, oCIS busy), edits parked in "forgotten" | yes | alarm within minutes on `PutFile error` / `storeForgotten`; **rescue job** copies every forgotten file to a recovery folder and tells the owner; root cause logged |
| 2 | Editor cannot apply stored edits (`changesError` null reference), file cannot be opened or edited | yes | `editor_unstick` tool: force save, rescue forgotten, drop the stuck document key through ONLYOFFICE's command service (JWT), reopen check; runbook for people |
| 3 | Edits made but never saved, so deletions "come back" | yes | save-health probe (below) and a visible "not saved" alert path; document the symptom |
| 4 | Diagnosis impossible because container logs vanish on recreate | yes | archive logs before any recreate (P59 promotion plan pre-step) and keep rotated logs on disk for 30 days |
| 5 | Users re-upload or delete the file as a workaround (duplicates, DMS link files, lost history) | yes | runbook "file will not open: do not delete"; versions are restored from Drive's version list; rescue tool covers the rest |
| 6 | Planned or unplanned restart of ONLYOFFICE, the editor bridge, Drive or the host with people editing | yes (reboot 20 Nov) | pre-restart **force save** of every open document; P57 post-boot check also opens and saves a probe document; Stalwart/editor bridge checks already in P57 |
| 7 | Silent breakage of saving after a release, certificate, proof-key or network change | partly | **synthetic save probe** (headless browser opens a probe workbook through Drive, edits, saves, checks that a new version appears) after every promotion and every 15 minutes; failure pages the owner |
| 8 | Private sheet views multiply in a shared workbook (old automation could loop) | no evidence on this file; reproduced in simulation | PR #12 (one attempt per person and sheet), plus a cap: never create when a sheet already has many views; one-off cleaner for legacy "Temporary View" shells (done by hand for the shared workbook) |
| 9 | Disk or cache full on the ONLYOFFICE or Drive volumes (document cache was 255 MB and is never pruned) | no | disk and cache alert at 80 percent, scheduled cache prune of closed documents |
| 10 | File corruption, bad macro or manual edit, huge file slowness | no | Drive keeps every save as a version (27 in two hours here) and the nightly backup covers Drive; restore drill already passes (P39); runbook for restoring one file |
| 11 | Two editors with different page versions (browser cached the old start page) | possible | versioned start-page URL and a restart of the editor with every promotion (P59 plan step) |
| 13 | Stored sheet views the editor cannot read (empty filters in a Private view): blank grid, `changesError` null reference, file cannot be used | yes (the shared workbook, 20-21 Nov) | sanitiser that strips unreadable view data (part of the unstick tool and run before each file is opened by the automation); decide with the owner whether the private-view automation stays on, is limited, or is paused until the cause is proven; test on the test site with two users and filters |
| 12 | Changes to sheet-view or sheet structure by one person break the other person's open session | suspected (null reference on views) | after the legacy views are cleaned, repeat the two-person test on test; keep the editor start page minimal |

**Build order (each item is a normal branch, test, merge, production):** (a) the
unstick-and-rescue tool and runbook; (b) log archiving before recreation (with P59);
(c) alarms on the editor and Drive logs plus the forgotten-file rescue job (systemd
timer, like the P57 host checks); (d) the synthetic save probe; (e) pre-restart force
save; (f) cache and disk alerts; (g) PR #12 and the view cap. Related: P57, P59, P42.
**Honest limit:** nothing guarantees that a save never fails; the aim is that a failure
is seen within minutes, no edit is lost, and a stuck file is recoverable without deleting
it.
