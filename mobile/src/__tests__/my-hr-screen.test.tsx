import type { ReactNode } from 'react';
import { Text } from 'react-native';
import { renderRouter, screen } from 'expo-router/testing-library';

import MyHr from '@/app/(app)/my-hr';
import { ThemeProvider } from '@/theme';

import { fakeErp, thrown } from './fake-erp';

const mockErp = fakeErp({
  'hrms.api.get_current_employee_info': { body: { message: { name: 'EMP-0001', employee_name: 'Worker A', designation: 'Engineer', department: 'Civil' } } },
  'hrms.api.get_leave_balance_map': { body: { message: { 'Casual Leave': { allocated_leaves: 10, balance_leaves: 5 } } } },
  'hrms.api.get_leave_applications': {
    body: { message: [{ name: 'HR-LAP-0001', leave_type: 'Casual Leave', from_date: '2026-12-01', to_date: '2026-12-02', status: 'Approved', total_leave_days: 2 }] },
  },
  'hrms.api.get_expense_claims': {
    body: { message: [{ name: 'HR-EXP-0001', posting_date: '2026-11-20', expense_type: 'Travel', approval_status: 'Draft', total_claimed_amount: 2500, currency: 'INR' }] },
  },
  'hrms.api.get_expense_claim_summary': { body: { message: { total_pending_amount: 2500, total_approved_amount: 150000, currency: 'INR' } } },
  'hrms.api.get_holidays_for_employee': { body: { message: [{ holiday_date: '2999-12-25', description: 'Christmas' }] } },
  'frappe.client.get_list': { status: 403, body: thrown('Not permitted') },
});
const mockApiRef = { current: mockErp.api };
jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useApiRef: () => mockApiRef }));
const mockPrevent = jest.fn();
jest.mock('expo-screen-capture', () => ({ usePreventScreenCapture: () => mockPrevent() }));

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;

describe('My HR screen', () => {
  it("shows the person's own HR data, money in Indian format, status in words", async () => {
    await renderRouter({ 'my-hr': MyHr, index: () => <Text>home</Text> }, { initialUrl: '/my-hr', wrapper });
    expect(await screen.findByText('Worker A')).toBeOnTheScreen();
    expect(screen.getByText('EMP-0001 · Engineer · Civil')).toBeOnTheScreen();
    expect(screen.getByText('5 left of 10')).toBeOnTheScreen();
    expect(screen.getByText('Casual Leave: 01-12-2026 – 02-12-2026')).toBeOnTheScreen();
    expect(screen.getByText('Approved')).toBeOnTheScreen();
    expect(screen.getByText('Waiting for approval: ₹2,500.00')).toBeOnTheScreen();
    expect(screen.getByText('Approved: ₹1,50,000.00')).toBeOnTheScreen();
    expect(screen.getByText('Travel: ₹2,500.00')).toBeOnTheScreen();
    expect(screen.getByText('25-12-2999')).toBeOnTheScreen();
    expect(screen.getByText("Couldn't load this part. Not permitted")).toBeOnTheScreen();
  });

  it('blocks screenshots while it is open', async () => {
    mockPrevent.mockClear();
    await renderRouter({ 'my-hr': MyHr, index: () => <Text>home</Text> }, { initialUrl: '/my-hr', wrapper });
    await screen.findByText('Worker A');
    expect(mockPrevent).toHaveBeenCalled();
  });
});
