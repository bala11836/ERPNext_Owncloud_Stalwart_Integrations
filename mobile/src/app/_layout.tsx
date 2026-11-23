import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { ActivityIndicator, View } from 'react-native';

import { AppLock } from '@/auth/lock';
import { AuthProvider, useAuth } from '@/auth/session';
import { clearErpCache } from '@/lib/erp';
import { wipeOffline } from '@/lib/offline-store';
import { ThemeProvider, useTheme } from '@/theme';

export default function RootLayout() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Nav />
      </AuthProvider>
    </ThemeProvider>
  );
}

function Nav() {
  const t = useTheme();
  const { status } = useAuth();
  useEffect(() => {
    if (status !== 'signedOut') return;
    clearErpCache();
    // ponytail: wipes unsent items without asking; the warning with "send now" comes with the queue's screen.
    wipeOffline().catch(() => {});
  }, [status]);
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
