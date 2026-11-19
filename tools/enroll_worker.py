#!/usr/bin/env python3
"""Enroll revocable, owner-scoped TEST/production document worker credentials.

All credentials stay on the deployment host. Users must already exist in Drive
(normally through their first SSO sign-in). DMS permissions remain owner-aware.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import urllib.request


def enroll(profile):
    if profile['tier'] not in {'test','production'}:raise ValueError('Unknown deployment tier')
    dms_code=Path(profile['source'])/'integrations/dms/bootstrap.py'
    code=dms_code.read_text()+"\nimport json,sys;print('PRIVATE_ENROLLMENT='+json.dumps(configure(json.load(sys.stdin))))"
    process=subprocess.run(['docker','exec','-i',profile['dms_container'],'python','manage.py','shell','-c',code],
        input=json.dumps(profile),text=True,capture_output=True)
    if process.returncode or 'PRIVATE_ENROLLMENT=' not in process.stdout:
        raise RuntimeError('DMS enrollment failed; inspect the native service privately')
    rows=json.loads(process.stdout.split('PRIVATE_ENROLLMENT=',1)[1].strip())
    for user in rows:
        response=subprocess.run(['docker','exec',profile['drive_container'],'ocis','auth-app','create',
            '--user-name='+user['email'],'--expiration=720h'],capture_output=True,text=True)
        if response.returncode:raise RuntimeError('Drive user is not ready for enrollment')
        token=response.stdout.strip().split()[-1]
        authorization=base64.b64encode((user['email']+':'+token).encode()).decode()
        request=urllib.request.Request(profile['files_url'].rstrip('/')+'/graph/v1.0/me',
            headers={'Authorization':'Basic '+authorization})
        with urllib.request.urlopen(request,timeout=30) as answer:identity=json.load(answer)
        if identity.get('mail','').casefold()!=user['email']:
            raise RuntimeError('Drive token identity does not match the enrolled owner')
        user.update(files_token=token,files_user_id=identity['id'])
    config={key:profile[key] for key in ['files_url','paperless_url','paperless_public_url','office_space_id','office_processor']}
    config.update(users=rows,max_bytes=profile.get('max_bytes',41943040))
    destination=Path(profile['worker_config'])
    if not destination.parent.is_dir():raise ValueError('Prepare worker runtime before enrollment')
    temporary=destination.with_name(destination.name+'.pending')
    temporary.write_text(json.dumps(config,indent=2)+'\n');temporary.chmod(0o600);os.chown(temporary,10001,10001)
    os.replace(temporary,destination)
    return {'enrolled_users':len(rows),'credentials_displayed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--profile',required=True)
    print(enroll(json.loads(Path(parser.parse_args().profile).read_text())))
