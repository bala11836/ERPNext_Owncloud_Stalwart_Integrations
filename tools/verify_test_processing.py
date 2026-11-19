#!/usr/bin/env python3
"""Create one synthetic personal PDF on test and verify Drive -> DMS processing.

No production endpoints, messages or business records are modified. The probe
remains in test for inspection and is removed by the next data refresh.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
import urllib.request
from urllib.parse import urlsplit
import uuid

from test_refresh_worker import private_profile


def pdf(text):
    stream=('BT /F1 18 Tf 50 780 Td ('+text+') Tj ET').encode()
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    data=b'%PDF-1.4\n';offsets=[0]
    for number,value in enumerate(objects,1):
        offsets.append(len(data));data+=str(number).encode()+b' 0 obj\n'+value+b'\nendobj\n'
    start=len(data);data+=b'xref\n0 6\n0000000000 65535 f \n'
    data+=b''.join(('%010d 00000 n \n'%position).encode() for position in offsets[1:])
    return data+b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(start).encode()+b'\n%%EOF\n'


def verify(path,timeout=240):
    config=private_profile(path)
    profile=json.loads(Path(config['runtime_profile']).read_text())
    enrollment=json.loads(Path(config['worker_enrollment_profile']).read_text())
    worker=json.loads(Path(enrollment['worker_config']).read_text())
    for key,host in [('files_url','drive'),('paperless_public_url','dms')]:
        url=urlsplit(worker[key])
        if url.scheme!='https' or url.hostname!=profile['hosts'][host]:
            raise ValueError('Probe must use only marked test endpoints')
    user=worker['users'][0]
    auth='Basic '+base64.b64encode((user['email']+':'+user['files_token']).encode()).decode()
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args):raise ValueError('Probe endpoint attempted a redirect')
    opener=urllib.request.build_opener(NoRedirect)
    def request(method,url,authorization,data=None):
        with opener.open(urllib.request.Request(url,data=data,method=method,
                headers={'Authorization':authorization,'Content-Type':'application/pdf' if data else 'application/json'}),timeout=30) as response:
            body=response.read()
            return body
    drives=json.loads(request('GET',worker['files_url']+'/graph/v1.0/me/drives',auth))['value']
    personal=next(row for row in drives if row['driveType']=='personal'
        and row.get('owner',{}).get('user',{}).get('id')==user['files_user_id'])
    root=personal['root']['webDavUrl'].rstrip('/')
    if urlsplit(root).hostname!=profile['hosts']['drive']:raise ValueError('Foreign DAV root')
    name='Repository-acceptance-'+uuid.uuid4().hex+'.pdf'
    request('PUT',root+'/'+name,auth,pdf(name[:-4]))
    job=None;deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        with sqlite3.connect(Path(enrollment['worker_state'])/'jobs.sqlite3') as db:
            for row in db.execute('SELECT payload FROM jobs'):
                value=json.loads(row[0])
                if value.get('file',{}).get('name')==name:job=value;break
        if job and job.get('status')=='done':break
        time.sleep(3)
    if not job or job.get('status')!='done':
        raise RuntimeError('Synthetic document did not finish within the test acceptance limit')
    if job.get('shared') or not job['paperless_link'].startswith(worker['paperless_public_url'].rstrip('/')+'/'):
        raise RuntimeError('Personal document sharing/link isolation mismatch')
    document=json.loads(request('GET',worker['paperless_public_url']+'/api/documents/'+str(job['document_id'])+'/',
        'Token '+user['paperless_token']))
    if document['owner']!=user['paperless_user_id']:raise RuntimeError('DMS owner mismatch')
    if name[:-4] not in document.get('content',''):raise RuntimeError('Synthetic PDF text was not extracted')
    code=('import json;from documents.models import Document;'
        'from guardian.shortcuts import get_users_with_perms,get_groups_with_perms;'
        'd=Document.objects.get(pk='+str(int(job['document_id']))+');'
        'print("PERMISSIONS="+json.dumps({"users":list(get_users_with_perms(d).values_list("id",flat=True)),'
        '"groups":list(get_groups_with_perms(d).values_list("id",flat=True))}))')
    native=subprocess.run(['docker','exec',config['containers']['dms'],'python','manage.py','shell','-c',code],
        capture_output=True,text=True,check=True)
    permissions=json.loads(native.stdout.split('PERMISSIONS=',1)[1].strip())
    if permissions['groups'] or set(permissions['users'])-{user['paperless_user_id']}:
        raise RuntimeError('Personal document was granted to another ordinary principal')
    result={'passed':True,'probe_file':name,'document_id':job['document_id'],
        'owner_verified':True,'personal_privacy_verified':True,'text_extracted':True,
        'test_link_verified':True,'completed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    receipt=Path(config['state_root'])/'processing-acceptance.private.json'
    receipt.write_text(json.dumps(result,indent=2)+'\n');receipt.chmod(0o600)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True)
    args=parser.parse_args();os.umask(0o077);print(json.dumps(verify(args.config)))
