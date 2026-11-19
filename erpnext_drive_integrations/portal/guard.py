"""Refuse Frappe's deprecated `cmd=` RPC on every path (deep audit AUTH-01, 2026-11-11).

Frappe 16 runs `?cmd=<guest method>` on ANY path before it looks at the path, so `/login?cmd=...` reached
guest methods without passing Authentik. Desk JS never sends `cmd` (frappe.request deletes it and calls
/api/method/...), so refusing it everywhere costs nothing. Runs first in before_request.
"""
import frappe
from frappe import _


def refuse_rpc_cmd():
    if "cmd" in (frappe.form_dict or {}):
        frappe.throw(_("Not found"), frappe.PageDoesNotExistError)
