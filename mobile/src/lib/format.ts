// Display formatting only: never used for arithmetic (CLAUDE.md rule 10).

/** Indian grouping: 150000 -> "₹1,50,000.00". */
export function formatINR(value: unknown): string {
  if (value === null || value === undefined || value === '') return '';
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return String(value);
  const [whole, paise] = Math.abs(n).toFixed(2).split('.');
  const last3 = whole.slice(-3);
  const rest = whole.slice(0, -3);
  const grouped = rest ? `${rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',')},${last3}` : last3;
  const negative = n < 0 && `${whole}.${paise}` !== '0.00';
  return `${negative ? '-' : ''}₹${grouped}.${paise}`;
}

/** An amount in its currency: Indian format for INR (or no currency given), else "USD 12.50" as sent. */
export function formatMoney(value: unknown, currency?: string | null): string {
  if (!currency || currency === 'INR') return formatINR(value);
  return value === null || value === undefined || value === '' ? '' : `${currency} ${String(value)}`;
}

/** Today's date on this phone as ERPNext writes dates ("2026-11-23"), not the UTC date. */
export function localToday(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** ERPNext "2026-11-08" / "2026-11-08 09:37:32.19" -> "08-11-2026" / "08-11-2026 09:37". */
export function formatDate(value: unknown, withTime = false): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?/.exec(String(value ?? ''));
  if (!m) return String(value ?? '');
  const date = `${m[3]}-${m[2]}-${m[1]}`;
  return withTime && m[4] ? `${date} ${m[4]}:${m[5]}` : date;
}

export type Field = { fieldname: string; fieldtype: string; label?: string; options?: string };

/** Field types never shown as values (layout, secrets, raw data). */
export const HIDDEN_TYPES = new Set([
  'Section Break', 'Column Break', 'Tab Break', 'HTML', 'Button', 'Image', 'Fold', 'Heading',
  'Password', 'Signature', 'Geolocation', 'JSON', 'Code', 'Barcode', 'Table MultiSelect',
]);

export function formatValue(field: Field, value: unknown): string {
  if (value === null || value === undefined || value === '') return '';
  switch (field.fieldtype) {
    case 'Currency':
      return formatINR(value);
    case 'Percent':
      return `${String(value)}%`;
    case 'Check':
      return value ? 'Yes' : 'No';
    case 'Date':
      return formatDate(value);
    case 'Datetime':
      return formatDate(value, true);
    case 'Text Editor':
    case 'HTML Editor':
    case 'Markdown Editor':
    case 'Small Text':
    case 'Long Text':
    case 'Text':
      return String(value).replace(/<[^>]*>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
    case 'Attach':
    case 'Attach Image':
      return 'Attachment';
    default:
      return String(value);
  }
}
