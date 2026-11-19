# ONLYOFFICE editor customisation (`onlyoffice-editor`)

Space-saving layout and private sheet views for ONLYOFFICE Docs opened from
Drive through WOPI.

## Purpose

P42: ONLYOFFICE replaces Collabora. In WOPI mode the editor's layout is set by
ONLYOFFICE's WOPI start page (`editor-wopi.ejs`); ONLYOFFICE Community ignores
the official layout options, so our copy of that page applies the layout the
owner agreed on 18 November 2026 (goal: maximum working space).

## Agreed layout (final, owner approved 18 November 2026)

Editor (this module, `editor-wopi.ejs`):
- **One header row:** compact header; Drive's ✕ and ⋮ at the left, then the
  tabs, the file name, and ONLYOFFICE's logo at the far right. The tabs get
  the space first: the file name and the logo shrink (the logo down to its
  icon) before the tabs scroll; the tab scroll arrows are 28 px wide. Avatar, header search, Share and open-file-location are removed (the
  co-editor count appears only while others are in the file).
- **Logo:** kept, as the licence requires, but not linked to the vendor site.
- **Always the light theme** (also on devices in dark mode), so the agreed
  greys, icons and headers look the same everywhere.
- **Tabs start after Drive's ✕ and ⋮** (84 px), which sit at the top left.
- **One side strip, on the right, header grey (#D9D9D9), opened from a
  hamburger (≡) at the far right of the status bar** (after zoom +, like the
  sheet list), on desktop and phones. It takes no width while closed, opens
  over the sheet, and closes with the button or a click on the sheet; it
  stays while one of its settings panels is open. The hamburger is pinned to
  the bottom-right corner above the strip, and one tap closes an open
  settings panel together with the strip. It holds:
  first the contextual settings buttons (cell, shape, image, text, slicer,
  pivot field list: the pivot list and object settings exist only here),
  then the former left strip (search, comments, chat, spell check, about).
  Their panels still open on the left; the empty left column collapses while
  no panel is open. Tried and replaced: always visible, auto-hide on hover,
  an edge handle on phones. Phones use the desktop editor because
  ONLYOFFICE's touch editor is view-only in the free edition (verified on
  10.0.0.1).
- **Headers:** row and column headers #D9D9D9, hover #C6C6C6, selected row
  or column #A6A6A6, text #262626; numbers of filtered rows blue (#1F5BC6). The row-number column width is drawn by
  ONLYOFFICE's compiled engine and cannot be changed; white text on the
  selected header is impossible in sheet views (one text colour for all
  headers). Only ONLYOFFICE's official theme tokens are used.
- **Private sheet views:** every person automatically works in their own view
  per sheet ("Private - <name>"), reused on reopening, so filters and sorting
  do not change what others see; protected sheets are skipped; no green
  "Sheet View mode" headers.
- **Licence notice:** the About panel keeps ONLYOFFICE's notices and adds that
  this is a modified version based on ONLYOFFICE by Ascensio System SIA
  (additional terms 2 and 3). About is the only place these notices appear
  (File → Info is document information), so its strip button stays. About
  shows only when clicked, as a small card (340 px) beside the strip instead
  of a full-window page, with a ✕ close button; Esc or the side-menu
  hamburger also close it.
- **Side-menu hamburger:** four thin lines, matching ONLYOFFICE's sheet-list
  button.
- **Click relay:** a click in the editor tells Drive to close its open file
  menu (no data sent).

Drive (`integrations/drive/workspace.js`, while `/external-onlyoffice/` is open):
- Drive's top bar is hidden; its ⋮ (file menu) and ✕ (close) float in the
  editor's header row at the **top left** (easier to reach on phones):
  transparent, icons rgb(56,56,56), ✕ 24 px icon in a 32 px button at 10 px
  from the left edge, ⋮ 16 px at 46 px.
- **Phones (up to 768 px):** the status bar shows only add sheet (+),
  ONLYOFFICE's sheet list (≡) and our side-menu hamburger; sheet tabs, their
  scroll arrows, zoom and the save-status text are hidden.
- Drive's tooltips are hidden while editing (the ⋮ tooltip stayed on screen).
- Drive's file menu is styled like ONLYOFFICE's (Segoe UI 13 px, dark grey,
  single border, grey hover).
- The editor frame fills the whole window (fixed, edge to edge, no border or
  rounded corners) for a native-app look; Drive's details panel, when
  opened, stays beside it.

Saving: auto-assembly writes changes to Drive every 2 to 3 minutes while open
and within seconds of closing (`deployment/config/onlyoffice-local-production-linux.json`).

## Contents

- `integrations/onlyoffice/editor-wopi.ejs`: patched start page (mounted read-only)
- `integrations/onlyoffice/editor-wopi.original.ejs`: the unmodified page from the pinned image, for review and diff
- `deployment/stacks/editor-onlyoffice.compose.json`, `deployment/config/onlyoffice-local-production-linux.json`
- `tests/test_onlyoffice_editor.py`

## Requirements

ONLYOFFICE Docs pinned by digest (10.0.0.1); the patch is tied to that
version's start page (checked by fingerprint in the tests).

## Reuse

Select `editor_product: onlyoffice` in the runtime profile. On an ONLYOFFICE
upgrade, copy the new start page to `editor-wopi.original.ejs`, re-apply the
marked `cloud-integrations` changes and update the fingerprint in the test.

## Configuration

Auto-assembly (periodic save to Drive while open) and the WOPI IP filter are
in `deployment/config/onlyoffice-local-production-linux.json`.

## Tests

- `tests/test_onlyoffice_editor.py`

## Licenses

- ONLYOFFICE Docs: GNU AGPL v3 with additional terms (attribution, modified
  version notice, no trademark grant), https://github.com/ONLYOFFICE/DocumentServer;
  pinned image, its user interface adjusted at runtime by the start page
  above. The ONLYOFFICE name and logo stay visible; About states the
  modification.
- `editor-wopi.ejs`: Apache License 2.0, (c) Ascensio System SIA; modified
  here (changes marked `cloud-integrations`), notice kept.

Developed with AI assistance (Claude); the owner reviews and is responsible.

Test-site marker: on hostnames starting with `test.` or `test-` (enforced by the renderer) this module shows the shared TEST SITE marker, a 3px striped top line with a small tab, top window only, no layout space. Editor: in the start page, when the office host is opened directly.
