import { Stack, useLocalSearchParams } from 'expo-router';
import { ScrollView } from 'react-native';

import { DocView } from '@/components/doc-view';
import { NoScreenshots } from '@/components/no-screenshots';
import { WorkflowActions } from '@/components/workflow-actions';
import { useTheme } from '@/theme';

export default function DocScreen() {
  const t = useTheme();
  const { doctype, name, workflow } = useLocalSearchParams<{ doctype: string; name: string; workflow?: string }>();
  return (
    <ScrollView style={{ backgroundColor: t.c.bg }}>
      <Stack.Screen options={{ title: doctype }} />
      {/* Build guide section 9: no screenshots of payslips or of documents being approved. */}
      {(doctype === 'Salary Slip' || workflow === '1') && <NoScreenshots />}
      {/* Opened from Inbox: the workflow actions ERPNext allows this person, first. */}
      {workflow === '1' && <WorkflowActions doctype={doctype} name={name} />}
      <DocView doctype={doctype} name={name} />
    </ScrollView>
  );
}
