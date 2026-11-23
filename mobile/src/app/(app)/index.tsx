import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { View } from 'react-native';

import { useAuth } from '@/auth/session';
import { Screen, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { offlineStore } from '@/lib/offline-store';

/** Today: the person's day at a glance. Role cards (team attendance, approvals by department) come later. */
export default function Today() {
  const { user } = useAuth();
  const [waiting, setWaiting] = useState<number | null>(null);

  // Counted again whenever the tab is opened: captures made offline wait in the encrypted queue.
  useFocusEffect(
    useCallback(() => {
      let live = true;
      offlineStore()
        .then((store) => store.all())
        .then(
          (items) => live && setWaiting(items.filter((i) => i.state === 'waiting').length),
          () => live && setWaiting(null),
        );
      return () => {
        live = false;
      };
    }, []),
  );

  return (
    <Screen>
      <View style={{ gap: 6 }}>
        <T variant="title">{user?.name ? text('today.hello', { name: user.name }) : text('tab.today')}</T>
      </View>
      {waiting !== null && (
        <Status
          kind={waiting ? 'pending' : 'ok'}
          label={waiting ? text('today.waiting', { count: waiting }) : text('today.nothingWaiting')}
        />
      )}
    </Screen>
  );
}
