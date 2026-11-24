import type { ReactNode } from 'react';
import { Text } from 'react-native';
import { router as nav } from 'expo-router';
import { act, fireEvent, renderRouter, screen, within } from 'expo-router/testing-library';

import Inbox from '@/app/(app)/inbox';
import ApprovalScreen from '@/app/approvals/[doctype]/[name]';
import AttendanceApprovalScreen from '@/app/approvals/attendance';
import DocScreen from '@/app/doc/[doctype]/[name]';
import { APPLY_METHOD, COMMENT_METHOD, MODIFIED_METHOD, TRANSITIONS_METHOD, clearApprovalCache } from '@/lib/approvals';
import { HR_API } from '@/lib/attendance';
import { clearErpCache } from '@/lib/erp';
import { LOGS_METHOD, MARK_READ_METHOD, clearInbox } from '@/lib/inbox';
import { memoryStore } from '@/lib/queue';
import { resetConnection } from '@/lib/saved';
import { ThemeProvider } from '@/theme';

import { type Answer, fakeErp, thrown } from './fake-erp';

let mockErp = fakeErp({});
let mockDown = false; // no connection: every call fails as fetch does offline
const mockApiRef = {
  current: async (...a: Parameters<ReturnType<typeof fakeErp>['api']>) => {
    if (mockDown) throw new TypeError('Network request failed');
    return mockErp.api(...a);
  },
};
const mockAuth = { api: (...a: Parameters<ReturnType<typeof fakeErp>['api']>) => mockApiRef.current(...a), user: { name: 'PM One', email: 'pm@example.com', roles: [] } };
jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: () => mockAuth, useApiRef: () => mockApiRef }));
let mockConfirmed = true;
const mockConfirm = jest.fn(async (_reason: string) => mockConfirmed);
jest.mock('@/auth/confirm', () => ({ confirmIdentity: (reason: string) => mockConfirm(reason) }));
jest.mock('@/components/doc-view', () => ({ DocView: () => null }));
jest.mock('expo-screen-capture', () => ({
  usePreventScreenCapture: () => {},
  enableAppSwitcherProtectionAsync: async () => {},
  disableAppSwitcherProtectionAsync: async () => {},
}));
jest.mock('@/components/private-image', () => {
  const { createElement } = jest.requireActual('react');
  const { Text } = jest.requireActual('react-native');
  return { PrivateImage: ({ path }: { path: string }) => createElement(Text, null, `photo ${path}`) };
});
const mockStore = memoryStore();
jest.mock('@/lib/offline-store', () => ({ offlineStore: async () => mockStore }));
let mockWidth = 400;
jest.mock('react-native/Libraries/Utilities/useWindowDimensions', () => ({
  __esModule: true,
  default: () => ({ width: mockWidth, height: 800, scale: 2, fontScale: 1 }),
}));

const ago = (minutes: number) => {
  const d = new Date(Date.now() - minutes * 60000);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:00`;
};
const actions = [
  { name: 'WA-1', reference_doctype: 'Payment Entry', reference_name: 'PE-0412', workflow_state: 'Pending Approval', creation: ago(3000) },
  { name: 'WA-2', reference_doctype: 'Purchase Order', reference_name: 'PO-0233', workflow_state: 'Pending Approval', creation: ago(1500) },
  { name: 'WA-3', reference_doctype: 'Leave Application', reference_name: 'LA-1', workflow_state: 'Open', creation: ago(120) },
  { name: 'WA-4', reference_doctype: 'Leave Application', reference_name: 'LA-2', workflow_state: 'Open', creation: ago(60) },
];
const note = { name: 'NL-1', subject: '<b>PO-0233</b> was updated', document_type: 'Purchase Order', document_name: 'PO-0233', read: 0, creation: '2026-11-23 10:01:00' };
const meta = (name: string, fields: { fieldname: string; fieldtype: string; label: string }[]) => ({ docs: [{ name, fields }] });
const PE = {
  name: 'PE-0412',
  doctype: 'Payment Entry',
  party_name: 'Supplier One',
  paid_amount: 452000,
  paid_from_account_currency: 'INR',
  mode_of_payment: 'Bank Transfer',
  project: 'PROJ-A',
  workflow_state: 'Pending Approval',
  modified: '2026-11-24 08:00:00.1',
  references: [
    { reference_doctype: 'Purchase Invoice', reference_name: 'PI-0981', allocated_amount: 310000 },
    { reference_doctype: 'Purchase Invoice', reference_name: 'PI-0990', allocated_amount: 142000 },
  ],
};
const LEAVE = (name: string) => ({ name, doctype: 'Leave Application', employee: 'EMP-1', employee_name: 'Worker Nine', leave_type: 'Casual Leave', from_date: '2026-11-26', to_date: '2026-11-28', total_leave_days: 3, department: 'Civil', workflow_state: 'Open', modified: 'm1' });
const PO = { name: 'PO-0233', doctype: 'Purchase Order', supplier_name: 'Supplier Two', grand_total: 118450, currency: 'INR', workflow_state: 'Pending Approval', modified: 'm2', items: [] };
const DOCS: Record<string, unknown> = { 'PE-0412': PE, 'PO-0233': PO, 'LA-1': LEAVE('LA-1'), 'LA-2': LEAVE('LA-2') };
const BOOT = {
  sites: [{ name: 'S1', label: 'Site A', project: 'PROJ-A', project_name: 'Tower A', supervisor: false, approver: true, verifier: false, shifts: [] }],
  check_in_sites: [],
};
const ENTRIES = [
  { name: 'A1', employee: 'E1', employee_name: 'Mason One', attendance_date: '2026-11-24', shift: 'Morning', attendance_status: 'Present', entry_type: 'Team', check_in_time: '2026-11-24 08:02:00', accuracy_m: 8, can_review: true },
  { name: 'A2', employee: 'E2', employee_name: 'Helper Two', attendance_date: '2026-11-24', shift: 'Morning', attendance_status: 'Present', entry_type: 'Team', captured_offline: 1, can_review: true },
];

function serve(over: Record<string, Answer | ((args: Record<string, unknown>) => Answer)> = {}) {
  mockErp = fakeErp({
    'frappe.client.get_list': (args) => {
      if (args.doctype === 'Workflow Action') return { body: { message: actions } };
      if (args.doctype === 'Payment Entry') return { body: { message: [{ name: 'PE-0412', party_name: 'Supplier One', paid_amount: 452000, paid_from_account_currency: 'INR', payment_type: 'Pay', project: 'PROJ-A' }] } };
      if (args.doctype === 'Purchase Order') return { body: { message: [{ name: 'PO-0233', supplier_name: 'Supplier Two', grand_total: 118450, currency: 'INR', project: 'PROJ-C' }] } };
      if (args.doctype === 'Leave Application' && String(args.fields).includes('employee_name'))
        return { body: { message: ['LA-1', 'LA-2'].map((n) => ({ name: n, employee_name: 'Worker Nine', leave_type: 'Casual Leave', from_date: '2026-11-26', to_date: '2026-11-28' })) } };
      if (args.doctype === 'Leave Application') return { body: { message: [{ name: 'LA-9' }] } };
      return { body: { message: [] } };
    },
    [LOGS_METHOD]: { body: { message: { notification_logs: [note] } } },
    [MARK_READ_METHOD]: { body: { message: null } },
    [`${HR_API}.bootstrap`]: { body: { message: BOOT } },
    [`${HR_API}.approvals`]: { body: { message: ENTRIES } },
    [`${HR_API}.entry`]: (args) => ({ body: { message: { name: args.name, photo: `/private/files/${String(args.name)}.jpg` } } }),
    [`${HR_API}.review_many`]: (args) => ({ body: { message: (args.names as string[]).map((n) => ({ name: n, ok: true })) } }),
    'frappe.desk.form.load.getdoctype': (args) =>
      args.doctype === 'Payment Entry'
        ? { body: meta('Payment Entry', [{ fieldname: 'mode_of_payment', fieldtype: 'Link', label: 'Mode of Payment' }, { fieldname: 'project', fieldtype: 'Link', label: 'Project' }]) }
        : { body: meta('Leave Application', [{ fieldname: 'leave_type', fieldtype: 'Link', label: 'Leave Type' }, { fieldname: 'total_leave_days', fieldtype: 'Float', label: 'Total Leave Days' }]) },
    'frappe.desk.form.load.getdoc': (args) => ({
      body: {
        docs: [DOCS[String(args.name)]],
        docinfo: {
          attachments: [{ name: 'F1', file_name: 'bill-0981.jpg', file_url: '/private/files/bill-0981.jpg' }],
          workflow_logs: [{ content: 'Pending Approval', owner: 'acc@example.com', creation: '2026-11-23 10:00:00' }],
          user_info: { 'acc@example.com': { fullname: 'Accounts A' } },
        },
      },
    }),
    'hrms.hr.doctype.leave_application.leave_application.get_leave_balance_on': { body: { message: 5 } },
    [TRANSITIONS_METHOD]: { body: { message: [{ action: 'Approve', next_state: 'Approved' }, { action: 'Reject', next_state: 'Rejected' }, { action: 'Send Back', next_state: 'Draft' }] } },
    [MODIFIED_METHOD]: (args) => ({ body: { message: { modified: (DOCS[String(args.filters)] as { modified: string }).modified } } }),
    [APPLY_METHOD]: (args) => ({ body: { message: { name: (args.doc as { name: string }).name } } }),
    [COMMENT_METHOD]: { body: { message: {} } },
    ...over,
  });
  return mockErp.calls;
}

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;
const app = {
  '(app)/inbox': Inbox,
  'approvals/[doctype]/[name]': ApprovalScreen,
  'approvals/attendance': AttendanceApprovalScreen,
  'doc/[doctype]/[name]': DocScreen,
  index: () => <Text>home</Text>,
};
const openInbox = () => renderRouter(app, { initialUrl: '/inbox', wrapper });
const applied = () => mockErp.calls.filter((c) => c.method === APPLY_METHOD);

describe('approvals inbox', () => {
  beforeEach(async () => {
    clearInbox();
    clearErpCache();
    clearApprovalCache();
    resetConnection();
    await mockStore.clear();
    mockDown = false;
    mockWidth = 400;
    mockConfirmed = true;
    mockConfirm.mockClear();
  });

  it('every approval across all sites, longest waiting first, with area counts, amounts and ages', async () => {
    serve();
    await openInbox();
    expect(await screen.findByText('Payment Entry · Supplier One')).toBeOnTheScreen();
    expect(screen.getByText('₹4,52,000.00')).toBeOnTheScreen();
    expect(screen.getByText('2 days')).toBeOnTheScreen(); // red after two days
    expect(screen.getByText('1 day')).toBeOnTheScreen(); // amber after one
    expect(screen.getByText('WAITING LONGEST')).toBeOnTheScreen();
    expect(await screen.findByText('Attendance · 2 entries')).toBeOnTheScreen();
    expect(screen.getByText('Site A · 1 to check closely')).toBeOnTheScreen();
    expect(screen.getByText('All 5')).toBeOnTheScreen();
    expect(screen.getByText('Payments 1')).toBeOnTheScreen();
    expect(screen.getByText('HR 2')).toBeOnTheScreen();
    expect(screen.getByText('PO-0233 was updated')).toBeOnTheScreen(); // notifications stay below
  });

  it('filters by area and by site', async () => {
    serve();
    await openInbox();
    await screen.findByText('Attendance · 2 entries');
    await fireEvent.press(screen.getByText('HR 2'));
    expect(screen.queryByText('Payment Entry · Supplier One')).toBeNull();
    expect(screen.getAllByText('Leave Application · Worker Nine')).toHaveLength(2);
    await fireEvent.press(screen.getByText('All 5'));
    await fireEvent.press(screen.getByRole('button', { name: 'Site: All sites. Change' }));
    await fireEvent.press(await screen.findByText('Tower A'));
    expect(screen.getByText('Payment Entry · Supplier One')).toBeOnTheScreen();
    expect(screen.getByText('Attendance · 2 entries')).toBeOnTheScreen();
    expect(screen.queryByText('Purchase Order · Supplier Two')).toBeNull();
  });

  it('a payment card: amount, who and where, steps, facts, documents against it; Approve with Face ID', async () => {
    serve();
    const router = await openInbox();
    await fireEvent.press(await screen.findByText('Payment Entry · Supplier One'));
    expect(router.getPathname()).toBe('/approvals/Payment Entry/PE-0412');
    expect(await screen.findByText('₹4,52,000.00')).toBeOnTheScreen();
    expect(screen.getByText('Supplier One · PROJ-A')).toBeOnTheScreen();
    expect(screen.getByText('You: Pending Approval')).toBeOnTheScreen();
    expect(screen.getByText('Bank Transfer')).toBeOnTheScreen();
    expect(screen.getByText('Purchase Invoice · PI-0981')).toBeOnTheScreen();
    expect(screen.getByText('Against 2 documents (listed below)')).toBeOnTheScreen();
    expect(screen.getByText('Pending Approval · by Accounts A · 23-11-2026 10:00')).toBeOnTheScreen();
    expect(screen.getByText('1 of 5')).toBeOnTheScreen();

    await fireEvent.press(await screen.findByRole('button', { name: 'Approve' }));
    expect(mockConfirm).toHaveBeenCalledWith('Confirm Approve for PE-0412');
    expect(applied()[0].args).toEqual({ doc: { doctype: 'Payment Entry', name: 'PE-0412' }, action: 'Approve' });
    // The next item slides in, with what happened to this one.
    expect(await screen.findByText('Approve done for PE-0412. Now: Approved.')).toBeOnTheScreen();
    expect(router.getPathname()).toBe('/approvals/Purchase Order/PO-0233');
  });

  it('a no-action needs a reason, which goes to ERPNext as a comment', async () => {
    serve();
    await openInbox();
    await fireEvent.press(await screen.findByText('Payment Entry · Supplier One'));
    await fireEvent.press(await screen.findByRole('button', { name: 'Reject' }));
    const reason = screen.getByLabelText('Reason (the sender sees it)');
    expect(screen.getByRole('button', { name: 'Reject with this reason' })).toBeDisabled();
    await fireEvent.changeText(reason, 'Attach the second bill');
    await fireEvent.press(screen.getByRole('button', { name: 'Reject with this reason' }));
    expect(applied()[0].args).toMatchObject({ action: 'Reject' });
    expect(mockErp.calls.find((c) => c.method === COMMENT_METHOD)?.args).toMatchObject({ reference_name: 'PE-0412', content: 'Reject: Attach the second bill', comment_email: 'pm@example.com' });
  });

  it('other actions are under More', async () => {
    serve();
    await openInbox();
    await fireEvent.press(await screen.findByText('Payment Entry · Supplier One'));
    await fireEvent.press(await screen.findByRole('button', { name: 'More: Send Back' }));
    expect(await screen.findByText('Then: Draft')).toBeOnTheScreen();
  });

  it('nothing is sent when Face ID is not confirmed', async () => {
    serve();
    mockConfirmed = false;
    await openInbox();
    await fireEvent.press(await screen.findByText('Payment Entry · Supplier One'));
    await fireEvent.press(await screen.findByRole('button', { name: 'Approve' }));
    expect(await screen.findByText('Not confirmed. Nothing was changed.')).toBeOnTheScreen();
    expect(applied()).toHaveLength(0);
  });

  it("changed since it was opened: nothing is sent and the new version shows; ERPNext's refusal shown as given", async () => {
    serve({ [MODIFIED_METHOD]: { body: { message: { modified: 'newer' } } } });
    await openInbox();
    await fireEvent.press(await screen.findByText('Payment Entry · Supplier One'));
    await fireEvent.press(await screen.findByRole('button', { name: 'Approve' }));
    expect(await screen.findByText(/was changed after you opened it/)).toBeOnTheScreen();
    expect(applied()).toHaveLength(0);

    serve({ [APPLY_METHOD]: { status: 417, body: thrown('Self approval is not allowed') } });
    await fireEvent.press(await screen.findByRole('button', { name: 'Approve' }));
    expect(await screen.findByText('Self approval is not allowed')).toBeOnTheScreen();
  });

  it('offline: the card is read from the saved copy and deciding waits for a connection', async () => {
    serve();
    await openInbox();
    await fireEvent.press(await screen.findByText('Payment Entry · Supplier One'));
    await screen.findByText('Bank Transfer');
    await act(async () => nav.back());
    mockDown = true;
    await fireEvent.press(await screen.findByText('Payment Entry · Supplier One'));
    expect(await screen.findByText('Bank Transfer')).toBeOnTheScreen();
    expect(screen.getByText(/Deciding needs internet/)).toBeOnTheScreen();
  });

  it('leave: balance and others on leave; Approve all with one Face ID (never for money)', async () => {
    serve();
    await openInbox();
    await fireEvent.press(await screen.findAllByText('Leave Application · Worker Nine').then((l) => l[0]));
    expect(await screen.findByText('3 days · 26-11-2026 – 28-11-2026')).toBeOnTheScreen();
    expect(await screen.findByText('5 days now, 2 after this')).toBeOnTheScreen();
    expect(screen.getByText('1 others in the department on leave')).toBeOnTheScreen();
    await fireEvent.press(screen.getByRole('button', { name: 'Approve all 2 with one Face ID' }));
    expect(mockConfirm).toHaveBeenCalledTimes(1);
    expect(applied().map((c) => (c.args.doc as { name: string }).name)).toEqual(['LA-1', 'LA-2']);
  });

  it('a payment card has no Approve all', async () => {
    serve();
    await openInbox();
    await fireEvent.press(await screen.findByText('Payment Entry · Supplier One'));
    await screen.findByRole('button', { name: 'Approve' });
    expect(screen.queryByText(/Approve all/)).toBeNull();
  });

  it('attendance: one worker at a time, exceptions first, with the photo; approve one, then all', async () => {
    serve();
    await openInbox();
    await fireEvent.press(await screen.findByText('Attendance · 2 entries'));
    expect(await screen.findByText('Helper Two')).toBeOnTheScreen(); // captured offline: first
    expect(await screen.findByText('photo /private/files/A2.jpg')).toBeOnTheScreen();
    expect(screen.getByText(/Captured offline/)).toBeOnTheScreen();
    await fireEvent.press(screen.getByRole('button', { name: 'Approve' }));
    const first = mockErp.calls.find((c) => c.method === `${HR_API}.review_many`);
    expect(first?.args).toMatchObject({ names: ['A2'], decision: 'Approve' });
    expect(await screen.findByText('Mason One')).toBeOnTheScreen();
  });

  it('tablet, landscape: the list, the card and the attachments side by side', async () => {
    mockWidth = 1280;
    serve();
    await openInbox();
    expect(await screen.findByText('Payment Entry · Supplier One')).toBeOnTheScreen();
    // The longest waiting opens at once on the right.
    expect(await screen.findByText('Bank Transfer')).toBeOnTheScreen();
    expect(screen.getByText('Attached (1)')).toBeOnTheScreen();
    await fireEvent.press(screen.getAllByText('Leave Application · Worker Nine')[0]);
    expect(await screen.findByText('5 days now, 2 after this')).toBeOnTheScreen();
  });

  it('opening a notification marks it read and opens its document', async () => {
    const calls = serve();
    const router = await openInbox();
    await fireEvent.press(await screen.findByText('PO-0233 was updated'));
    expect(calls.some((c) => c.method === MARK_READ_METHOD && c.post && c.args.docname === 'NL-1')).toBe(true);
    expect(router.getPathname()).toBe('/doc/Purchase Order/PO-0233');
  });

  it('the attachment opens in the app when it is a picture', async () => {
    serve();
    await openInbox();
    await fireEvent.press(await screen.findByText('Payment Entry · Supplier One'));
    const box = await screen.findByText('bill-0981.jpg');
    await fireEvent.press(box);
    expect(await screen.findByText('photo /private/files/bill-0981.jpg')).toBeOnTheScreen();
    expect(within(screen.getByText('Attached (1)').parent!.parent!).getByText('Hide')).toBeOnTheScreen();
  });
});
