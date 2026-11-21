import { useState } from 'react';
import { View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { APP_NAME, CLIENT_ID, useAuth } from '@/auth/session';
import { Button, Status, T } from '@/components/ui';
import { useTheme } from '@/theme';

export default function SignIn() {
  const t = useTheme();
  const { signIn } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onPress = async () => {
    setBusy(true);
    setError(null);
    try {
      await signIn();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Sign-in failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.c.bg }}>
      <View style={{ flex: 1, justifyContent: 'center', padding: 24, gap: 20, maxWidth: 520, width: '100%', alignSelf: 'center' }}>
        <T variant="title" style={{ fontSize: t.font(34) }}>
          {APP_NAME}
        </T>
        <Button label={busy ? 'Opening sign-in...' : 'Sign in with passkey'} icon="fingerprint" onPress={busy ? () => {} : onPress} />
        <T variant="small" color="muted">
          Uses your company passkey (Face ID / fingerprint), the same sign-in as ERPNext on the web.
        </T>
        {!CLIENT_ID && <Status kind="warn" label="Sign-in is not set up in this build yet" />}
        {error && <Status kind="danger" label={error} />}
      </View>
    </SafeAreaView>
  );
}
