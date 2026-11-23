import { t } from '@/i18n';

describe('texts', () => {
  it('fills placeholders and leaves unknown ones visible', () => {
    expect(t('erp.failed', { status: 503 })).toBe('ERPNext error (503). Try again.');
    expect(t('erp.failed')).toBe('ERPNext error ({status}). Try again.');
  });
});
