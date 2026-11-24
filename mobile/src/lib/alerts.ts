// Phone alerts (owner, 24 November 2026): one Android notification channel per area (Payments, Purchase, ...) with
// a normal sound the person can change per area; the locked-screen text names only the kind, the count and the
// site, never a person or an amount. Tapping an alert opens the screen named in its `url` (only the app's own
// approval screens), behind the app lock. Real alerts come with push (P14); the Settings test uses the same path.
import * as Notifications from 'expo-notifications';
import { AndroidImportance } from 'expo-notifications';
import * as Linking from 'expo-linking';
import { router } from 'expo-router';
import { useEffect } from 'react';

import { ApprovalAlert } from '../../modules/approval-alert';

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

/** Android: can this phone show the full page (Android 14+ asks the person once)? Elsewhere: not offered. */
export const fullPageAllowed = () => ApprovalAlert?.canUseFullScreen() ?? true;
export const fullPageAvailable = () => !!ApprovalAlert;
export const openFullPageSettings = () => ApprovalAlert?.openFullScreenSettings();

/**
 * An approval alert after `seconds`. Android: the full page over the locked screen, ringing up to 30 seconds
 * (modules/approval-alert). iPhone (Apple allows a full page only for phone calls): a normal notification.
 * `body` names only the count and the site.
 */
export async function scheduleApprovalAlert(seconds: number, a: { area: Area; title: string; body: string; url: string }): Promise<'page' | 'banner'> {
  const url = openableUrl(a.url) ?? '/inbox';
  const label = text(AREA_LOOK[a.area].label);
  if (ApprovalAlert) {
    ApprovalAlert.schedule(seconds, {
      area: a.area,
      areaLabel: label,
      title: a.title,
      body: a.body,
      url: Linking.createURL(url),
      channel: text('alert.ringChannel', { area: label }),
      listChannel: text('alert.listChannel', { area: label }),
      later: text('alert.later'),
      review: text('alert.review'),
    });
    return 'page';
  }
  await Notifications.scheduleNotificationAsync({
    content: { title: a.title, body: a.body, data: { url } },
    trigger: { type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL, seconds, channelId: await areaChannel(a.area) },
  });
  return 'banner';
}
