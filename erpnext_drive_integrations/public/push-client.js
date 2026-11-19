/* Opt-in browser/PWA ERP alerts, using the native Frappe HR relay project. */
(()=>{
 if(window.self!==window.top||location.hostname!=='erp.example.com'||/^\/(api|assets|login)/.test(location.pathname)||window.cloudPush)return;
 // iOS may launch the installed app's start_url after a push tap. Recover only a
 // recent, single-use same-origin Mail/Calendar destination written by that tap.
 let readingClick=false;
 async function followNotificationClick(){
  if(readingClick||!('indexedDB'in window))return;readingClick=true;
  try{
   const pending=await new Promise(resolve=>{
    const request=indexedDB.open('cloud-notification-navigation',1);
    request.onupgradeneeded=()=>request.result.createObjectStore('pending');request.onerror=()=>resolve(null);
    request.onsuccess=()=>{
     const db=request.result,tx=db.transaction('pending','readwrite'),store=tx.objectStore('pending'),read=store.get('click');let value;
     read.onsuccess=()=>{value=read.result;store.delete('click');};
     tx.oncomplete=()=>{db.close();resolve(value);};tx.onerror=()=>{db.close();resolve(null);};
    };
   });
   if(pending?.expires>Date.now()){
    const target=new URL(pending.url,location.origin);
    if(target.origin===location.origin&&/^\/(mail|calendar)(\/|$)/.test(target.pathname)&&target.href!==location.href)location.assign(target.href);
   }
  }catch(_){}finally{readingClick=false;}
 }
 followNotificationClick();
 addEventListener('pageshow',followNotificationClick);
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')followNotificationClick();});
 const BASE='/api/method/erpnext_drive_integrations.portal.push.';
 let config,modules,messaging,registration,enabled=false,panel,csrf;
 const message=(text)=>{let p=document.querySelector('#uf-push-message');if(p)p.textContent=text;};
 async function request(method,args={},post=false){
  if(!csrf){let r=await fetch('/api/method/erpnext_drive_integrations.portal.hub.context',{credentials:'same-origin',cache:'no-store'});if(!r.ok)throw Error('Sign in again');csrf=(await r.json()).message.csrf;}
  const settings={credentials:'same-origin',cache:'no-store',headers:{}};
  if(post){settings.method='POST';settings.headers={'Content-Type':'application/json','X-Frappe-CSRF-Token':csrf};settings.body=JSON.stringify(args);}
  const r=await fetch(BASE+method,settings);if(!r.ok)throw Error('Request failed. Please sign in again or retry.');return (await r.json()).message;
 }
 function supported(){return isSecureContext&&'Notification'in window&&'serviceWorker'in navigator&&'PushManager'in window;}
 async function sdk(){
  if(!modules){const version=config.sdk_version; if(!/^\d+\.\d+\.\d+$/.test(version))throw Error('Invalid SDK version');
   const [app,push]=await Promise.all([import(`https://www.gstatic.com/firebasejs/${version}/firebase-app.js`),import(`https://www.gstatic.com/firebasejs/${version}/firebase-messaging.js`)]);
   modules={app,push};const name='cloud-erp-push';const instance=app.getApps().find(a=>a.name===name)||app.initializeApp(config.config,name);messaging=push.getMessaging(instance);
   push.onMessage(messaging, payload=>{if(!registration)return;const data=payload.data||{};registration.showNotification(data.title||'ERPNext',{body:data.body||'Open ERPNext to view your notification.',data:{url:data.click_action||'/desk'},tag:data.event_id?'uf-'+data.event_id:undefined});});
  }return modules;
 }
 async function waitForActivation(reg){
  if(reg.active)return;
  const worker=reg.installing||reg.waiting;if(!worker)throw Error('Push worker is unavailable');
  await new Promise((resolve,reject)=>{let timer=setTimeout(()=>reject(Error('Push worker timed out')),20000);const done=()=>{if(worker.state==='activated'){clearTimeout(timer);resolve();}else if(worker.state==='redundant'){clearTimeout(timer);reject(Error('Push worker failed'));}};worker.addEventListener('statechange',done);done();});
 }
 async function enable(){
  if(!supported()){message('Use a supported browser. On iPhone, open the installed ERPNext Home Screen app.');return;}
  // This call stays directly inside the user's click gesture (required by Safari).
  const permission=await Notification.requestPermission();
  if(permission!=='granted'){message('Notifications are blocked. Allow them in this browser/phone’s notification settings, then retry.');return;}
  try{
   message('Connecting this device…');config=await request('configuration');const {push}=await sdk();
   const url=BASE+'worker?v=20261106-push1&config='+encodeURIComponent(JSON.stringify(config.config));
   registration=await navigator.serviceWorker.register(url,{scope:'/cloud-push/',updateViaCache:'none'});await waitForActivation(registration);
   const token=await push.getToken(messaging,{vapidKey:config.vapid_public_key,serviceWorkerRegistration:registration});
   const result=await request('subscribe',{token},true);if(!result.success)throw Error(result.message);
   enabled=true;message('Enabled for this signed-in browser. Use Send test, then check your device.');
  }catch(e){message(e.message||'Could not enable notifications.');}
 }
 async function disable(){
  try{
   await request('unsubscribe',{},true);enabled=false;
   if(modules&&messaging)await modules.push.deleteToken(messaging).catch(()=>{});
   message('Disabled for this browser. Other devices are unchanged.');
  }catch(e){message(e.message||'Could not confirm disable. Retry while signed in.');}
 }
 function button(label,fn){const b=document.createElement('button');b.type='button';b.className='uf-header-button';b.textContent=label;b.onclick=fn;return b;}
 async function open(){
  panel?.remove();panel=document.createElement('section');panel.className='uf-hub-panel';panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Device push notifications');
  const title=document.createElement('h3');title.textContent='Device push notifications';const text=document.createElement('p');text.id='uf-push-message';text.textContent='Checking this browser…';
  panel.append(title,text,button('Enable',enable),button('Disable',disable),button('Send test',async()=>{try{const result=await request('test_notification',{},true);message(result.message);}catch(e){message(e.message);}}),button('Close',()=>panel.remove()));document.body.append(panel);
  try{const state=await request('status');enabled=state.enabled;message(!state.available?'Push service is not enabled on this site.':enabled?'Enabled for this signed-in browser.':'Not enabled. On iPhone, use the ERPNext app added to Home Screen.');}catch(e){message(e.message);}
 }
 window.cloudPush={open};
})();
