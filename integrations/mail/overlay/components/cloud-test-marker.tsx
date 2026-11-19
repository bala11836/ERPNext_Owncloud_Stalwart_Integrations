"use client";
/* Test-site marker (owner, 19 Nov 2026): the same marker as the other apps.
   Test hostnames start with test. or test- (enforced by the renderer). */
import { useEffect } from "react";

export function CloudTestMarker() {
  useEffect(() => {
    try{if(window.top!==window||!/^test[.-]/.test(location.hostname)||document.getElementById('cloud-test-marker'))return;}catch(e){return;}var add=function(){if(document.getElementById('cloud-test-marker'))return;var s=document.createElement('style');s.textContent='#cloud-test-marker{position:fixed;top:0;left:0;right:0;height:3px;background:repeating-linear-gradient(135deg,#e8590c 0 12px,#f59f00 12px 24px);z-index:2147483647;pointer-events:none}#cloud-test-marker span{position:absolute;top:3px;left:50%;transform:translateX(-50%);background:#e8590c;color:#fff;font:600 10px/14px system-ui,sans-serif;letter-spacing:.08em;padding:0 8px;border-radius:0 0 4px 4px;opacity:.92}';var d=document.createElement('div');d.id='cloud-test-marker';d.setAttribute('aria-hidden','true');d.innerHTML='<span>TEST SITE</span>';document.head.appendChild(s);document.body.appendChild(d);};if(document.body)add();else document.addEventListener('DOMContentLoaded',add);
  }, []);
  return null;
}
