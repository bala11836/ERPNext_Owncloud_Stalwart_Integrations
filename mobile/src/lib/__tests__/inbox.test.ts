import { fakeErp } from '@/__tests__/fake-erp';
import { ACTIONS_METHOD, LOGS_METHOD, MARK_READ_METHOD, clearInbox, markRead, refreshInbox, unreadCount } from '@/lib/inbox';

jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: jest.fn() }));

const action = { name: 'WA-1', reference_doctype: 'Purchase Order', reference_name: 'PO-0001', workflow_state: 'Pending', creation: '2026-11-23 10:00:00' };
const unread = { name: 'NL-1', subject: '<b>PO-0001</b> needs approval', document_type: 'Purchase Order', document_name: 'PO-0001', read: 0, creation: '2026-11-23 10:01:00' };
const read = { ...unread, name: 'NL-2', read: 1 };

const erp = () =>
  fakeErp({
    [ACTIONS_METHOD]: { body: { message: [action] } },
    [LOGS_METHOD]: { body: { message: { notification_logs: [unread, read], user_info: {} } } },
    [MARK_READ_METHOD]: { body: { message: null } },
  });

describe('inbox data', () => {
  afterEach(() => clearInbox());

  it('asks ERPNext for open Workflow Actions and the last 50 notifications', async () => {
    const { api, calls } = erp();
    await refreshInbox(api);
    const list = calls.find((c) => c.method === ACTIONS_METHOD)!;
    expect(list.args.doctype).toBe('Workflow Action');
    expect(JSON.parse(String(list.args.filters))).toEqual({ status: 'Open' });
    expect(calls.find((c) => c.method === LOGS_METHOD)!.args.limit).toBe('50');
  });

  it('counts approvals waiting plus unread notifications', () => {
    expect(unreadCount({ actions: [action], notifications: [unread, read] })).toBe(2);
    expect(unreadCount({ actions: [], notifications: [read] })).toBe(0);
  });

  it('marks a notification read on the server (POST, by name)', async () => {
    const { api, calls } = erp();
    await refreshInbox(api);
    await markRead(api, 'NL-1');
    expect(calls.at(-1)).toEqual({ method: MARK_READ_METHOD, args: { docname: 'NL-1' }, post: true });
  });
});
