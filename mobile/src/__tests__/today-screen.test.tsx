import type { ReactNode } from 'react';
import { Text } from 'react-native';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import Today from '@/app/(app)/index';
import { HR_API } from '@/lib/attendance';
import { ACTIONS_METHOD, LOGS_METHOD, byType, clearInbox } from '@/lib/inbox';
import { loadTodayHr } from '@/lib/my-hr';
import { choosePlace } from '@/lib/places';
import { memoryStore } from '@/lib/queue';
import { ThemeProvider } from '@/theme';

import { type Answer, fakeErp } from './fake-erp';

const day = { name: 'Day1', start: '00:00', end: '23:59', label: 'Day' };
const night = { name: 'Night1', start: '23:59', end: '00:00', label: 'Night' };
const action = (n: string, doctype: string) => ({ name: n, reference_doctype: doctype, reference_name: n, workflow_state: 'Pending', creation: '2026-11-23 10:00:00' });
const states = [...Array(8).fill('Submitted'), 'Approved', 'Draft', 'Draft', 'Returned', 'Not recorded', 'Not recorded', 'Not recorded'];
const answers: Record<string, Answer | ((args: Record<string, unknown>) => Answer)> = {
  [`${HR_API}.bootstrap`]: {
    body: {
      message: {
        sites: [
          { name: 'S1', label: 'Site 1', project: 'P1', project_name: 'Project 1', supervisor: true, approver: true, shifts: [day, night] },
          { name: 'S3', label: 'Site 3', project: 'P1', project_name: 'Project 1', supervisor: true, approver: false, shifts: [day] },
        ],
        check_in_sites: [{ name: 'S1', label: 'Site 1', project: 'P1', shifts: [day, night] }],
      },
    },
  },
  [`${HR_API}.my_attendance`]: { body: { message: [] } },
  [`${HR_API}.team`]: (args) =>
    args.site === 'S3'
      ? { body: { message: { total: 4, missing: 4, workers: Array(4).fill({ state: 'Not recorded' }) } } }
      : { body: { message: { total: 15, missing: 6, workers: states.map((state, i) => ({ state, can_edit: state === 'Draft', entry: state === 'Draft' ? `E${i}` : null })) } } },
  [`${HR_API}.approvals`]: {
    body: {
      message: [
        { name: 'P1', captured_offline: 1, attendance_status: 'Present', can_review: true },
        { name: 'P2', captured_offline: 0, attendance_status: 'Absent', can_review: true },
        { name: 'P3', captured_offline: 0, attendance_status: 'Present', can_review: false },
      ],
    },
  },
  [ACTIONS_METHOD]: { body: { message: [action('A', 'Purchase Order'), action('B', 'Leave Application'), action('C', 'Purchase Order')] } },
  [LOGS_METHOD]: { body: { message: { notification_logs: [{ name: 'N1', subject: 'x', read: 0, creation: '2026-11-23 10:00:00' }], user_info: {} } } },
  'hrms.api.get_current_employee_info': { body: { message: { name: 'EMP-0001' } } },
  'hrms.api.get_holidays_for_employee': {
    body: { message: [{ holiday_date: '2000-01-01', description: 'Past' }, { holiday_date: '2999-12-25', description: 'Christmas' }] },
  },
  'hrms.api.get_leave_applications': {
    body: { message: [{ name: 'L1', leave_type: 'Casual Leave', from_date: '2999-01-01', to_date: '2999-01-01', status: 'Open' }] },
  },
};
let mockOffline = false;
const mockErp = fakeErp(answers);
const mockApiRef = {
  current: async (path: string, init?: RequestInit) => {
    if (mockOffline && path.includes('self_check_in')) throw new TypeError('Network request failed');
    return mockErp.api(path, init);
  },
};
jest.mock('@/auth/session', () => ({
  APP_NAME: 'ERP Mobile',
  SignedOutError: class SignedOutError extends Error {},
  useAuth: () => ({ user: { name: 'Worker A', email: 'a@example.com', roles: [] } }),
  useApiRef: () => mockApiRef,
}));
const mockStore = memoryStore();
jest.mock('@/lib/offline-store', () => ({ offlineStore: async () => mockStore }));
const mockSaved = new Map<string, string>();
jest.mock('expo-secure-store', () => ({
  getItemAsync: async (k: string) => mockSaved.get(k) ?? null,
  setItemAsync: async (k: string, v: string) => void mockSaved.set(k, v),
}));

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;
const stub = (label: string) => {
  const Stub = () => <Text>{label}</Text>;
  Stub.displayName = label;
  return Stub;
};
const app = {
  index: Today,
  inbox: stub('Inbox screen'),
  'my-hr': stub('My HR screen'),
  'attendance/check-in': stub('Check-in screen'),
  'attendance/team': stub('Team screen'),
  'attendance/approve': stub('Approve screen'),
};
const open = () => renderRouter(app, { initialUrl: '/', wrapper });
const position = (label: string) => JSON.stringify(screen.toJSON()).indexOf(label);
const teamCalls = () => mockErp.calls.filter((c) => c.method === `${HR_API}.team`).map((c) => c.args);

describe('Today', () => {
  beforeEach(async () => {
    clearInbox();
    mockOffline = false;
    mockErp.calls.length = 0;
    choosePlace('S1', null);
    await mockStore.clear();
  });

  it('the header: app, role badge, project, site, shift and the Inbox count', async () => {
    await open();
    expect(await screen.findByText('Project 1')).toBeOnTheScreen();
    expect(screen.getByText('ERP Mobile')).toBeOnTheScreen();
    expect(screen.getByText('APPROVER · SUPERVISOR · STAFF')).toBeOnTheScreen();
    expect(screen.getByText('Site 1')).toBeOnTheScreen();
    expect(screen.getByText('Day shift (00:00–23:59)')).toBeOnTheScreen();
    expect(await screen.findByLabelText('Inbox: 4 waiting')).toBeOnTheScreen(); // 3 approvals + 1 unread
  });

  it('own attendance first, then the team, then bulk approval, then what waits', async () => {
    await open();
    await screen.findByText('WAITING FOR YOU');
    const order = ['My attendance: not checked in yet', 'My team today', 'Bulk attendance approval', 'WAITING FOR YOU'].map(position);
    expect(order.every((p) => p >= 0)).toBe(true);
    expect([...order].sort((a, b) => a - b)).toEqual(order);
  });

  it('the team card: marked of total, each state in words, and the next step', async () => {
    const router = await open();
    expect(await screen.findByText('9/15')).toBeOnTheScreen();
    expect(screen.getByText('9 sent for approval or approved')).toBeOnTheScreen();
    expect(screen.getByText('2 saved as drafts')).toBeOnTheScreen();
    expect(screen.getByText('1 returned for correction')).toBeOnTheScreen();
    expect(screen.getByText('3 not marked yet')).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Continue marking (3 left)'));
    expect(await screen.findByText('Team screen')).toBeOnTheScreen();
    expect(router.getSearchParams()).toMatchObject({ site: 'S1', shift: 'Day1' });
  });

  it('the bulk approval card: count, ready for this person, exceptions, then the bulk screen', async () => {
    const router = await open();
    expect(await screen.findByText('2 ready for you to approve')).toBeOnTheScreen();
    expect(screen.getByText('2 exceptions (offline or absent)')).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Review and approve'));
    expect(await screen.findByText('Approve screen')).toBeOnTheScreen();
    expect(router.getSearchParams()).toMatchObject({ site: 'S1' });
  });

  it('the approvals tally by document type, with the total', async () => {
    await open();
    expect(await screen.findByText('3 TOTAL')).toBeOnTheScreen();
    expect(screen.getByText('Purchase Order')).toBeOnTheScreen();
    expect(screen.getByText('2 pending')).toBeOnTheScreen();
    expect(screen.getByText('1 pending')).toBeOnTheScreen();
  });

  it('choosing another site in the header shows that site’s cards', async () => {
    await open();
    await screen.findByText('9/15');
    await fireEvent.press(screen.getByLabelText('Site Site 1. Change'));
    await fireEvent.press(screen.getByText('Site 3'));
    expect(await screen.findByText('0/4')).toBeOnTheScreen();
    expect(screen.queryByText('Bulk attendance approval')).toBeNull(); // not an approver at Site 3
    expect(screen.getByText('SUPERVISOR')).toBeOnTheScreen();
    expect(JSON.parse(mockSaved.get('header-place') ?? '{}')).toEqual({ site: 'S3', shift: null });
  });

  it('the shift pill switches to the next shift and the team card follows', async () => {
    await open();
    await screen.findByText('9/15');
    await fireEvent.press(screen.getByLabelText('Day shift (00:00–23:59). Change shift'));
    expect(await screen.findByText('Night shift (23:59–00:00)')).toBeOnTheScreen();
    expect(teamCalls().at(-1)).toEqual({ site: 'S1', shift: 'Night1' });
  });

  it('what waits to be sent: an offline banner, then "Send now" sends it', async () => {
    mockOffline = true;
    await mockStore.put({ id: 'q1', method: `${HR_API}.self_check_in`, args: { payload: {} }, createdAt: Date.now(), attempts: 0, state: 'waiting' });
    await open();
    expect(await screen.findByText('No connection: 1 captures are saved on this phone and are sent by themselves.')).toBeOnTheScreen();
    expect(screen.getByText('1 captures waiting to send')).toBeOnTheScreen();
    mockOffline = false;
    answers[`${HR_API}.self_check_in`] = { body: { message: { name: 'E1' } } };
    await fireEvent.press(screen.getByText('Send now'));
    expect(await screen.findByText('Nothing waiting to send')).toBeOnTheScreen();
    expect(await mockStore.all()).toEqual([]);
  });

  it('"+" offers only the actions this person really has', async () => {
    const router = await open();
    await screen.findByText('9/15');
    await fireEvent.press(screen.getByLabelText('Quick actions'));
    expect(screen.getAllByText('Check in')).toHaveLength(2); // the attendance strip and the quick action
    expect(screen.getByText('Mark attendance at Site 1')).toBeOnTheScreen();
    expect(screen.getByText('Approve attendance at Site 1')).toBeOnTheScreen();
    expect(screen.queryByText(/Payment|Gate pass|PTW/)).toBeNull();
    await fireEvent.press(screen.getByText('Mark attendance at Site 1'));
    expect(await screen.findByText('Team screen')).toBeOnTheScreen();
    expect(router.getPathname()).toBe('/attendance/team');
  });

  it('no attendance module on the server: no attendance cards, no project line and no "+"', async () => {
    const saved = answers[`${HR_API}.bootstrap`];
    answers[`${HR_API}.bootstrap`] = { status: 404, body: {} };
    await open();
    await screen.findByText('WAITING FOR YOU');
    expect(screen.queryByText('My team today')).toBeNull();
    expect(screen.queryByText('Project 1')).toBeNull();
    expect(screen.queryByLabelText('Quick actions')).toBeNull();
    answers[`${HR_API}.bootstrap`] = saved;
  });

  it('one tap switches Outdoor mode', async () => {
    await open();
    await fireEvent.press(await screen.findByLabelText('Outdoor mode: OFF'));
    expect(screen.getByLabelText('Outdoor mode: ON')).toBeOnTheScreen();
  });

  it('refused items and the HR card', async () => {
    await mockStore.put({ id: 'r', method: 'm', args: {}, createdAt: Date.now(), attempts: 1, state: 'failed', error: 'refused' });
    await open();
    expect(await screen.findByText('Next holiday: 25-12-2999 Christmas')).toBeOnTheScreen();
    expect(screen.getByText('1 leave applications still open')).toBeOnTheScreen();
    expect(screen.getByText('1 not accepted by ERPNext: open them to see why')).toBeOnTheScreen();
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
