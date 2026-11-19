#!/usr/bin/env python3
"""Build the prepared public ERP core with the pinned official apps_json input.

The app list is a BuildKit file mount, not an APPS_JSON_BASE64 argument. Force
the builder stage to consume it rather than reuse a build without the mount.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def build(context,tag):
    context=Path(context).resolve()
    if not re.fullmatch(r'[a-z0-9./_-]+:[A-Za-z0-9_.-]+',tag):raise ValueError('Use an explicit image tag')
    lock=json.loads((context/'source-lock.json').read_text())
    for name,entry in lock['apps'].items():
        actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=context/'app-sources'/name,text=True).strip()
        if actual!=entry['commit']:raise ValueError('Prepared source changed: '+name)
    cache_key=hashlib.sha256((context/'apps.json').read_bytes()+
        json.dumps(lock,sort_keys=True).encode()).hexdigest()
    subprocess.run(['docker','build','--build-arg','CACHE_BUST='+cache_key,
        '--no-cache-filter','builder','--secret','id=apps_json,src='+str(context/'apps.json'),
        '-t',tag,str(context)],check=True)
    # A successfully built image with only Frappe is not a valid nine-app core.
    code="from pathlib import Path;import json;expected="+repr(sorted(lock['apps']))+";root=Path('/home/frappe/frappe-bench/apps');missing=[name for name in expected if not (root/name/name).is_dir()];assert not missing,missing;print(json.dumps({'public_app_sources':len(expected),'all_present':True}))"
    subprocess.run(['docker','run','--rm','--network','none','--entrypoint',
        '/home/frappe/frappe-bench/env/bin/python',tag,'-c',code],check=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--context',required=True);p.add_argument('--tag',required=True)
    a=p.parse_args();build(a.context,a.tag)
