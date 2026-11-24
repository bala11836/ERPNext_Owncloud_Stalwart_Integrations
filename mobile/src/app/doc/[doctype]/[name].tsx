import { Stack, useLocalSearchParams } from 'expo-router';
import { ScrollView } from 'react-native';

import { DocView } from '@/components/doc-view';
import { NoScreenshots } from '@/components/no-screenshots';
import { useTheme } from '@/theme';

/** A record, read-only. Approvals open as approval cards (app/approvals), not here. */
export default function DocScreen() {
  const t = useTheme();
  const { doctype, name } = useLocalSearchParams<{ doctype: string; name: string }>();
  return (
    <ScrollView style={{ backgroundColor: t.c.bg }}>
      <Stack.Screen options={{ title: doctype }} />
      {/* Build guide section 9: no screenshots of payslips. */}
      {doctype === 'Salary Slip' && <NoScreenshots />}
      <DocView doctype={doctype} name={name} />
    </ScrollView>
  );
}
