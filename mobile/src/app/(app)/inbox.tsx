import { Screen, Status } from '@/components/ui';
import { t as text } from '@/i18n';

// ponytail: placeholder until step 3 (approvals waiting for the person, notifications, unread count).
export default function Inbox() {
  return (
    <Screen>
      <Status kind="info" label={text('inbox.soon')} />
    </Screen>
  );
}
