import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import * as SecureStore from 'expo-secure-store';
import { useCallback, useEffect, useState } from 'react';
import { Linking, Pressable, Switch, TextInput, View } from 'react-native';

import { RELOCK_AFTER_MS } from '@/auth/lock';
import { PUSH_ADDRESS } from '@/auth/push-address';
import { useApiRef, useAuth } from '@/auth/session';
import { AREA_LOOK } from '@/components/approval-row';
import { Button, Screen, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { fullPageAllowed, fullPageAvailable, openFullPageSettings, scheduleApprovalAlert } from '@/lib/alerts';
import { AREAS, type Area } from '@/lib/approvals';
import { type Api } from '@/lib/erp';
import { loadBoot } from '@/lib/attendance';
import { offlineStorageKind, offlineStore } from '@/lib/offline-store';
import { type PushState, pushAvailable, registerPush, ringOff, setRing } from '@/lib/push';
import { flushQueue } from '@/lib/sender';
import { useTheme } from '@/theme';

/** Alerts while the app is closed: on or why not, a retry, which areas ring the full page, and the phone's settings. */
function PushSettings({ api }: { api: () => Api }) {
  const t = useTheme();
  const [state, setState] = useState<PushState | 'failed' | null>(null);
  const [off, setOff] = useState<Area[]>([]);
  useEffect(() => {
    SecureStore.getItemAsync(PUSH_ADDRESS).then((a) => a && setState('registered'), () => {});
    ringOff().then(setOff, () => {});
  }, []);
  const turnOn = () => registerPush(api()).then(setState, () => setState('failed'));
  const flip = (area: Area, on: boolean) => {
    setOff((o) => (on ? o.filter((a) => a !== area) : [...o, area]));
    setRing(area, on).catch(() => {});
  };
  return (
    <View style={{ gap: 10 }}>
      {state === 'registered' ? (
        <Status kind="ok" label={text('push.on')} />
      ) : (
        <>
          {state ? <Status kind="warn" label={text(`push.${state}`)} /> : null}
          <Button label={text('push.turnOn')} icon="bell" secondary onPress={turnOn} />
        </>
      )}
      <T style={{ fontWeight: '700' }}>{text('push.ringFor')}</T>
      <T variant="small" color="muted">
        {text('push.ringHint')}
      </T>
      {AREAS.map((area) => {
        const on = !off.includes(area);
        const label = text(AREA_LOOK[area].label);
        return (
          <Pressable
            key={area}
            accessibilityRole="switch"
            accessibilityLabel={label}
            accessibilityState={{ checked: on }}
            onPress={() => flip(area, !on)}
            style={{ minHeight: t.touch, flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 4 }}>
            <T style={{ flex: 1 }}>{label}</T>
            <Switch value={on} onValueChange={(v) => flip(area, v)} trackColor={{ true: t.c.primary, false: t.c.muted }} thumbColor={t.c.bg} />
          </Pressable>
        );
      })}
      <T variant="small" color="muted">
        {text('push.battery')}
      </T>
      <Button label={text('push.phoneSettings')} icon="chevron-right" secondary onPress={() => Linking.openSettings()} />
    </View>
  );
}

const CONFIRM_WORD = 'DELETE';
const TEST_DELAY_S = 60;

/**
 * A test approval alert in a minute, exactly as a real one will look (lib/alerts.ts): Payments, the kind, a count
 * and the person's first site, no names or amounts. Android: the full page over the locked screen, ringing; iPhone:
 * a notification. Review / tapping opens the Inbox behind the app lock. No server involved.
 */
async function scheduleTest(api: Api): Promise<'page' | 'banner' | false> {
  const { granted } = await Notifications.requestPermissionsAsync();
  if (!granted) return false;
  const site = await loadBoot(api).then((b) => b.sites[0]?.label ?? b.check_in_sites[0]?.label, () => undefined);
  return scheduleApprovalAlert(TEST_DELAY_S, {
    area: 'payments',
    title: text('alert.paymentTitle'),
    body: site ? text('alert.paymentBody', { site }) : text('alert.paymentBodyNoSite'),
    url: '/inbox',
  });
}

export default function Settings() {
  const t = useTheme();
  const { user, signOut } = useAuth();
  const apiRef = useApiRef();
  const toggle = () => t.setOutdoor(!t.outdoor);
  const [storage, setStorage] = useState<'encrypted' | 'memory' | null>(null);
  // Owner decision 4 (23 November 2026): with unsent entries, signing out needs "Send now" or the word DELETE.
  const [unsent, setUnsent] = useState(0);
  const [typed, setTyped] = useState('');
  const [sending, setSending] = useState(false);
  const [test, setTest] = useState<'scheduled' | 'scheduledPage' | 'denied' | 'failed' | null>(null);
  const sendTest = () =>
    scheduleTest(apiRef.current).then(
      (how) => setTest(how === 'page' ? 'scheduledPage' : how ? 'scheduled' : 'denied'),
      () => setTest('failed'),
    );
  // Android 14+: full-page alerts need the person's once-only permission (system Settings).
  const [pageAllowed, setPageAllowed] = useState(fullPageAllowed);
  const count = useCallback(
    () =>
      offlineStore()
        .then((st) => st.all())
        .then((items) => setUnsent(items.length), () => setUnsent(0)),
    [],
  );
  useEffect(() => {
    offlineStorageKind().then(setStorage, () => setStorage('memory'));
    count();
  }, [count]);
  const sendNow = async () => {
    setSending(true);
    await flushQueue(apiRef.current).catch(() => {});
    await count();
    setSending(false);
  };
  const mayLeave = unsent === 0 || typed.trim() === CONFIRM_WORD;
  return (
    <Screen>
      <View style={{ gap: 6 }}>
        <T variant="title">{user?.name || text('settings.signedIn')}</T>
        {user?.email ? <T color="muted">{user.email}</T> : null}
      </View>

      <Pressable
        accessibilityRole="switch"
        accessibilityState={{ checked: t.outdoor }}
        onPress={toggle}
        style={{
          minHeight: t.touch + 16,
          flexDirection: 'row',
          alignItems: 'center',
          gap: 12,
          padding: 16,
          borderWidth: t.border,
          borderColor: t.c.border,
          borderRadius: 10,
        }}>
        <View style={{ flex: 1, gap: 4 }}>
          <T style={{ fontWeight: '700' }}>{text('settings.outdoor', { state: text(t.outdoor ? 'settings.on' : 'settings.off') })}</T>
          <T variant="small" color="muted">
            {text('settings.outdoorHint')}
          </T>
        </View>
        <Switch
          value={t.outdoor}
          onValueChange={toggle}
          trackColor={{ true: t.c.primary, false: t.c.muted }}
          thumbColor={t.c.bg}
        />
      </Pressable>

      <Status kind="ok" label={text('settings.appLock', { seconds: RELOCK_AFTER_MS / 1000 })} />
      {storage ? (
        <Status
          kind={storage === 'encrypted' ? 'ok' : 'warn'}
          label={text(storage === 'encrypted' ? 'storage.encrypted' : 'storage.memory')}
        />
      ) : null}

      <View style={{ gap: 10 }}>
        <Button label={text('notify.test')} icon="bell" secondary onPress={sendTest} />
        {fullPageAvailable() && !pageAllowed && (
          <>
            <Status kind="warn" label={text('notify.pageOff')} />
            <Button
              label={text('notify.allowPage')}
              icon="chevron-right"
              secondary
              onPress={() => {
                openFullPageSettings();
                setPageAllowed(fullPageAllowed());
              }}
            />
          </>
        )}
        {test ? (
          <Status kind={test === 'scheduled' || test === 'scheduledPage' ? 'ok' : 'warn'} label={text(`notify.${test}`, { seconds: TEST_DELAY_S })} />
        ) : null}
      </View>

      {pushAvailable() && <PushSettings api={() => apiRef.current} />}

      {unsent > 0 && (
        <View style={{ gap: 10 }}>
          <Status kind="warn" label={text('signOut.unsent', { count: unsent })} />
          <Button label={text('today.sendNow')} icon="upload" onPress={sendNow} disabled={sending} />
          <TextInput
            value={typed}
            onChangeText={setTyped}
            accessibilityLabel={text('signOut.typeDelete', { word: CONFIRM_WORD })}
            placeholder={text('signOut.typeDelete', { word: CONFIRM_WORD })}
            placeholderTextColor={t.c.muted}
            autoCapitalize="characters"
            autoCorrect={false}
            style={{
              minHeight: t.touch,
              paddingHorizontal: 12,
              borderWidth: 1,
              borderColor: t.c.line,
              borderRadius: 10,
              color: t.c.text,
              fontSize: t.font(16),
            }}
          />
        </View>
      )}
      <Button label={text('settings.signOut')} icon="sign-out" secondary tone={unsent > 0 ? 'danger' : 'primary'} onPress={signOut} disabled={!mayLeave} />
      <T variant="small" color="muted">
        {text('settings.version', { version: Constants.expoConfig?.version ?? '' })}
      </T>
    </Screen>
  );
}
