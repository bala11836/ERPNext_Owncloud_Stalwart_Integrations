import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { View } from 'react-native';

import { useApiRef, useAuth } from '@/auth/session';
import { Card, Screen, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { formatDate, localToday } from '@/lib/format';
import { byType, refreshInbox, useInbox } from '@/lib/inbox';
import { loadTodayHr } from '@/lib/my-hr';
import { offlineStore } from '@/lib/offline-store';

const WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

type Hr = Awaited<ReturnType<typeof loadTodayHr>>;

/**
 * Today (build guide section 6), step T1: what waits for the person, from data the app already has. Attendance
 * cards (T2) and the server's role cards (T3) come next.
 */
export default function Today() {
  const { user } = useAuth();
  const apiRef = useApiRef();
  const inbox = useInbox();
  const [queue, setQueue] = useState<{ waiting: number; refused: number } | null>(null);
  const [hr, setHr] = useState<Hr>(null);

  // Fresh whenever the tab is opened: the offline queue, the inbox and the HR card.
  useFocusEffect(
    useCallback(() => {
      let live = true;
      offlineStore()
        .then((store) => store.all())
        .then(
          (items) =>
            live &&
            setQueue({
              waiting: items.filter((i) => i.state === 'waiting').length,
              refused: items.filter((i) => i.state === 'failed').length,
            }),
          () => live && setQueue(null),
        );
      refreshInbox(apiRef.current);
      loadTodayHr(apiRef.current, localToday()).then(
        (h) => live && setHr(h),
        () => live && setHr(null),
      );
      return () => {
        live = false;
      };
    }, [apiRef]),
  );

  const today = localToday();
  const unread = inbox.notifications.filter((n) => !n.read).length;
  const toInbox = () => router.push('/inbox');

  return (
    <Screen>
      <View style={{ gap: 4 }}>
        <T variant="title">{user?.name ? text('today.hello', { name: user.name }) : text('tab.today')}</T>
        <T color="muted">{`${WEEKDAYS[new Date().getDay()]}, ${formatDate(today)}`}</T>
      </View>

      {inbox.loaded && (
        <Card
          icon="hand-back-right-outline"
          title={text('today.waitingForYou')}
          detail={inbox.actions.length ? byType(inbox.actions.map((a) => a.reference_doctype)) : text('inbox.noneWaiting')}
          count={inbox.actions.length}
          onPress={toInbox}
        />
      )}
      {inbox.loaded && unread > 0 && (
        <Card icon="bell-outline" title={text('today.unread', { count: unread })} onPress={toInbox} />
      )}

      {queue && (
        <Status
          kind={queue.waiting ? 'pending' : 'ok'}
          label={queue.waiting ? text('today.waiting', { count: queue.waiting }) : text('today.nothingWaiting')}
        />
      )}
      {queue && queue.refused > 0 && <Status kind="danger" label={text('today.refused', { count: queue.refused })} />}

      {hr && (hr.nextHoliday || hr.openLeaves > 0) && (
        <Card
          icon="calendar-star"
          title={
            hr.nextHoliday
              ? text('today.nextHoliday', { date: formatDate(hr.nextHoliday.holiday_date), name: hr.nextHoliday.description ?? '' })
              : text('tab.myHr')
          }
          detail={hr.openLeaves ? text('today.openLeaves', { count: hr.openLeaves }) : undefined}
          onPress={() => router.push('/my-hr')}
        />
      )}
    </Screen>
  );
}
