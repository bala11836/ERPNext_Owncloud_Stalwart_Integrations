import { Stack, router, useLocalSearchParams } from 'expo-router';

import { ApprovalCard } from '@/components/approval-card';
import { finish } from '@/lib/approvals';
import { refreshInbox } from '@/lib/inbox';
import { useApiRef } from '@/auth/session';

/** Phone: one approval card; after an action the next item of the Inbox's list slides in, or back to the list. */
export default function ApprovalScreen() {
  const apiRef = useApiRef();
  const { doctype, name, done } = useLocalSearchParams<{ doctype: string; name: string; done?: string }>();
  const next = (message: string) => {
    refreshInbox(apiRef.current);
    const item = finish(`doc:${doctype}:${name}`);
    if (item?.doc) router.replace({ pathname: '/approvals/[doctype]/[name]', params: { doctype: item.doc.doctype, name: item.doc.name, done: message } });
    else if (item?.attendance) router.replace({ pathname: '/approvals/attendance', params: { site: item.attendance.site, mode: item.attendance.mode } });
    else router.back();
  };
  return (
    <>
      <Stack.Screen options={{ title: doctype }} />
      <ApprovalCard key={`${doctype}/${name}`} doctype={doctype} name={name} done={done} onDone={next} />
    </>
  );
}
