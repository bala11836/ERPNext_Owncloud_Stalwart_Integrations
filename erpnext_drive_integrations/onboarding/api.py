"""Mobile app API (ADR-037). Every method runs as the signed-in user, so ERPNext's own permission
checks decide what is returned; nothing here grants access.

`bootstrap` gives the app what the web desk gets at login: who you are, your roles, and the same
role-filtered left-hand menus (`frappe.boot.get_module_sidebars`).
"""
import frappe


def menus_from_sidebars(sidebars):
    """Keep what the app can open (DocType lists), grouped under their section headings.

    Menus with nothing openable are dropped, as are headings with no links under them.
    """
    menus = []
    for entry in sidebars.values():
        items, section = [], None
        for item in entry.get("items") or []:
            if item.get("type") == "Section Break":
                section = {"type": "section", "label": item.get("label") or ""}
            elif item.get("type") == "Link" and item.get("link_type") == "DocType" and item.get("link_to"):
                if section:
                    items.append(section)
                    section = None
                # ponytail: sidebar link filters (e.g. "Draft invoices") are not applied yet; the app opens
                # the whole list the user may read. Add when a menu relies on them.
                items.append({"type": "doctype", "label": item.get("label") or item["link_to"], "doctype": item["link_to"]})
        if any(i["type"] == "doctype" for i in items):
            menus.append({"name": entry.get("name"), "label": entry.get("label") or entry.get("name"),
                          "app": entry.get("app"), "items": items})
    return sorted(menus, key=lambda m: m["label"].lower())


@frappe.whitelist(methods=["GET"])
def bootstrap():
    from frappe.boot import get_module_sidebars

    from erpnext_drive_integrations.onboarding.access import RoleReach, filtered_sidebars, own_roles

    user = frappe.session.user
    sidebars = get_module_sidebars()
    if user != "Administrator":
        # Same rule as the web Desktop: only menus the user's own roles connect to (access.py).
        sidebars = filtered_sidebars(sidebars, RoleReach(own_roles(user)))
    return {
        "user": {"email": user, "full_name": frappe.utils.get_fullname(user)},
        "roles": frappe.get_roles(user),
        "menus": menus_from_sidebars(sidebars),
    }
