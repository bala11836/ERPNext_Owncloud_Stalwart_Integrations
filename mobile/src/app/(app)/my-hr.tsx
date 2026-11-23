import { Screen, Status } from '@/components/ui';
import { t as text } from '@/i18n';

// ponytail: placeholder until step 4 (leave, expense claims, payslips, holidays from Frappe HR's own app API).
export default function MyHr() {
  return (
    <Screen>
      <Status kind="info" label={text('myHr.soon')} />
    </Screen>
  );
}
