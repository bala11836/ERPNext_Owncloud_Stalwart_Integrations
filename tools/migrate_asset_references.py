#!/usr/bin/env python3
"""Rewrite retired addon asset prefixes in system settings, never business text.

Run in the site's bench environment. Supply old prefixes privately through JSON;
dry-run is the default. Matching data/config rollback must already exist.
"""
import argparse
import json
import frappe


def migrate(mapping, apply=False):
    if not mapping or any(not a.startswith("/assets/") or not b.startswith("/assets/") for a, b in mapping.items()):
        raise ValueError("Only explicit asset-path prefix mappings are allowed")
    changes = []
    rows = frappe.db.sql(
        "select doctype, field, value from tabSingles where doctype in %s",
        (("Website Settings", "Navbar Settings", "Portal Settings"),), as_dict=True)
    for row in rows:
        value = row.value or ""
        replacement = value
        for before, after in mapping.items():
            replacement = replacement.replace(before, after)
        if replacement == value:
            continue
        changes.append({"doctype": row.doctype, "field": row.field})
        if apply:
            frappe.db.sql("update tabSingles set value=%s where doctype=%s and field=%s",
                          (replacement, row.doctype, row.field))
    if apply:
        frappe.db.commit()
        frappe.clear_cache()
    return changes


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True)
    parser.add_argument("--sites-path", default=".")
    parser.add_argument("--mapping-json", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    frappe.init(site=args.site, sites_path=args.sites_path)
    frappe.connect()
    try:
        print(json.dumps({"applied": args.apply, "changes": migrate(json.loads(args.mapping_json), args.apply)}))
    finally:
        frappe.destroy()
