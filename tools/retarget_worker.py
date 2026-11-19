"""Retarget only worker-generated links after a TEST data refresh.

Original documents, user-written links and document/Space ACLs are untouched.
Do not call the normal worker's finish(): that would reapply sharing permissions.
"""
import base64
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
from urllib.parse import quote,urlsplit,urlunsplit
import urllib.request
import urllib.error


def retarget(profile):
    if profile.get('tier')!='test':raise ValueError('Link retargeting is test-only')
    config=json.loads(Path(profile['worker_config']).read_text())
    files=config['files_url'].rstrip('/');dms=config['paperless_public_url'].rstrip('/')
    old_files=set(profile['source_files_origins']);old_dms=set(profile['source_dms_origins'])
    if files in old_files or dms in old_dms:raise ValueError('Test and source origins must differ')
    users={user['email']:user for user in config['users']}
    database=Path(profile['worker_state'])/'jobs.sqlite3'
    if not database.exists():return {'generated_links_retargeted':0,'notes_retargeted':0}
    notes={};changed=0;skipped=0;missing=0
    def url(value,origins,target):
        parsed=urlsplit(value);origin=parsed.scheme+'://'+parsed.netloc
        return target+urlunsplit(('', '',parsed.path,parsed.query,parsed.fragment)) if origin in origins else value
    with sqlite3.connect(database) as db:
        for key,raw in db.execute('SELECT key,payload FROM jobs').fetchall():
            row=json.loads(raw);file=row.get('file',{});owner=key.split('|',1)[0]
            previous=row.get('paperless_link')
            if file.get('url'):file['url']=url(file['url'],old_files,files)
            if row.get('status')=='done' and previous and row.get('document_id') and owner in users:
                target=url(previous,old_dms,dms)
                if not target.startswith(dms+'/documents/') or not file.get('url','').startswith(files+'/'):
                    raise ValueError('Unexpected generated job URL')
                short=hashlib.sha256(file['fid'].encode()).hexdigest()[:10]
                name=quote(Path(file['name']).stem[:90]+'-'+short+'.url',safe='')
                shortcut=file['url'].rsplit('/',1)[0]+'/DMS%20Links/'+name
                user=users[owner];authorization='Basic '+base64.b64encode((owner+':'+user['files_token']).encode()).decode()
                expected=('[InternetShortcut]\r\nURL='+previous+'\r\n').encode()
                replacement=('[InternetShortcut]\r\nURL='+target+'\r\n').encode()
                try:
                    with urllib.request.urlopen(urllib.request.Request(shortcut,headers={'Authorization':authorization}),timeout=30) as response:
                        existing=response.read(16385)
                except urllib.error.HTTPError as error:
                    if error.code!=404:raise
                    # Users may delete generated shortcuts or move the original
                    # after processing. Preserve that choice; never recreate it.
                    existing=None;missing+=1
                if existing==expected:
                    request=urllib.request.Request(shortcut,data=replacement,method='PUT',
                        headers={'Authorization':authorization,'Content-Type':'application/internet-shortcut'})
                    with urllib.request.urlopen(request,timeout=30):pass
                    changed+=1
                elif existing is not None and existing!=replacement:skipped+=1
                row['paperless_link']=target
                for origin in old_files:notes['ownCloud source: '+origin+'/f/'+file['fid']]='ownCloud source: '+files+'/f/'+file['fid']
            elif row.get('status')=='pending':
                row.update(status='error',task=None,error=None,next_attempt=0)
            db.execute('UPDATE jobs SET payload=? WHERE key=?',(json.dumps(row),key))
    code="import json,sys;from documents.models import Note;mapping=json.load(sys.stdin);print(sum(Note.objects.filter(note=old).update(note=new) for old,new in mapping.items()))"
    result=subprocess.run(['docker','exec','-i',profile['dms_container'],'python','manage.py','shell','-c',code],
        input=json.dumps(notes),text=True,capture_output=True)
    if result.returncode:raise RuntimeError('Generated source-note retargeting failed')
    return {'generated_links_retargeted':changed,'user_modified_links_preserved':skipped,
            'absent_generated_links_preserved':missing,
            'notes_retargeted':int(result.stdout.strip().splitlines()[-1])}
