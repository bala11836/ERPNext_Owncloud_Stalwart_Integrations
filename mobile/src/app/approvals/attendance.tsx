import { router, useLocalSearchParams } from 'expo-router';

import { AttendanceCards } from '@/components/attendance-cards';
import { finish } from '@/lib/approvals';

/** Phone: a site's attendance as cards; when the last one is done, the next Inbox item or back to the list. */
export default function AttendanceApprovalScreen() {
  const { site, mode } = useLocalSearchParams<{ site: string; mode?: 'approve' | 'verify' }>();
  const next = (message: string) => {
    const item = finish(`att:${mode === 'verify' ? 'verify' : 'approve'}:${site}`);
    if (item?.doc) router.replace({ pathname: '/approvals/[doctype]/[name]', params: { doctype: item.doc.doctype, name: item.doc.name, done: message } });
    else router.back();
  };
  return <AttendanceCards site={site} mode={mode === 'verify' ? 'verify' : 'approve'} onDone={next} />;
}
