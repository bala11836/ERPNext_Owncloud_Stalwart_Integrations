// Phone alerts (owner, 24 November 2026): one Android notification channel per area (Payments, Purchase, ...) with
// a normal sound the person can change per area; the locked-screen text names only the kind, the count and the
// site, never a person or an amount. Tapping an alert opens the screen named in its `url` (only the app's own
// approval screens), behind the app lock. Real alerts come with push (P14); the Settings test uses the same path.
import * as Notifications from 'expo-notifications';
import { AndroidImportance } from 'expo-notifications';
import { router } from 'expo-router';
import { useEffect } from 'react';

import { AREA_LOOK } from '@/components/approval-row';
import { t as text } from '@/i18n';
import type { Area } from '@/lib/approvals';

/** The only places an alert may open. */
export const openableUrl = (url: unknown): string | null =>
  typeof url === 'string' && /^\/(inbox|approvals\/[^?#]*)$/.test(url) ? url : null;

/** The area's channel (created once; Android keeps the person's own sound and on/off choice for it). */
export async function areaChannel(area: Area): Promise<string> {
  await Notifications.setNotificationChannelAsync(area, { name: text(AREA_LOOK[area].label), importance: AndroidImportance.HIGH });
  return area;
}

let handled: string | null = null;
/** Signed-in screens: a tapped alert opens its screen once (the app lock shows first when the app was away). */
export function useAlertTaps() {
  const last = Notifications.useLastNotificationResponse();
  useEffect(() => {
    const id = last?.notification?.request?.identifier ?? null;
    const url = openableUrl(last?.notification?.request?.content?.data?.url);
    if (!id || id === handled || !url) return;
    handled = id;
    router.push(url as never);
  }, [last]);
}
