import Constants from 'expo-constants';
import { useEffect, useState } from 'react';
import { Pressable, Switch, View } from 'react-native';

import { RELOCK_AFTER_MS } from '@/auth/lock';
import { useAuth } from '@/auth/session';
import { Button, Screen, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { offlineStorageKind } from '@/lib/offline-store';
import { useTheme } from '@/theme';

export default function Settings() {
  const t = useTheme();
  const { user, signOut } = useAuth();
  const toggle = () => t.setOutdoor(!t.outdoor);
  const [storage, setStorage] = useState<'encrypted' | 'memory' | null>(null);
  useEffect(() => {
    offlineStorageKind().then(setStorage, () => setStorage('memory'));
  }, []);
  return (
    <Screen>
      <View style={{ gap: 6 }}>
        <T variant="title">{user?.name || 'Signed in'}</T>
        {user?.email ? <T color="muted">{user.email}</T> : null}
        <Status kind="ok" label={user ? `Connected to ERPNext: ${user.roles.length} roles` : 'Connected to ERPNext'} />
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
          <T style={{ fontWeight: '700' }}>Outdoor mode: {t.outdoor ? 'ON' : 'OFF'}</T>
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

      <Button label="Sign out" icon="sign-out" secondary onPress={signOut} />
      <T variant="small" color="muted">
        Version {Constants.expoConfig?.version}
      </T>
    </Screen>
  );
}
