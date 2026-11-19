#!/usr/bin/env python3
"""Read-only native-bench asset manifest/hook check; run inside the ERP image.

Usage: python verify_erp_assets.py SITE
Reports public asset names only, never site configuration or user records.
"""
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit


def verify(site):
    os.chdir('/home/frappe/frappe-bench/sites')
    import frappe
    frappe.init(site);frappe.connect()
    try:
        root=Path.cwd();assets=root/'assets';mapping={};missing=[]
        for name in ['assets.json','assets-rtl.json']:
            file=assets/name
            if file.exists():mapping.update(json.loads(file.read_text()))
        for key,value in mapping.items():
            if isinstance(value,str) and value.startswith('/assets/') and not (root/urlsplit(value).path.lstrip('/')).is_file():
                missing.append(value)
        hooks=[]
        for name in ['app_include_js','app_include_css','web_include_js','web_include_css']:
            values=frappe.get_hooks(name) or []
            for value in values:
                if not isinstance(value,str):continue
                if '.bundle.' in value and value not in mapping and not value.startswith('/assets/'):
                    missing.append('Unresolved bundle: '+value);continue
                target=mapping.get(value,value)
                if target.startswith('/assets/'):
                    hooks.append(target)
                    if not (root/urlsplit(target).path.lstrip('/')).is_file():missing.append(target)
        result={'manifest_entries':len(mapping),'hook_assets':len(hooks),'missing':sorted(set(missing))}
        if missing:raise RuntimeError(json.dumps(result))
        return result
    finally:frappe.destroy()


if __name__=='__main__':print(json.dumps(verify(sys.argv[1])))
