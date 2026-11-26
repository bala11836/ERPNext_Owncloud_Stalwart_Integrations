// Alerts while the app is closed (owner, 26 November 2026), the way large apps do it: ERPNext sends a data-only
// message straight to Google FCM (server part mobile_push); the native part (modules/approval-alert, PushService)
// writes the text on the phone and rings the full page for every approval, or shows a normal alert when an entry
// was returned. Google never gets a name or an amount. Android builds only: iPhone (Apple's push) comes later;
// Expo Go and tests have no native part.
import * as Linking from 'expo-linking';
import * as Notifications from 'expo-notifications';
import * as SecureStore from 'expo-secure-store';
import { useEffect } from 'react';
import { z } from 'zod';

import { ApprovalAlert } from '../../modules/approval-alert';
import { PUSH_ADDRESS, PUSH_API } from '@/auth/push-address';
import { AREA_LOOK } from '@/components/approval-row';
import { t as text } from '@/i18n';
import { AREAS, type Area, SPECS } from '@/lib/approvals';
import { ENTRY_DOCTYPE } from '@/lib/attendance';
import { type Api, callErp } from '@/lib/erp';

const RING_OFF = 'push-ring-off';
const Ok = z.object({ ok: z.boolean() });

export type PushState = 'registered' | 'denied' | 'unavailable';

/** This phone can receive alerts while closed: the native part exists only in Android builds (not iPhone, Expo Go, tests). */
export const pushAvailable = () => !!ApprovalAlert;

/**
 * After sign-in: this phone's FCM address to ERPNext, for the signed-in person only (the server keeps one phone per
 * person). 'unavailable' when the build has no Firebase file or no native part; 'denied' when alerts are blocked.
 */
export async function registerPush(api: Api): Promise<PushState> {
  if (!pushAvailable()) return 'unavailable';
  const { granted } = await Notifications.requestPermissionsAsync();
  if (!granted) return 'denied';
  let token: string;
  try {
    token = String((await Notifications.getDevicePushTokenAsync()).data);
  } catch {
    return 'unavailable'; // this build was made without google-services.json
  }
  await callErp(api, `${PUSH_API}.register_device`, Ok, { token, platform: 'android' }, { post: true });
  await SecureStore.setItemAsync(PUSH_ADDRESS, token);
  return 'registered';
}

/** Areas whose approvals ring the full page (all by default, owner); the person may make an area a normal alert. */
export async function ringOff(): Promise<Area[]> {
  const raw = await SecureStore.getItemAsync(RING_OFF).catch(() => null);
  const list: unknown = raw ? JSON.parse(raw) : [];
  return Array.isArray(list) ? list.filter((a): a is Area => AREAS.includes(a)) : [];
}

export async function setRing(area: Area, on: boolean) {
  const off = new Set(await ringOff());
  if (on) off.delete(area);
  else off.add(area);
  await SecureStore.setItemAsync(RING_OFF, JSON.stringify([...off]));
  await writePushTexts();
}

/**
 * Everything the native part needs to write an alert without the app running: which area each ERPNext document
 * type belongs to, the area names, the texts in the app's language, where a tap goes, and which areas ring.
 * Texts carry only the kind, the area and the site.
 */
export async function pushTexts() {
  const areas: Record<string, Area> = Object.fromEntries(Object.entries(SPECS).map(([doctype, s]) => [doctype, s.area]));
  areas[ENTRY_DOCTYPE] = 'attendance';
  return {
    areas,
    labels: Object.fromEntries(AREAS.map((a) => [a, text(AREA_LOOK[a].label)])),
    approvalTitle: text('push.approvalTitle'),
    verifyTitle: text('push.verifyTitle'),
    returnedTitle: text('push.returnedTitle'),
    bodySite: text('push.bodySite'),
    bodyNoSite: text('push.bodyNoSite'),
    returnedBody: text('push.returnedBody'),
    ringChannel: text('alert.ringChannel'),
    listChannel: text('alert.listChannel'),
    normalChannel: text('alert.normalChannel'),
    later: text('alert.later'),
    review: text('alert.review'),
    // The app's own link for "x", less the x: the native part appends a path such as "inbox".
    base: Linking.createURL('/x').slice(0, -1),
    ringOff: await ringOff(),
  };
}

export async function writePushTexts() {
  if (pushAvailable()) ApprovalAlert?.setPushTexts(JSON.stringify(await pushTexts()));
}

/** Signed-in screens: keep the native texts current and the phone registered (quietly; Settings shows the state). */
export function usePushRegistration(apiRef: { current: Api }) {
  useEffect(() => {
    writePushTexts().catch(() => {});
    registerPush(apiRef.current).catch(() => {}); // offline or the server part not installed yet: tried again next start
  }, [apiRef]);
}
