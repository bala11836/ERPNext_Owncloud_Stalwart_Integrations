/* Dedicated push scope: no fetch interception or application-page caching. */
'use strict';
const options=JSON.parse(new URL(self.location.href).searchParams.get('config')||'null');
if(!options||typeof options.projectId!=='string'||typeof options.messagingSenderId!=='string')throw Error('Push configuration missing');
importScripts('https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js','https://www.gstatic.com/firebasejs/10.8.0/firebase-messaging-compat.js');
firebase.initializeApp(options);
firebase.messaging().onBackgroundMessage(payload=>{
 if(payload.notification)return;
 const data=payload.data||{};
 return self.registration.showNotification(data.title||'ERPNext',{
  body:data.body||'Open ERPNext to view your notification.',
  icon:'/assets/erpnext_drive_integrations/company-logo-approved-v6.svg',
  tag:data.event_id?'ci-'+data.event_id:undefined,data:{url:data.click_action||'/desk'}
 });
});
self.addEventListener('notificationclick',event=>{
 event.notification.close();let target;
 try{target=new URL(event.notification.data?.url||'/desk',self.location.origin);}catch(_){target=new URL('/desk',self.location.origin);}
 if(target.origin!==self.location.origin)target=new URL('/desk',self.location.origin);
 event.waitUntil(clients.openWindow(target.href));
});
self.addEventListener('install',()=>self.skipWaiting());
