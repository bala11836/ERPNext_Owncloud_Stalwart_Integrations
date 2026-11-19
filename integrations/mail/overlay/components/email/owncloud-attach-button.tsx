"use client";

import {useEffect,useRef,useState} from 'react';
import {Cloud,Loader2} from '@/components/icons';
import {Button} from '@/components/ui/button';
import {toast} from '@/stores/toast-store';

const FILES='https://drive.example.com';
const MAX_BYTES=25*1024*1024;

/** Uses an independent Files browser session; mail never receives a Files token. */
export function OwncloudAttachButton({onFiles}:{onFiles:(files:File[])=>Promise<void>}) {
 const [busy,setBusy]=useState(false);
 const pending=useRef<{popup:Window;nonce:string;timer:ReturnType<typeof setInterval>}|null>(null);
 const addFiles=useRef(onFiles);addFiles.current=onFiles;
 const clear=()=>{if(pending.current)clearInterval(pending.current.timer);pending.current=null;setBusy(false);};
 useEffect(()=>{
  const receive=async(event:MessageEvent)=>{
   const current=pending.current;
   if(!current||event.origin!==FILES||event.source!==current.popup||event.data?.nonce!==current.nonce)return;
   const message=event.data;
   if(message.name==='office-picker:error'){toast.error(String(message.error||'Could not attach the selected file.'));clear();return;}
   if(message.name==='office-picker:cancel'){current.popup.close();clear();return;}
   if(message.name!=='office-picker:file')return;
   if(!(message.bytes instanceof ArrayBuffer)||message.bytes.byteLength>MAX_BYTES||typeof message.filename!=='string'){
    toast.error('The Files attachment is invalid or exceeds 25 MB.');clear();return;
   }
   const name=message.filename.split(/[\\/]/).pop()?.replace(/[\r\n]/g,'').slice(0,255)||'attachment';
   try{
    await addFiles.current([new File([message.bytes],name,{type:typeof message.contentType==='string'?message.contentType:'application/octet-stream'})]);
    current.popup.close();
   }catch{toast.error('The attachment could not be uploaded. Please try again.');}
   finally{clear();}
  };
  window.addEventListener('message',receive);
  return()=>{window.removeEventListener('message',receive);if(pending.current)clearInterval(pending.current.timer);};
 },[]);
 const open=()=>{
  if(pending.current){pending.current.popup.focus();return;}
  const nonce=crypto.randomUUID();
  const url=new URL(FILES+'/');
  url.searchParams.set('embed','true');url.searchParams.set('embed-target','file');
  url.searchParams.set('embed-delegate-authentication','false');url.searchParams.set('office-mail-picker',nonce);
  const popup=window.open(url.toString(),'office-file-picker-'+nonce,'popup,width=1100,height=780');
  if(!popup){toast.error('Allow pop-ups for Mail to open the Files picker.');return;}
  setBusy(true);
  const started=Date.now();
  const timer=setInterval(()=>{if(popup.closed||Date.now()-started>10*60*1000)clear();},700);
  pending.current={popup,nonce,timer};
 };
 return <Button type="button" variant="ghost" onClick={open} className="h-9 gap-1.5 px-2" title="Attach a file from your ownCloud account" data-testid="composer-attach-owncloud">
  {busy?<Loader2 className="h-4 w-4 animate-spin"/>:<Cloud className="h-4 w-4"/>}Files
 </Button>;
}
