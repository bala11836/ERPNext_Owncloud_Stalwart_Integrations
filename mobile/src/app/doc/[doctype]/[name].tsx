import { Stack, useLocalSearchParams } from 'expo-router';
import { ScrollView } from 'react-native';

import { DocView } from '@/components/doc-view';
import { useTheme } from '@/theme';

export default function DocScreen() {
  const t = useTheme();
  const { doctype, name } = useLocalSearchParams<{ doctype: string; name: string }>();
  return (
    <ScrollView style={{ backgroundColor: t.c.bg }}>
      <Stack.Screen options={{ title: doctype }} />
      <DocView doctype={doctype} name={name} />
    </ScrollView>
  );
}
