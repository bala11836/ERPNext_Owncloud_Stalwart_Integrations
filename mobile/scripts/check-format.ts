// Fails (exit 1) if money / date display formatting breaks. Run: pnpm test
import { formatDate, formatINR, formatValue } from '../src/lib/format.ts';

const cases: [string, string][] = [
  [formatINR(150000), '₹1,50,000.00'],
  [formatINR(12345678.9), '₹1,23,45,678.90'],
  [formatINR(999), '₹999.00'],
  [formatINR(1000), '₹1,000.00'],
  [formatINR('250000.5'), '₹2,50,000.50'],
  [formatINR(0), '₹0.00'],
  [formatINR(-500.5), '-₹500.50'],
  [formatINR(-0.001), '₹0.00'],
  [formatINR(null), ''],
  [formatINR('abc'), 'abc'],
  [formatDate('2026-11-08'), '08-11-2026'],
  [formatDate('2026-11-08 09:37:32.191', true), '08-11-2026 09:37'],
  [formatValue({ fieldname: 'x', fieldtype: 'Check' }, 0), 'No'],
  [formatValue({ fieldname: 'x', fieldtype: 'Text Editor' }, '<p>Hello&nbsp;<b>site</b></p>'), 'Hello site'],
];

let failed = 0;
for (const [got, want] of cases) {
  if (got !== want) {
    failed++;
    console.log(`FAIL  got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
  }
}
console.log(`${cases.length - failed}/${cases.length} format checks passed`);
process.exit(failed ? 1 : 0);
