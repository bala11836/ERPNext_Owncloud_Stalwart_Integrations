import type { ReactNode } from 'react';
import { Text } from 'react-native';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import Today from '@/app/(app)/index';
import { HR_API } from '@/lib/attendance';
import { ACTIONS_METHOD, LOGS_METHOD, byType, clearInbox } from '@/lib/inbox';
import { loadTodayHr } from '@/lib/my-hr';
import { memoryStore } from '@/lib/queue';
import { ThemeProvider } from '@/theme';

import { fakeErp } from './fake-erp';

const action = (n: string, doctype: string) => ({ name: n, reference_doctype: doctype, reference_name: n, workflow_state: 'Pending', creation: '2026-11-23 10:00:00' });
const answers = {
  [`${HR_API}.bootstrap`]: {
    body: { message: { sites: [{ name: 'S1', label: 'Site 1', supervisor: true, approver: false, shifts: [{ name: 'D', start: '00:00', end: '23:59', label: 'Day' }] }], check_in_sites: [{ name: 'S1', label: 'Site 1', shifts: [{ name: 'D', start: '00:00', end: '23:59', label: 'Day' }] }] } },
  },
  [`${HR_API}.my_attendance`]: { body: { message: [] } },
  [`${HR_API}.team`]: { body: { message: { total: 15, missing: 3 } } },
  [ACTIONS_METHOD]: { body: { message: [action('A', 'Purchase Order'), action('B', 'Leave Application'), action('C', 'Purchase Order')] } },
  [LOGS_METHOD]: {
    body: { message: { notification_logs: [{ name: 'N1', subject: 'x', read: 0, creation: '2026-11-23 10:00:00' }], user_info: {} } },
  },
  'hrms.api.get_current_employee_info': { body: { message: { name: 'EMP-0001' } } },
  'hrms.api.get_holidays_for_employee': {
    body: { message: [{ holiday_date: '2000-01-01', description: 'Past' }, { holiday_date: '2999-12-25', description: 'Christmas' }] },
  },
  'hrms.api.get_leave_applications': {
    body: { message: [{ name: 'L1', leave_type: 'Casual Leave', from_date: '2999-01-01', to_date: '2999-01-01', status: 'Open' }] },
  },
};
const mockErp = fakeErp(answers);
const mockApiRef = { current: mockErp.api };
jest.mock('@/auth/session', () => ({
  SignedOutError: class SignedOutError extends Error {},
  useAuth: () => ({ user: { name: 'Worker A', email: 'a@example.com', roles: [] } }),
  useApiRef: () => mockApiRef,
}));
const mockStore = memoryStore();
jest.mock('@/lib/offline-store', () => ({ offlineStore: async () => mockStore }));

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;
const app = { index: Today, inbox: () => <Text>Inbox screen</Text>, 'my-hr': () => <Text>My HR screen</Text> };

describe('Today, step T1', () => {
  beforeEach(async () => {
    clearInbox();
    await mockStore.clear();
  });

  it('shows what waits by document type, unread notifications and the HR card', async () => {
    await mockStore.put({ id: 'r', method: 'm', args: {}, createdAt: 1, attempts: 1, state: 'failed', error: 'refused' });
    await renderRouter(app, { initialUrl: '/', wrapper });
    expect(await screen.findByText('2 Purchase Order · 1 Leave Application')).toBeOnTheScreen();
    expect(screen.getByText('3')).toBeOnTheScreen();
    expect(screen.getByText('1 unread notifications')).toBeOnTheScreen();
    expect(await screen.findByText('Next holiday: 25-12-2999 Christmas')).toBeOnTheScreen();
    expect(screen.getByText('1 leave applications still open')).toBeOnTheScreen();
    expect(screen.getByText('1 not accepted by ERPNext: open them to see why')).toBeOnTheScreen();
  });

  it('the waiting card opens the Inbox', async () => {
    const router = await renderRouter(app, { initialUrl: '/', wrapper });
    await fireEvent.press(await screen.findByText('Waiting for you'));
    expect(await screen.findByText('Inbox screen')).toBeOnTheScreen();
    expect(router.getPathname()).toBe('/inbox');
  });
});

describe('Today helpers', () => {
  it('counts what waits by document type, most first, at most three', () => {
    expect(byType(['B', 'A', 'B', 'C', 'D', 'B', 'A'])).toBe('3 B · 2 A · 1 C');
    expect(byType([])).toBe('');
  });

  it('the HR card is null without an employee, and finds the next holiday and open leave', async () => {
    expect(await loadTodayHr(fakeErp({ 'hrms.api.get_current_employee_info': { body: {} } }).api, '2026-11-23')).toBeNull();
    expect(await loadTodayHr(fakeErp(answers).api, '2026-11-23')).toEqual({
      nextHoliday: { holiday_date: '2999-12-25', description: 'Christmas' },
      openLeaves: 1,
    });
  });
});

describe('Today, step T2', () => {
  beforeEach(() => clearInbox());

  it('puts the check-in status first, then the team card, then what waits', async () => {
    await renderRouter(app, { initialUrl: '/', wrapper });
    expect(await screen.findByText('Not checked in yet today')).toBeOnTheScreen();
    expect(screen.getByText('Team today at Site 1: 12 of 15 marked')).toBeOnTheScreen();
    await screen.findByText('Waiting for you');
    const order = ['Not checked in yet today', 'Team today at Site 1: 12 of 15 marked', 'Waiting for you'].map(
      (label) => screen.toJSON() && JSON.stringify(screen.toJSON()).indexOf(label),
    );
    expect([...order].sort((a, b) => Number(a) - Number(b))).toEqual(order);
  });
});
