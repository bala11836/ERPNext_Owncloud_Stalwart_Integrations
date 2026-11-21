# Editor: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 21 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# Editor: P items

ONLYOFFICE Docs: the document and spreadsheet editor behind Drive, private sheet views, file safety.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

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
