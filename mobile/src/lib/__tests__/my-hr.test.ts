import { fakeErp, thrown } from '@/__tests__/fake-erp';
import { formatMoney, localToday } from '@/lib/format';
import { loadMyHr, statusKind } from '@/lib/my-hr';

jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: jest.fn() }));

const employee = { name: 'EMP-0001', employee_name: 'Worker A', designation: 'Engineer', department: 'Civil', company: 'Company 1' };
const hr = (over: Record<string, unknown> = {}) =>
  fakeErp({
    'hrms.api.get_current_employee_info': { body: { message: employee } },
    'hrms.api.get_leave_balance_map': { body: { message: { 'Casual Leave': { allocated_leaves: 10, balance_leaves: 5 } } } },
    'hrms.api.get_leave_applications': { body: { message: [] } },
    'hrms.api.get_expense_claims': { body: { message: [] } },
    'hrms.api.get_expense_claim_summary': { body: { message: { total_pending_amount: 150000, total_approved_amount: 0, total_rejected_amount: 0, currency: 'INR' } } },
    'hrms.api.get_holidays_for_employee': {
      body: { message: [{ holiday_date: '2026-11-01', description: 'Past' }, { holiday_date: '2026-12-25', description: 'Christmas' }] },
    },
    'frappe.client.get_list': { status: 403, body: thrown('Not permitted') },
    ...over,
  });

describe('My HR data', () => {
  it('finds the employee first and asks for their own records', async () => {
    const { api, calls } = hr();
    const data = await loadMyHr(api, '2026-11-23');
    expect(data?.employee?.name).toBe('EMP-0001');
    const leaves = calls.find((c) => c.method === 'hrms.api.get_leave_applications')!;
    expect(leaves.args).toEqual({ employee: 'EMP-0001', limit: '10' });
    const slips = calls.find((c) => c.method === 'frappe.client.get_list')!;
    expect(JSON.parse(String(slips.args.filters))).toEqual({ employee: 'EMP-0001', docstatus: 1 });
  });

  it('shows only upcoming holidays', async () => {
    const data = await loadMyHr(hr().api, '2026-11-23');
    expect(data && 'data' in data.holidays && data.holidays.data.map((h) => h.description)).toEqual(['Christmas']);
  });

  it('one refused part (payslips) does not hide the others', async () => {
    const data = await loadMyHr(hr().api, '2026-11-23');
    expect(data?.slips).toEqual({ error: 'Not permitted' });
    expect(data && 'data' in data.balances).toBe(true);
  });

  it('a sign-in without an employee gives null, and asks nothing else', async () => {
    // Frappe sends {} when the function returns None (handler.py adds "message" only for a value).
    for (const body of [{}, { message: null }]) {
      const { api, calls } = hr({ 'hrms.api.get_current_employee_info': { body } });
      expect(await loadMyHr(api, '2026-11-23')).toBeNull();
      expect(calls).toHaveLength(1);
    }
  });

  it('never uses an answer of the wrong shape', async () => {
    const { api } = hr({ 'hrms.api.get_leave_balance_map': { body: { message: { 'Casual Leave': { balance_leaves: 'five' } } } } });
    const data = await loadMyHr(api, '2026-11-23');
    expect(data?.balances).toEqual({ error: expect.stringContaining('does not understand') });
  });
});

describe('display helpers', () => {
  it('maps ERPNext status words to icons', () => {
    expect(['Approved', 'Paid', 'Rejected', 'Cancelled', 'Open', 'Draft', null].map(statusKind)).toEqual(
      ['ok', 'ok', 'danger', 'danger', 'pending', 'pending', 'info'],
    );
  });

  it('shows amounts in Indian format for INR and as sent otherwise', () => {
    expect(formatMoney(150000, 'INR')).toBe('₹1,50,000.00');
    expect(formatMoney('2500.5', null)).toBe('₹2,500.50');
    expect(formatMoney(12.5, 'USD')).toBe('USD 12.5');
  });

  it("uses the phone's own date, not the UTC date", () => {
    expect(localToday(new Date(2026, 10, 23, 0, 30))).toBe('2026-11-23');
    expect(localToday(new Date(2026, 0, 5, 23, 59))).toBe('2026-01-05');
  });
});
