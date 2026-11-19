"""Data-preserving metadata consolidation; invoked only with a private audited plan.

Never calls uninstall_app or drops a business table. Back up database/files/config
and stop workers/scheduler before invoking from the site's bench console.
"""
import json
from pathlib import Path
import frappe

APP = "erpnext_drive_integrations"


def consolidate(plan_path, apply=False):
    plan = json.loads(Path(plan_path).read_text())
    old_apps = plan["source_apps"]
    installed = frappe.get_installed_apps()
    if APP in installed and not any(a in installed for a in old_apps):
        return {"status": "already consolidated", "apps": installed}
    if len(old_apps) != 3 or not all(a in installed for a in old_apps):
        raise ValueError("Source app membership differs from the audited plan")
    modules = frappe.get_all("Module Def", filters={"app_name": ["in", old_apps]}, fields=["name", "app_name"])
    expected = plan["module_names"]
    if {m.name for m in modules} != set(expected):
        raise ValueError("Module inventory differs from the audited plan")
    doctypes = frappe.get_all("DocType", filters={"module": ["in", list(expected)]}, pluck="name")
    counts = {dt: frappe.db.count(dt) for dt in doctypes if not frappe.get_meta(dt).issingle and not frappe.get_meta(dt).is_virtual}
    result = {"source_apps": old_apps, "modules": modules, "record_counts": counts}
    if not apply:
        return result
    for old, new in expected.items():
        if old != new:
            if frappe.db.exists("Module Def", new):
                raise ValueError("Destination module already exists: " + new)
            # Native Module Def permits rename only while marked custom. Change
            # metadata within this transaction, use native link rewriting, then
            # restore its standard status; no DocType/table is uninstalled.
            was_custom = frappe.db.get_value("Module Def", old, "custom")
            frappe.db.set_value("Module Def", old, "custom", 1, update_modified=False)
            frappe.rename_doc("Module Def", old, new, force=True)
            frappe.db.set_value("Module Def", new, "custom", was_custom, update_modified=False)
        frappe.db.set_value("Module Def", new, "app_name", APP, update_modified=False)
    replacement = []
    for name in installed:
        if name in old_apps:
            if APP not in replacement:
                replacement.append(APP)
        else:
            replacement.append(name)
    frappe.db.set_global("installed_apps", json.dumps(replacement))
    frappe.clear_cache()
    for dt, before in counts.items():
        if frappe.db.count(dt) != before:
            raise RuntimeError("Record count changed for " + dt)
    # Caller commits only after writing the receipt and validating ownership.
    result.update(status="metadata updated", apps=replacement)
    return result
