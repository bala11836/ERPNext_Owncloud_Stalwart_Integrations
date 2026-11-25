import {
  APPLY_METHOD,
  COMMENT_METHOD,
  ChangedError,
  MODIFIED_METHOD,
  ageOf,
  applyAction,
  arrange,
  docItem,
  finish,
  loadCard,
  setQueue,
  splitActions,
  waitingSince,
  type Item,
} from '@/lib/approvals';
import { memoryStore } from '@/lib/queue';

import { fakeErp } from '../../__tests__/fake-erp';

jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: jest.fn() }));
const mockStore = memoryStore();
jest.mock('@/lib/offline-store', () => ({ offlineStore: async () => mockStore }));

const NOW = new Date(2026, 10, 24, 12, 0).getTime();
const at = (minutesAgo: number) => {
  const d = new Date(NOW - minutesAgo * 60000);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:00`;
};
const item = (key: string, minutesAgo: number): Item => ({ key, area: 'other', title: key, detail: '', project: null, amount: null, created: at(minutesAgo) });

describe('ages (owner: amber after one day, red after two)', () => {
  it('labels and levels', () => {
    expect(ageOf(at(40), NOW)).toEqual({ label: '40 min', level: 'new' });
    expect(ageOf(at(180), NOW)).toEqual({ label: '3 h', level: 'new' });
    expect(ageOf(at(1500), NOW)).toEqual({ label: '1 day', level: 'amber' });
    expect(ageOf(at(3 * 1440), NOW)).toEqual({ label: '3 days', level: 'red' });
  });
  it('attendance waits from its check-in time, not from midnight of its day', () => {
    const evening = new Date(2026, 10, 25, 18, 7).getTime();
    const since = waitingSince([
      { attendance_date: '2026-11-25', check_in_time: '2026-11-25 18:09:00' },
      { attendance_date: '2026-11-25', check_in_time: '2026-11-25 16:09:12' },
    ]);
    expect(since).toBe('2026-11-25 16:09:12');
    expect(ageOf(since, evening).label).toBe('1 h');
    // No time (absent, or the verification list): the start of the day.
    expect(ageOf(waitingSince([{ attendance_date: '2026-11-25', check_in_time: null }]), evening).label).toBe('18 h');
  });
  it('longest waiting first, split at one day', () => {
    const { longest, newer } = arrange([item('a', 10), item('b', 3000), item('c', 200), item('d', 1600)], NOW);
    expect(longest.map((i) => i.key)).toEqual(['b', 'd']);
    expect(newer.map((i) => i.key)).toEqual(['c', 'a']);
  });
});

describe('the two big buttons follow whatever the workflow calls its actions', () => {
  it('approve / reject, the rest under More', () => {
    const split = splitActions([
      { action: 'Send Back', next_state: 'Draft' },
      { action: 'Approve', next_state: 'Approved' },
      { action: 'Reject', next_state: 'Rejected' },
    ]);
    expect(split.yes?.action).toBe('Approve');
    expect(split.no?.action).toBe('Send Back');
    expect(split.more.map((m) => m.action)).toEqual(['Reject']);
  });
  it('other names: Authorise and Hold', () => {
    const split = splitActions([{ action: 'Hold', next_state: 'On Hold' }, { action: 'Authorise', next_state: 'Authorised' }]);
    expect(split.yes?.action).toBe('Authorise');
    expect(split.no?.action).toBe('Hold');
  });
  it('only one action that is not a no: it is the main one', () => {
    expect(splitActions([{ action: 'Review', next_state: 'Reviewed' }]).yes?.action).toBe('Review');
  });
});

describe('list rows', () => {
  it('a payment: who, where, the amount in Indian format', () => {
    const row = docItem(
      { name: 'WA-1', reference_doctype: 'Payment Entry', reference_name: 'PE-0412', workflow_state: 'Pending Approval', creation: at(10) },
      { name: 'PE-0412', party_name: 'Supplier One', paid_amount: 452000, paid_from_account_currency: 'INR', payment_type: 'Pay', project: 'PROJ-A' },
    );
    expect(row).toMatchObject({ area: 'payments', title: 'Payment Entry · Supplier One', amount: '₹4,52,000.00', project: 'PROJ-A' });
    expect(row.detail).toBe('PE-0412 · Pay · Pending Approval');
  });
  it('an unknown workflow document still shows its type and name', () => {
    const row = docItem({ name: 'WA-2', reference_doctype: 'Quality Inspection', reference_name: 'QI-1', workflow_state: null, creation: at(5) }, undefined);
    expect(row).toMatchObject({ area: 'other', title: 'Quality Inspection', detail: 'QI-1', amount: null });
  });
  it('after an action the next item comes, else the one before', () => {
    setQueue([item('a', 1), item('b', 2), item('c', 3)]);
    expect(finish('b')?.key).toBe('c');
    expect(finish('c')?.key).toBe('a');
    expect(finish('a')).toBeNull();
  });
});

const META = {
  docs: [
    {
      name: 'Purchase Order',
      title_field: 'supplier_name',
      fields: [
        { fieldname: 'schedule_date', fieldtype: 'Date', label: 'Required By' },
        { fieldname: 'project', fieldtype: 'Link', label: 'Project' },
        { fieldname: 'total_taxes_and_charges', fieldtype: 'Currency', label: 'Total Taxes and Charges' },
        { fieldname: 'items', fieldtype: 'Table', label: 'Items', options: 'Purchase Order Item' },
      ],
    },
  ],
};
const PO = {
  name: 'PO-0233',
  doctype: 'Purchase Order',
  supplier_name: 'Supplier Two',
  grand_total: 118450,
  currency: 'INR',
  schedule_date: '2026-11-28',
  project: 'PROJ-C',
  total_taxes_and_charges: 12450,
  workflow_state: 'Pending Approval',
  modified: '2026-11-24 09:00:00.000001',
  items: [
    { item_name: 'Cement 53 grade', qty: 200, uom: 'Bag', rate: 385, amount: 77000, last_purchase_rate: 370, supplier_quotation: 'SQ-0007', material_request: 'MR-0518' },
    { item_name: 'River sand', qty: 10, uom: 'Cu Meter', rate: 2900, amount: 29000, last_purchase_rate: 3000 },
  ],
};
const serveCard = (extra: Record<string, { body: unknown }> = {}) =>
  fakeErp({
    'frappe.desk.form.load.getdoctype': { body: META },
    'frappe.desk.form.load.getdoc': {
      body: {
        docs: [PO],
        docinfo: {
          attachments: [{ name: 'F1', file_name: 'quote.pdf', file_url: '/private/files/quote.pdf' }],
          workflow_logs: [{ content: 'Pending Approval', owner: 'buyer@example.com', creation: '2026-11-23 10:00:00' }],
          user_info: { 'buyer@example.com': { fullname: 'Buyer B' } },
        },
      },
    },
    ...extra,
  });

describe('the card', () => {
  it('a purchase order: amount, supplier and site, facts, item lines and warnings from ERPNext data', async () => {
    const card = await loadCard(serveCard().api, 'Purchase Order', 'PO-0233');
    expect(card.headline).toBe('₹1,18,450.00');
    expect(card.party).toBe('Supplier Two');
    expect(card.project).toBe('PROJ-C');
    expect(card.facts).toEqual([
      { label: 'Required By', value: '28-11-2026' },
      { label: 'Project', value: 'PROJ-C' },
      { label: 'Total Taxes and Charges', value: '₹12,450.00' },
    ]);
    expect(card.lines[0]).toEqual({ title: 'Cement 53 grade', detail: '200 Bag × ₹385.00', amount: '₹77,000.00' });
    expect(card.flags.map((f) => f.label)).toEqual([
      'Cement 53 grade: rate 4% above the last purchase (₹370.00)',
      'From supplier quotation SQ-0007',
      'From material request MR-0518',
    ]);
    expect(card.steps).toEqual([{ state: 'Pending Approval', by: 'Buyer B', at: '2026-11-23 10:00:00' }]);
    expect(card.attachments).toEqual([{ name: 'F1', fileName: 'quote.pdf', url: '/private/files/quote.pdf', image: false }]);
  });

  it('changed after it was opened: nothing is applied', async () => {
    const erp = serveCard({ [MODIFIED_METHOD]: { body: { message: { modified: '2026-11-24 09:30:00.000001' } } } });
    const card = await loadCard(erp.api, 'Purchase Order', 'PO-0233');
    await expect(applyAction(erp.api, card, 'Approve', '', {})).rejects.toBeInstanceOf(ChangedError);
    expect(erp.calls.some((c) => c.method === APPLY_METHOD)).toBe(false);
  });

  it('a reason goes in as a comment after the action', async () => {
    const erp = serveCard({
      [MODIFIED_METHOD]: { body: { message: { modified: PO.modified } } },
      [APPLY_METHOD]: { body: { message: { name: 'PO-0233' } } },
      [COMMENT_METHOD]: { body: { message: {} } },
    });
    const card = await loadCard(erp.api, 'Purchase Order', 'PO-0233');
    await applyAction(erp.api, card, 'Reject', 'Rate too high', { email: 'pm@example.com', name: 'PM' });
    const methods = erp.calls.filter((c) => c.post).map((c) => c.method);
    expect(methods).toEqual([APPLY_METHOD, COMMENT_METHOD]);
    expect(erp.calls.find((c) => c.method === COMMENT_METHOD)?.args).toMatchObject({ reference_name: 'PO-0233', content: 'Reject: Rate too high' });
  });
});
