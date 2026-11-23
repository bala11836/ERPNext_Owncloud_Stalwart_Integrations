import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Modal, Pressable, View } from 'react-native';

import { useApiRef, useAuth } from '@/auth/session';
import { Icon, type IconName } from '@/components/icon';
import { Button, Card, Progress, Screen, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { type TodayAttendance, clock, loadTodayAttendance } from '@/lib/attendance';
import { formatDate, localToday } from '@/lib/format';
import { byType, refreshInbox, useInbox } from '@/lib/inbox';
import { loadTodayHr } from '@/lib/my-hr';
import { offlineStore } from '@/lib/offline-store';
import { flushQueue } from '@/lib/sender';
import { useTheme } from '@/theme';

const WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const nowHHMM = (d = new Date()) => `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;

type Hr = Awaited<ReturnType<typeof loadTodayHr>>;
type Action = { key: string; icon: IconName; label: string; go: () => void };

/**
 * Today: the person's day at a glance, by what ERPNext lets them do (owner's reference design of 23 November,
 * kept to the sunlight rules): their own attendance first, then their team, what waits for their approval,
 * what waits to be sent, and the rest. Only real actions appear; role cards decided by the server come later.
 */
export default function Today() {
  const t = useTheme();
  const { user } = useAuth();
  const apiRef = useApiRef();
  const inbox = useInbox();
  const [queue, setQueue] = useState<{ waiting: number; refused: number; offline: boolean } | null>(null);
  const [hr, setHr] = useState<Hr>(null);
  const [att, setAtt] = useState<TodayAttendance | null>(null);
  const [sheet, setSheet] = useState(false);

  const countQueue = useCallback(async (offline: boolean) => {
    const items = await (await offlineStore()).all();
    setQueue({
      waiting: items.filter((i) => i.state === 'waiting').length,
      refused: items.filter((i) => i.state === 'failed').length,
      offline,
    });
  }, []);
  const sendNow = useCallback(async () => {
    const result = await flushQueue(apiRef.current).catch(() => ({ stopped: true }));
    await countQueue(result.stopped).catch(() => setQueue(null));
  }, [apiRef, countQueue]);

  // Fresh whenever the tab is opened: unsent captures go first, then the cards are counted again.
  useFocusEffect(
    useCallback(() => {
      let live = true;
      sendNow();
      refreshInbox(apiRef.current);
      loadTodayAttendance(apiRef.current, nowHHMM(), localToday()).then(
        (a) => live && setAtt(a),
        () => live && setAtt(null),
      );
      loadTodayHr(apiRef.current, localToday()).then(
        (h) => live && setHr(h),
        () => live && setHr(null),
      );
      return () => {
        live = false;
      };
    }, [apiRef, sendNow]),
  );

  const today = localToday();
  const unread = inbox.notifications.filter((n) => !n.read).length;

  const actions: Action[] = [
    ...(att?.self ? [{ key: 'self', icon: 'checked-in' as IconName, label: text('fab.checkIn'), go: () => router.push('/attendance/check-in') }] : []),
    ...(att?.teams ?? []).map((tm) => ({
      key: `team-${tm.siteId}`,
      icon: 'team' as IconName,
      label: text('fab.mark', { site: tm.site }),
      go: () => router.push({ pathname: '/attendance/team', params: { site: tm.siteId, shift: tm.shiftId } }),
    })),
    ...(att?.approvals ?? []).map((ap) => ({
      key: `appr-${ap.siteId}`,
      icon: 'approve' as IconName,
      label: text('fab.approve', { site: ap.site }),
      go: () => router.push({ pathname: '/attendance/approve', params: { site: ap.siteId } }),
    })),
  ];

  return (
    <View style={{ flex: 1, backgroundColor: t.c.bg }}>
      <Screen>
        {/* Greeting, date, and one-tap Outdoor mode (rule 13). */}
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <View style={{ flex: 1, gap: 4 }}>
            <T variant="title">{user?.name ? text('today.hello', { name: user.name }) : text('tab.today')}</T>
            <T color="muted">{`${WEEKDAYS[new Date().getDay()]}, ${formatDate(today)}`}</T>
          </View>
          <Pressable
            accessibilityRole="switch"
            accessibilityState={{ checked: t.outdoor }}
            accessibilityLabel={text('today.outdoor', { state: t.outdoor ? 'ON' : 'OFF' })}
            onPress={() => t.setOutdoor(!t.outdoor)}
            style={{
              minWidth: t.touch + 8,
              minHeight: t.touch + 8,
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 12,
              borderWidth: t.outdoor ? 4 : t.border,
              borderColor: t.outdoor ? t.c.primary : t.c.border,
            }}>
            <Icon name="sun" size={t.font(26)} color={t.c.text} />
            <T variant="small" style={{ fontWeight: '700' }}>
              {t.outdoor ? text('today.outdoorOn') : text('today.outdoorOff')}
            </T>
          </Pressable>
        </View>

        {queue?.offline && queue.waiting > 0 && <Status kind="offline" label={text('today.offlineBanner', { count: queue.waiting })} />}

        {/* My own attendance: a compact bar for everyone who checks in themselves. */}
        {att?.self && (
          <Pressable
            accessibilityRole="button"
            onPress={() => router.push('/attendance/check-in')}
            style={{
              minHeight: t.touch + 8,
              flexDirection: 'row',
              alignItems: 'center',
              gap: 10,
              paddingHorizontal: 14,
              borderRadius: 12,
              borderWidth: t.border,
              borderColor: att.self.today ? t.c.ok : t.c.warn,
            }}>
            <Icon
              name={att.self.today ? 'checked-in' : 'not-checked-in'}
              size={t.font(26)}
              color={att.self.today ? t.c.ok : t.c.warn}
            />
            <T style={{ flex: 1, fontWeight: '700' }}>
              {att.self.today
                ? text('today.selfIn', {
                    time: clock(att.self.today.check_in_time),
                    state: att.self.today.state,
                    out: att.self.today.check_out_time ? text('today.checkedOut', { time: clock(att.self.today.check_out_time) }) : '',
                  })
                : text('today.selfNotIn')}
            </T>
            <T style={{ fontWeight: '700' }} color="primary">
              {att.self.today ? text('today.open') : text('fab.checkIn')}
            </T>
          </Pressable>
        )}

        {/* My team (supervisor): marked out of total, by state in words, and the next step. */}
        {att?.teams.map((tm) => {
          const left = tm.counts['Not recorded'] ?? 0;
          const sent = (tm.counts.Submitted ?? 0) + (tm.counts.Approved ?? 0);
          const go = () => router.push({ pathname: '/attendance/team', params: { site: tm.siteId, shift: tm.shiftId } });
          return (
            <View key={`team-${tm.siteId}`} style={{ gap: 10, padding: 16, borderRadius: 12, borderWidth: t.border, borderColor: t.c.border }}>
              <T variant="small" color="muted" style={{ fontWeight: '700' }}>
                {text('today.teamLabel', { site: tm.site, shift: tm.shift }).toUpperCase()}
              </T>
              <View style={{ flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between' }}>
                <T variant="title">{text('today.myTeam')}</T>
                <T variant="title">{`${tm.marked}/${tm.total}`}</T>
              </View>
              <Progress done={tm.marked} total={tm.total} label={text('today.team', { site: tm.site, marked: tm.marked, total: tm.total })} />
              <View style={{ gap: 6 }}>
                {sent > 0 && <Status kind="ok" label={text('today.teamSent', { count: sent })} />}
                {(tm.counts.Draft ?? 0) > 0 && <Status kind="pending" label={text('today.teamDraft', { count: tm.counts.Draft })} />}
                {(tm.counts.Returned ?? 0) > 0 && <Status kind="warn" label={text('today.teamReturned', { count: tm.counts.Returned })} />}
                {left > 0 && <Status kind="warn" label={text('today.teamLeft', { count: left })} />}
              </View>
              <Button
                label={
                  left > 0
                    ? text('today.continueMarking', { count: left })
                    : tm.drafts > 0
                      ? text('team.submit', { count: tm.drafts })
                      : text('today.openTeam')
                }
                icon={left > 0 ? 'camera' : tm.drafts > 0 ? 'fingerprint' : 'team'}
                onPress={go}
              />
            </View>
          );
        })}

        {/* Attendance waiting for my approval (PM): how many, how many exceptions, then the bulk screen. */}
        {att?.approvals.map((ap) => (
          <View key={`appr-${ap.siteId}`} style={{ gap: 10, padding: 16, borderRadius: 12, borderWidth: t.border, borderColor: t.c.border }}>
            <View style={{ flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between' }}>
              <T variant="title" style={{ flex: 1 }}>
                {text('today.attendanceToApprove', { site: ap.site })}
              </T>
              <T variant="title">{ap.count}</T>
            </View>
            <Status kind="ok" label={text('today.readyToApprove', { count: ap.reviewable })} />
            {ap.exceptions > 0 && <Status kind="warn" label={text('today.exceptions', { count: ap.exceptions })} />}
            <Button
              label={text('today.reviewApprove')}
              icon="fingerprint"
              onPress={() => router.push({ pathname: '/attendance/approve', params: { site: ap.siteId } })}
            />
          </View>
        ))}

        {inbox.loaded && (
          <Card
            icon="hand"
            title={text('today.waitingForYou')}
            detail={inbox.actions.length ? byType(inbox.actions.map((a) => a.reference_doctype)) : text('inbox.noneWaiting')}
            count={inbox.actions.length}
            onPress={() => router.push('/inbox')}
          />
        )}
        {inbox.loaded && unread > 0 && (
          <Card icon="bell" title={text('today.unread', { count: unread })} onPress={() => router.push('/inbox')} />
        )}

        {/* Waiting to send: the encrypted offline queue, with "Send now". */}
        {queue && (queue.waiting > 0 || queue.refused > 0) ? (
          <View style={{ gap: 10, padding: 16, borderRadius: 12, borderWidth: t.border, borderColor: t.c.warn }}>
            {queue.waiting > 0 && <Status kind="pending" label={text('today.waiting', { count: queue.waiting })} />}
            {queue.refused > 0 && <Status kind="danger" label={text('today.refused', { count: queue.refused })} />}
            {queue.waiting > 0 && <Button label={text('today.sendNow')} icon="upload" secondary onPress={sendNow} />}
          </View>
        ) : (
          queue && <Status kind="ok" label={text('today.nothingWaiting')} />
        )}

        {hr && (hr.nextHoliday || hr.openLeaves > 0) && (
          <Card
            icon="holiday"
            title={
              hr.nextHoliday
                ? text('today.nextHoliday', { date: formatDate(hr.nextHoliday.holiday_date), name: hr.nextHoliday.description ?? '' })
                : text('tab.myHr')
            }
            detail={hr.openLeaves ? text('today.openLeaves', { count: hr.openLeaves }) : undefined}
            onPress={() => router.push('/my-hr')}
          />
        )}
        {actions.length > 0 && <View style={{ height: 72 }} />}
      </Screen>

      {/* "+": only the actions this person really has (owner decision; no empty or pretend actions). */}
      {actions.length > 0 && (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={text('fab.open')}
          onPress={() => setSheet(true)}
          style={{
            position: 'absolute',
            right: 16,
            bottom: 16,
            width: 64,
            height: 64,
            borderRadius: 32,
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: t.c.primary,
            borderWidth: 3,
            borderColor: t.c.bg,
          }}>
          <Icon name="plus" size={32} color={t.c.onPrimary} />
        </Pressable>
      )}
      <Modal visible={sheet} transparent animationType="slide" onRequestClose={() => setSheet(false)}>
        <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.55)' }} onPress={() => setSheet(false)} accessibilityLabel={text('fab.close')} />
        <View style={{ backgroundColor: t.c.bg, padding: 16, gap: 12, borderTopLeftRadius: 20, borderTopRightRadius: 20 }}>
          <T variant="title">{text('fab.title')}</T>
          {actions.map((a) => (
            <Button
              key={a.key}
              label={a.label}
              icon={a.icon}
              onPress={() => {
                setSheet(false);
                a.go();
              }}
            />
          ))}
          <Button label={text('fab.close')} icon="close" secondary onPress={() => setSheet(false)} />
        </View>
      </Modal>
    </View>
  );
}

