#!/usr/bin/env python3
"""Activate and verify native test Drive office registration after cold restore."""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import time
import urllib.request
from urllib.parse import urlsplit

from test_refresh_worker import private_profile


def verify(config):
    profile=json.loads(Path(config['runtime_profile']).read_text())
    if config['tier']!='test' or profile['tier']!='test':raise ValueError('Test only')
    enrollment=json.loads(Path(config['worker_enrollment_profile']).read_text())
    worker=json.loads(Path(enrollment['worker_config']).read_text())
    if urlsplit(worker['files_url']).hostname!=profile['hosts']['drive']:raise ValueError('Foreign Drive URL')
    # A running collaboration process can outlive the app registry's restart.
    # Register after the restored Drive is healthy, not concurrently with it.
    subprocess.run(['docker','restart',config['containers']['drive_collaboration']],check=True,stdout=subprocess.DEVNULL)
    user=worker['users'][0]
    authorization='Basic '+base64.b64encode((user['email']+':'+user['files_token']).encode()).decode()
    for attempt in range(60):
        try:
            request=urllib.request.Request(worker['files_url'].rstrip('/')+'/app/list',headers={'Authorization':authorization})
            with urllib.request.urlopen(request,timeout=10) as response:rows=json.load(response)['mime-types']
            extensions={row['ext'] for row in rows if row.get('allow_creation') is True}
            icons=[urlsplit(p['icon']).hostname for row in rows for p in row.get('app_providers',[]) if p.get('icon')]
            if {'docx','xlsx','pptx'}<=extensions and not {'odt','ods','odp'}&extensions:
                if not icons or any(host!=profile['hosts']['office'] for host in icons):
                    raise ValueError('Editor registration has a non-test origin')
                return {'registered':True,'microsoft_creation':True,'odf_creation':False,'editor_origin_verified':True}
        except OSError:
            if attempt==59:raise
        time.sleep(1)
    raise RuntimeError('Native test editor registration did not become ready')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True)
    print(json.dumps(verify(private_profile(p.parse_args().config))))
