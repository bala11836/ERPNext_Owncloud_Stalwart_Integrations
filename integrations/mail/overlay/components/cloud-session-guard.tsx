'use client';
import { useEffect } from 'react';
import { useAuthStore } from '@/stores/auth-store';
import { logoutEpoch, markRemoteCleanup } from '@/lib/cloud-session';
export function CloudSessionGuard() {
  useEffect(() => {
    const initial = logoutEpoch(); let busy = false;
    const check = () => {
      if (busy || initial === logoutEpoch() || !useAuthStore.getState().isAuthenticated) return;
      busy = true; markRemoteCleanup();
      // Preserve drafts/offline data while revoking every authenticated account slot.
      void useAuthStore.getState().logoutAll({endProviderSession:false,keepLocalData:true});
    };
    const timer = window.setInterval(check, 500);
    window.addEventListener('focus', check); window.addEventListener('pageshow', check);
    return () => { clearInterval(timer); window.removeEventListener('focus', check); window.removeEventListener('pageshow', check); };
  }, []);
  return null;
}
