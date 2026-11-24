import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { ActivityIndicator, View } from 'react-native';

import { AppLock } from '@/auth/lock';
import { AuthProvider, useAuth } from '@/auth/session';
import { t as text } from '@/i18n';
import { clearErpCache } from '@/lib/erp';
import { clearInbox } from '@/lib/inbox';
import { adoptOffline, purgeOffline, wipeOffline } from '@/lib/offline-store';
import { resetConnection } from '@/lib/saved';
import { ThemeProvider, useTheme } from '@/theme';

export default function RootLayout() {
  return (
    <ThemeProvider>
      <AuthProvider onUser={adoptOffline}>
        <Nav />
      </AuthProvider>
    </ThemeProvider>
  );
}

function Nav() {
  const t = useTheme();
  const { status, ended } = useAuth();
  useEffect(() => {
    purgeOffline().catch(() => {}); // app start: nothing older than a day stays
  }, []);
  useEffect(() => {
    if (status !== 'signedOut') return;
    clearErpCache();
    clearInbox();
    resetConnection();
    // Only Sign out (after its warning, Settings) deletes unsent entries; an expired sign-in keeps them,
    // encrypted, for the same person (owner decisions 4 and 5); another person's sign-in deletes them first.
    if (ended === 'signOut') wipeOffline().catch(() => {});
  }, [status, ended]);
  if (status === 'loading') {
    return (
      <View style={{ flex: 1, justifyContent: 'center', backgroundColor: t.c.bg }}>
        <ActivityIndicator size="large" color={t.c.primary} />
      </View>
    );
  }
  const signedIn = status === 'signedIn';
  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: t.c.bg },
          headerTintColor: t.c.text,
          headerTitleStyle: { fontSize: t.font(20), fontWeight: '700' },
          contentStyle: { backgroundColor: t.c.bg },
        }}>
        {/* App screens open only after a real ERPNext sign-in; signing out (here or on the web) closes them. */}
        <Stack.Protected guard={signedIn}>
          <Stack.Screen name="(app)" options={{ headerShown: false }} />
          <Stack.Screen name="menu/[name]" />
          <Stack.Screen name="list/[doctype]" />
          <Stack.Screen name="doc/[doctype]/[name]" />
          <Stack.Screen name="settings" options={{ title: text('settings.title') }} />
          <Stack.Screen name="attendance/check-in" options={{ title: text('checkIn.title') }} />
          <Stack.Screen name="attendance/team" options={{ title: text('team.title') }} />
          <Stack.Screen name="attendance/mark" options={{ title: text('team.title') }} />
          <Stack.Screen name="attendance/approve" options={{ title: text('approve.title') }} />
        </Stack.Protected>
        <Stack.Protected guard={!signedIn}>
          <Stack.Screen name="sign-in" options={{ headerShown: false }} />
        </Stack.Protected>
        <Stack.Screen name="oauth/callback" options={{ headerShown: false }} />
      </Stack>
      {signedIn && <AppLock />}
    </>
  );
}
