/* Cloud Mail picker bridge for ownCloud Web 12.5.0. No token leaves Files. */
(()=>{'use strict';
 const MAIL='https://mail.example.com';
 const params=new URLSearchParams(location.search);
 const pendingKey='office-mail-picker.pending';
 const supplied=params.get('office-mail-picker');
 if(supplied&&/^[a-f0-9-]{36}$/.test(supplied))sessionStorage.setItem(pendingKey,JSON.stringify({nonce:supplied,at:Date.now()}));
 let pending;
 try{pending=JSON.parse(sessionStorage.getItem(pendingKey)||'null');}catch{return;}
 if(!pending||Date.now()-pending.at>10*60*1000||!window.opener)return;
 const nonce=pending.nonce;
 let busy=false;
 const reply=(name,data={},transfer=[])=>window.opener.postMessage({name,nonce,...data},MAIL,transfer);
 const token=async()=>{
  const r=await fetch('/config.json',{credentials:'same-origin'});if(!r.ok)throw Error('Files configuration is unavailable.');
  const c=await r.json();const authority=c.openIdConnect.authority;const client=c.openIdConnect.client_id;
  const key='oc_oAuth.user:'+authority+':'+client;
  for(const storage of [sessionStorage,localStorage]){
   let user;try{user=JSON.parse(storage.getItem(key)||'null');}catch{continue;}
   if(user?.access_token&&user.expires_at>Date.now()/1000+5)return user.access_token;
  }
  throw Error('Your Files session needs refreshing. Sign in to Files and select the file again.');
 };
 window.addEventListener('message',async(event)=>{
  if(event.origin!==location.origin||event.source!==window||busy)return;
  if(event.data?.name==='owncloud-embed:cancel'){reply('office-picker:cancel');return;}
  if(event.data?.name!=='owncloud-embed:file-pick')return;
  const resource=event.data.data?.resource;
  if(!resource||resource.isFolder||typeof resource.webDavPath!=='string')return;
  busy=true;
  try{
   if(Number(resource.size)>25*1024*1024)throw Error('Choose a file smaller than 25 MB.');
   const path=resource.webDavPath;
   if(path.includes('://')||path.split('/').some(s=>decodeURIComponent(s)==='..'))throw Error('Invalid Files path.');
   const encoded=path.split('/').map(s=>encodeURIComponent(decodeURIComponent(s))).join('/');
   const url=new URL(encoded.startsWith('/dav/')?encoded:'/dav/'+encoded.replace(/^\//,''),location.origin);
   if(url.origin!==location.origin||!url.pathname.startsWith('/dav/'))throw Error('Invalid Files origin.');
   const response=await fetch(url,{headers:{Authorization:'Bearer '+await token()},credentials:'omit'});
   if(!response.ok)throw Error('Files could not download this document ('+response.status+').');
   const length=Number(response.headers.get('Content-Length'));
   if(length>25*1024*1024)throw Error('Choose a file smaller than 25 MB.');
   const bytes=await response.arrayBuffer();if(bytes.byteLength>25*1024*1024)throw Error('Choose a file smaller than 25 MB.');
   reply('office-picker:file',{bytes,filename:resource.name,contentType:resource.mimeType||response.headers.get('Content-Type')||'application/octet-stream'},[bytes]);
   sessionStorage.removeItem(pendingKey);
  }catch(error){reply('office-picker:error',{error:error instanceof Error?error.message:'Files attachment failed.'});busy=false;}
 });
})();
