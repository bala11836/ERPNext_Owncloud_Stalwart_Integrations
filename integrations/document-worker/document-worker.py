"""Poll enrolled users' writable Files drives; ingest documents with owner-bound tokens.

No Files deletes or original-file writes. State and retries survive container restarts.
"""
import base64,hashlib,json,logging,mimetypes,os,pathlib,re,sqlite3,time,uuid,datetime,fcntl
import urllib.request,urllib.parse,urllib.error,xml.etree.ElementTree as ET
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
os.umask(0o077)
STATE=pathlib.Path(os.environ.get('STATE_DIR','/state'));STATE.mkdir(parents=True,exist_ok=True);STATE.chmod(0o700)
DB=sqlite3.connect(STATE/'jobs.sqlite3');DB.row_factory=sqlite3.Row
os.chmod(STATE/'jobs.sqlite3',0o600)
DB.execute('CREATE TABLE IF NOT EXISTS jobs (key TEXT PRIMARY KEY, payload TEXT NOT NULL)');DB.commit()
EXT={'.pdf','.png','.jpg','.jpeg','.tif','.tiff','.webp','.bmp','.gif','.txt','.csv','.md','.doc','.docx','.xls','.xlsx','.ppt','.pptx','.odt','.ods','.odp','.rtf','.eml'}
N={'d':'DAV:','o':'http://owncloud.org/ns'}
PROPS=b'''<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:o="http://owncloud.org/ns"><d:prop><d:resourcetype/><d:getetag/><d:getcontentlength/><o:fileid/><o:id/></d:prop></d:propfind>'''
def raw(method,url,auth,data=None,headers=None,limit=45088768):
 h={'Authorization':auth,**(headers or {})};req=urllib.request.Request(url,method=method,data=data,headers=h)
 try:
  with urllib.request.urlopen(req,timeout=90) as r:
   body=r.read(limit+1)
   if len(body)>limit:raise ValueError('Response exceeds size limit')
   return body
 except urllib.error.HTTPError:raise
def js(method,url,auth,body=None):
 data=raw(method,url,auth,json.dumps(body).encode() if body is not None else None,{'Content-Type':'application/json'})
 return json.loads(data) if data else None
def save(key,p):
 DB.execute('INSERT OR REPLACE INTO jobs VALUES (?,?)',(key,json.dumps(p)));DB.commit()
def load(key):
 r=DB.execute('SELECT payload FROM jobs WHERE key=?',(key,)).fetchone();return json.loads(r[0]) if r else {}
def multipart(fields,filename,content):
 boundary='office'+uuid.uuid4().hex;out=[]
 for name,value in fields.items():
  out.extend([('--'+boundary+'\r\nContent-Disposition: form-data; name="'+name+'"\r\n\r\n'+str(value)+'\r\n').encode()])
 safe=filename.replace('"','_').replace('\r','').replace('\n','')
 out.extend([('--'+boundary+'\r\nContent-Disposition: form-data; name="document"; filename="'+safe+'"\r\nContent-Type: '+(mimetypes.guess_type(filename)[0] or 'application/octet-stream')+'\r\n\r\n').encode(),content,('\r\n--'+boundary+'--\r\n').encode()])
 return b''.join(out),{'Content-Type':'multipart/form-data; boundary='+boundary}
def walk(base,auth,maxbytes,depth=0):
 if depth>20:raise ValueError('Folder nesting exceeds 20 levels')
 tree=ET.fromstring(raw('PROPFIND',base,auth,PROPS,{'Depth':'1','Content-Type':'application/xml'}))
 seen=set()
 for response in tree.findall('d:response',N):
  href=response.findtext('d:href',namespaces=N)
  url=urllib.parse.urljoin(base,href or '')
  if urllib.parse.urlsplit(url).netloc!=urllib.parse.urlsplit(base).netloc:raise ValueError('Foreign DAV origin')
  if urllib.parse.unquote(url).rstrip('/')==urllib.parse.unquote(base).rstrip('/'):continue
  props=None
  for ps in response.findall('d:propstat',N):
   if '200' in (ps.findtext('d:status',namespaces=N) or ''):props=ps.find('d:prop',N);break
  if props is None:continue
  name=urllib.parse.unquote(urllib.parse.urlsplit(url).path.rstrip('/').split('/')[-1])
  if name.startswith('.office-') or name=='DMS Links':continue
  if props.find('d:resourcetype/d:collection',N) is not None:
   yield from walk(url.rstrip('/')+'/',auth,maxbytes,depth+1);continue
  if pathlib.Path(name).suffix.lower() not in EXT:continue
  size=int(props.findtext('d:getcontentlength',default='0',namespaces=N))
  if size==0 or size>maxbytes:continue
  fid=props.findtext('o:fileid',namespaces=N) or props.findtext('o:id',namespaces=N)
  if not fid:raise ValueError('Missing stable Files resource ID')
  if fid in seen:continue
  seen.add(fid)
  yield {'url':url,'name':name,'etag':props.findtext('d:getetag',default='',namespaces=N),'fid':fid,'size':size}
def apiurl(c,path):return c['paperless_url'].rstrip('/')+'/api/'+path.lstrip('/')
def files_credential(c,u):
 """Renew this user's same-scope 30-day app credential five days before expiry."""
 directory=STATE/'credentials';directory.mkdir(exist_ok=True);directory.chmod(0o700)
 key=hashlib.sha256(u['email'].encode()).hexdigest();path=directory/(key+'.json')
 def timestamp(value):return datetime.datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
 def authorization(secret):return 'Basic '+base64.b64encode((u['email']+':'+secret).encode()).decode()
 def persist(value):
  tmp=directory/(key+'.'+uuid.uuid4().hex+'.tmp');tmp.write_text(json.dumps(value));tmp.chmod(0o600);tmp.replace(path)
 with (directory/(key+'.lock')).open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  manager=c['files_url'].rstrip('/')+'/auth-app/tokens'
  if path.exists():saved=json.loads(path.read_text())
  else:
   entries=js('GET',manager,authorization(u['files_token']))
   # A new CLI enrollment has exactly one app credential. Never revoke an ambiguous token.
   entry=entries[0] if len(entries)==1 else None
   saved={'files_token':u['files_token'],'expires_at':timestamp(entry['expiration_date']) if entry else time.time()+25*86400,'token_hash':entry['token'] if entry else None}
   persist(saved)
  if saved['expires_at']-time.time()<5*86400 or os.environ.get('ROTATE_FILES_TOKENS_NOW')=='1':
   old=saved;auth=authorization(old['files_token'])
   created=js('POST',manager+'?'+urllib.parse.urlencode({'expiry':'720h','label':'Office document processor'}),auth)
   newauth=authorization(created['token'])
   me=js('GET',c['files_url'].rstrip('/')+'/graph/v1.0/me',newauth)
   if me['id']!=u['files_user_id']:raise ValueError('Renewed Files identity mismatch')
   entries=js('GET',manager,newauth)
   match=next((t for t in entries if t['label']=='Office document processor' and t['created_date']==created['created_date']),None)
   saved={'files_token':created['token'],'expires_at':timestamp(created['expiration_date']),'token_hash':match['token'] if match else None}
   persist(saved)  # Persist and validate the replacement before revoking the old token.
   if old.get('token_hash') and old['token_hash'].startswith('$2') and old['token_hash']!=saved['token_hash']:
    try:js('DELETE',manager+'?'+urllib.parse.urlencode({'token':old['token_hash']}),newauth)
    except Exception:logging.warning('Previous worker app token could not be revoked; it will expire')
   logging.info('Renewed Files worker credential; validity remains 30 days')
  u['_files_expiry']=saved['expires_at'];return saved['files_token']
def permissions(u,shared):
 groups=[u['office_group_id']] if shared else []
 return {'view':{'users':[],'groups':groups},'change':{'users':[],'groups':groups}}
def gettag(c,u,auth,shared):
 label='ownCloud Office' if shared else 'ownCloud Personal'
 items=js('GET',apiurl(c,'tags/?name__iexact='+urllib.parse.quote(label)),auth)['results']
 found=next((t for t in items if t['name']==label and t.get('owner')==u['paperless_user_id']),None)
 if found:return found['id']
 return js('POST',apiurl(c,'tags/'),auth,{'name':label,'color':'#254c76','matching_algorithm':0,'owner':u['paperless_user_id'],'set_permissions':permissions(u,shared)})['id']
def finish(c,u,fa,pa,key,p,docid):
 docid=p.get('document_id') or docid
 doc=js('GET',apiurl(c,f'documents/{docid}/'),pa)
 if doc.get('owner')!=u['paperless_user_id']:raise ValueError('Refusing cross-owner duplicate')
 shared=p['shared'];expected=[u['office_group_id']] if shared else []
 # A duplicate must not cause an existing personal document to become shared.
 if p.get('duplicate'):
  full=js('GET',apiurl(c,f'documents/{docid}/?full_perms=true'),pa)
  actual=sorted((full.get('permissions') or {}).get('view',{}).get('groups',[]))
  if actual!=expected:raise ValueError('Duplicate has different sharing scope; manual review required')
 tags=sorted(set(doc.get('tags',[])+[p['tag']]))
 js('PATCH',apiurl(c,f'documents/{docid}/'),pa,{'tags':tags,'set_permissions':permissions(u,shared)})
 source=c['files_url'].rstrip('/')+'/f/'+urllib.parse.quote(p['file']['fid'],safe='$!')
 link=c['paperless_public_url'].rstrip('/')+f'/documents/{docid}/details'
 # A private source link is metadata, not a public sharing link.
 try:
  notes=js('GET',apiurl(c,f'documents/{docid}/notes/'),pa)
  noteitems=notes.get('results',[]) if isinstance(notes,dict) else notes
  if not any(source in n.get('note','') for n in noteitems):js('POST',apiurl(c,f'documents/{docid}/notes/'),pa,{'note':'ownCloud source: '+source})
 except urllib.error.HTTPError as e:
  if e.code!=403:raise
  logging.info('Source note omitted: enrolled owner has no note permission')
 try:js('PUT',c['files_url'].rstrip('/')+'/graph/v1.0/extensions/org.libregraph/tags',fa,{'resourceId':p['file']['fid'],'tags':['paperless','dms-'+str(docid)]})
 except urllib.error.HTTPError as e:
  if e.code!=400:raise
  # A repeat assignment reports 400 when the tag already exists.
  if 'no new tags' not in e.read().decode():raise
 parent=p['file']['url'].rsplit('/',1)[0]+'/DMS%20Links/'
 try:raw('MKCOL',parent,fa)
 except urllib.error.HTTPError as e:
  if e.code!=405:raise
 short=hashlib.sha256(p['file']['fid'].encode()).hexdigest()[:10]
 filename=urllib.parse.quote(pathlib.Path(p['file']['name']).stem[:90]+'-'+short+'.url',safe='')
 raw('PUT',parent+filename,fa,('[InternetShortcut]\r\nURL='+link+'\r\n').encode(),{'Content-Type':'application/internet-shortcut'})
 p.update(status='done',document_id=int(docid),task=None,error=None,attempts=0,next_attempt=0,finished=time.time(),paperless_link=link)
 save(key,p);logging.info('processed scope=%s document=%s', 'office' if shared else 'personal',docid)
def pending(c,u,fa,pa,key,p):
 tasks=js('GET',apiurl(c,'tasks/?task_id='+urllib.parse.quote(p['task'])),pa)
 if isinstance(tasks,dict):tasks=tasks.get('results',[])
 if not tasks:return
 t=tasks[0];status=str(t.get('status','')).upper()
 if status in ['PENDING','STARTED','RETRY']:return
 result=t.get('result_data') or {}
 docid=t.get('related_document') or result.get('document_id') or next(iter(t.get('related_document_ids') or []),None)
 if status=='SUCCESS' and docid:
  if 'duplicate' in json.dumps(result).lower() or 'duplicate' in str(t.get('result','')).lower():p['duplicate']=True
  finish(c,u,fa,pa,key,p,docid);return
 p['task']=None
 raise RuntimeError('Paperless task '+str(status)+': '+str(result.get('error_message') or t.get('result',''))[:350])
def cycle(c):
 errors=0;seen=0
 for u in c['users']:
  current=files_credential(c,u)
  fa='Basic '+base64.b64encode((u['email']+':'+current).encode()).decode();pa='Token '+u['paperless_token']
  drives=js('GET',c['files_url'].rstrip('/')+'/graph/v1.0/me/drives',fa)['value']
  for d in drives:
   if d['driveType'] not in ['personal','project']:continue
   shared=d['id']==c['office_space_id']
   if shared and u['email']!=c.get('office_processor',c['users'][0]['email']):continue
   if d['driveType']=='project' and not shared:continue
   # Personal documents are polled only through that owner's enrollment.
   if d['driveType']=='personal' and d.get('owner',{}).get('user',{}).get('id')!=u.get('files_user_id'):continue
   for f in walk(d['root']['webDavUrl'].rstrip('/')+'/',fa,c['max_bytes']):
    seen+=1;key=u['email']+'|'+d['id']+'|'+f['fid'];p=load(key)
    try:
     if p.get('status')=='pending':pending(c,u,fa,pa,key,p);continue
     if p.get('status')=='done' and p.get('file',{}).get('etag')==f['etag']:continue
     if p.get('status')!='done' and p.get('next_attempt',0)>time.time():continue
     content=raw('GET',f['url'],fa,limit=c['max_bytes']);checksum=hashlib.sha256(content).hexdigest()
     if p.get('status')=='done' and p.get('sha256')==checksum:p['file']=f;save(key,p);continue
     previous=p.get('document_id');p.update(file=f,shared=shared,sha256=checksum,tag=gettag(c,u,pa,shared),duplicate=False)
     if not previous:
      # Reuse only within the same owner and sharing scope. Other scopes get
      # independent native Paperless documents, without widening an old copy.
      reused=False
      for other in DB.execute("SELECT key,payload FROM jobs WHERE json_extract(payload,'$.sha256')=? AND json_extract(payload,'$.status')='done'",(checksum,)).fetchall():
       if not other['key'].startswith(u['email']+'|'):continue
       candidate=json.loads(other['payload'])
       if candidate.get('shared')!=shared or not candidate.get('document_id'):continue
       p['duplicate']=True;finish(c,u,fa,pa,key,p,candidate['document_id']);reused=True;break
      if reused:continue
     fields={'title':pathlib.Path(f['name']).stem,'tags':p['tag']}
     endpoint=f'documents/{previous}/update_version/' if previous else 'documents/post_document/'
     body,headers=multipart(fields,f['name'],content)
     task=json.loads(raw('POST',apiurl(c,endpoint),pa,body,headers))
     p.update(task=task,status='pending',next_attempt=0);save(key,p)
     logging.info('queued scope=%s bytes=%s', 'office' if shared else 'personal',f['size'])
    except Exception as e:
     errors+=1;p['attempts']=p.get('attempts',0)+1;p['next_attempt']=time.time()+min(3600,60*2**min(p['attempts'],6));p['error']=str(e)[:500]
     if p.get('task'):p['status']='pending'
     else:p['status']='error'
     save(key,p);logging.error('job failed: %s endpoint=%s',str(e)[:220],getattr(e,'url','').split('?')[0])
 (STATE/'health.json').write_text(json.dumps({'last_cycle':time.time(),'files_seen':seen,'errors':errors,'enrolled_users':len(c['users']),'earliest_files_credential_expiry':min(u['_files_expiry'] for u in c['users'])}))
if __name__=='__main__':
 while True:
  try:
   config=json.loads(pathlib.Path(os.environ.get('CONFIG_FILE','/run/secrets/document-worker.json')).read_text());cycle(config)
  except Exception:logging.exception('poll cycle failed')
  if os.environ.get('RUN_ONCE')=='1':break
  time.sleep(config.get('poll_seconds',60) if 'config' in locals() else 60)
