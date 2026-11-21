#!/usr/bin/env python3
"""Repair a workbook whose saved sheet views make the ONLYOFFICE editor crash.

ONLYOFFICE 10.0.0 (build 169) can save a sheet view with a column filter that has no
filter inside, ``<columnFilter colId="5" id="{...}"></columnFilter>``. Opening the file
then fails with ``Cannot read properties of null (reading 'IU')`` and the grid stays
blank. This tool removes only those empty column filters (optionally also the empty
"Temporary View N" shells) from ``xl/namedSheetViews/*.xml`` and leaves every other part
of the file byte for byte unchanged. Views, their names and real filters are kept.

    python3 sheetview_sanitize.py IN.xlsx OUT.xlsx [--temporary] [--drop-all-views]

It never overwrites its input. Exit status 0 when OUT was written (also when nothing
needed repair), 2 for a file it cannot read. ``inspect`` mode only reports.
"""
import argparse
import hashlib
import re
import sys
import zipfile
from xml.dom import minidom

VIEW_PARTS = "xl/namedSheetViews/"
COLUMN_FILTER = re.compile(r"<columnFilter\b[^>]*?(?:/>|>(.*?)</columnFilter>)", re.S)
TEMPORARY = re.compile(r'<namedSheetView name="Temporary View \d+" id="\{[^}]*\}"\s*(?:/>|></namedSheetView>)')
REL_VIEW = re.compile(r"<Relationship [^>]*namedSheetView[^>]*?/>")
CT_VIEW = re.compile(r"<Override [^>]*namedSheetView[^>]*?/>")


def empty_column_filters(xml):
    """Count column filters that hold no <filter> (the shape that crashes the editor)."""
    return sum(1 for m in COLUMN_FILTER.finditer(xml) if "<filter" not in (m.group(1) or ""))


def strip_empty_column_filters(xml):
    def keep(match):
        return match.group(0) if "<filter" in (match.group(1) or "") else ""
    return COLUMN_FILTER.sub(keep, xml)


def inspect(path):
    report = {"parts": {}, "empty_column_filters": 0, "temporary_views": 0}
    with zipfile.ZipFile(path) as z:
        for name in sorted(n for n in z.namelist() if n.startswith(VIEW_PARTS)):
            xml = z.read(name).decode("utf8", "replace")
            empties = empty_column_filters(xml)
            temps = len(TEMPORARY.findall(xml))
            report["parts"][name] = {"empty_column_filters": empties, "temporary_views": temps,
                                      "views": re.findall(r'<namedSheetView name="([^"]*)"', xml)}
            report["empty_column_filters"] += empties
            report["temporary_views"] += temps
    return report


def sanitize(src, dst, temporary=False, drop_all_views=False):
    changed = []
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
        for info in zin.infolist():
            name, data = info.filename, zin.read(info.filename)
            if drop_all_views and name.startswith(VIEW_PARTS):
                changed.append(name)
                continue
            if name.startswith(VIEW_PARTS) and name.endswith(".xml"):
                text = data.decode("utf8")
                new = strip_empty_column_filters(text)
                if temporary:
                    new = TEMPORARY.sub("", new)
                if new != text:
                    minidom.parseString(new.encode("utf8"))  # still well-formed
                    data = new.encode("utf8")
                    changed.append(name)
            elif drop_all_views and (name == "[Content_Types].xml" or (name.startswith("xl/worksheets/_rels/") and name.endswith(".rels"))):
                text = data.decode("utf8")
                new = (CT_VIEW if name == "[Content_Types].xml" else REL_VIEW).sub("", text)
                if new != text:
                    minidom.parseString(new.encode("utf8"))
                    data = new.encode("utf8")
                    changed.append(name)
            copy = zipfile.ZipInfo(name, info.date_time)
            copy.compress_type, copy.external_attr, copy.create_system = info.compress_type, info.external_attr, info.create_system
            zout.writestr(copy, data)
    # every part that was not meant to change must be byte-identical
    with zipfile.ZipFile(src) as a, zipfile.ZipFile(dst) as b:
        assert b.testzip() is None
        kept = [n for n in b.namelist() if n not in changed]
        for n in kept:
            assert hashlib.sha256(a.read(n)).digest() == hashlib.sha256(b.read(n)).digest(), n
    return changed


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("source")
    p.add_argument("target", nargs="?")
    p.add_argument("--temporary", action="store_true", help="also remove empty 'Temporary View N' shells")
    p.add_argument("--drop-all-views", action="store_true", help="remove every sheet view (last resort)")
    args = p.parse_args(argv)
    try:
        report = inspect(args.source)
    except (zipfile.BadZipFile, OSError) as error:
        print("cannot read workbook:", error, file=sys.stderr)
        return 2
    print("empty column filters:", report["empty_column_filters"], "| empty Temporary View shells:", report["temporary_views"])
    if not args.target:
        return 0
    changed = sanitize(args.source, args.target, args.temporary, args.drop_all_views)
    print("written", args.target, "| parts changed:", len(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
