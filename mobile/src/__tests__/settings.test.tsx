import type { ReactNode } from 'react';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import Settings from '@/app/settings';
import { memoryStore } from '@/lib/queue';
import { ThemeProvider } from '@/theme';

const mockSignOut = jest.fn();
const mockApiRef: { current: jest.Mock } = { current: jest.fn() };
jest.mock('@/auth/session', () => ({
  SignedOutError: class SignedOutError extends Error {},
  useAuth: () => ({ user: { name: 'Worker A', email: 'a@example.com', roles: ['Employee'] }, signOut: mockSignOut }),
  useApiRef: () => mockApiRef,
}));
const mockStore = memoryStore();
jest.mock('@/lib/offline-store', () => ({ offlineStorageKind: async () => 'encrypted', offlineStore: async () => mockStore }));
const mockFlush = jest.fn(async () => ({ sent: 0, failed: 0, stopped: true }));
jest.mock('@/lib/sender', () => ({ flushQueue: () => mockFlush() }));
const mockSaved = new Map<string, string>();
jest.mock('expo-secure-store', () => ({
  getItemAsync: async (k: string) => mockSaved.get(k) ?? null,
  setItemAsync: async (k: string, v: string) => void mockSaved.set(k, v),
}));

const mockSchedule = jest.fn(async (_req: unknown) => 'n1');
const mockGranted = { granted: true };
const mockChannels: unknown[][] = [];
jest.mock('expo-notifications', () => ({
  AndroidImportance: { HIGH: 4 },
  SchedulableTriggerInputTypes: { TIME_INTERVAL: 'timeInterval' },
  requestPermissionsAsync: async () => mockGranted,
  setNotificationChannelAsync: async (...a: unknown[]) => void mockChannels.push(a),
  scheduleNotificationAsync: (req: unknown) => mockSchedule(req),
}));

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;
const open = () => renderRouter({ index: Settings }, { initialUrl: '/', wrapper });

describe('settings', () => {
  beforeEach(async () => {
    mockSaved.clear();
    mockSignOut.mockClear();
    await mockStore.clear();
  });

  it('shows the app lock, the offline storage and no demo statuses', async () => {
    await open();
    expect(
      screen.getByText('App lock: on. Face ID, fingerprint or passcode when the app opens and after 60 seconds away.'),
    ).toBeOnTheScreen();
    expect(await screen.findByText('Offline storage: encrypted on this phone')).toBeOnTheScreen();
    expect(screen.queryByText('How statuses look')).toBeNull();
  });

  it('remembers Outdoor mode on the phone', async () => {
    await open();
    expect(screen.getByText('Outdoor mode: Off')).toBeOnTheScreen();
    await fireEvent.press(screen.getByRole('switch', { name: /Outdoor mode/ }));
    expect(screen.getByText('Outdoor mode: On')).toBeOnTheScreen();
    expect(mockSaved.get('outdoor-mode')).toBe('1');
  });

  it('starts in Outdoor mode when it was left on', async () => {
    mockSaved.set('outdoor-mode', '1');
    await open();
    expect(await screen.findByText('Outdoor mode: On')).toBeOnTheScreen();
  });

  it('signing out with unsent entries: "Send now", or type DELETE first (owner decision 4)', async () => {
    await mockStore.put({ id: 'q1', method: 'm', args: {}, createdAt: Date.now(), attempts: 0, state: 'waiting' });
    await open();
    expect(await screen.findByText(/^1 entries are not sent yet/)).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Sign out'));
    expect(mockSignOut).not.toHaveBeenCalled();
    await fireEvent.press(screen.getByText('Send now'));
    expect(mockFlush).toHaveBeenCalled();
    await fireEvent.changeText(screen.getByLabelText('Type DELETE to delete them'), 'DELETE');
    await fireEvent.press(screen.getByText('Sign out'));
    expect(mockSignOut).toHaveBeenCalled();
  });

  it('nothing unsent: Sign out at once, no warning', async () => {
    await open();
    await screen.findByText('Offline storage: encrypted on this phone');
    expect(screen.queryByText(/entries are not sent yet/)).toBeNull();
    await fireEvent.press(screen.getByText('Sign out'));
    expect(mockSignOut).toHaveBeenCalled();
  });

  it('a test approval alert a minute later, as a real one: Payments channel, kind, count and site only; opens the Inbox', async () => {
    mockGranted.granted = true;
    mockSchedule.mockClear();
    mockChannels.length = 0;
    mockApiRef.current = jest.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ message: { sites: [{ name: 'S1', label: 'Site A', supervisor: false, approver: true, shifts: [] }], check_in_sites: [] } }),
    }));
    await open();
    await fireEvent.press(screen.getByRole('button', { name: 'Send test approval alert' }));
    expect(await screen.findByText('Test approval alert in 60 seconds. Close the app now and wait; tap it when it comes.')).toBeOnTheScreen();
    expect(mockSchedule).toHaveBeenCalledWith({
      content: { title: 'Payment approval waiting', body: '1 payment · Site A', data: { url: '/inbox' } },
      trigger: { type: 'timeInterval', seconds: 60, channelId: 'payments' },
    });
    expect(mockChannels).toEqual([['payments', { name: 'Payments', importance: 4 }]]);
  });

  it('says how to turn notifications on when the phone refuses', async () => {
    mockGranted.granted = false;
    mockSchedule.mockClear();
    await open();
    await fireEvent.press(screen.getByRole('button', { name: 'Send test approval alert' }));
    expect(await screen.findByText(/Notifications are off for this app/)).toBeOnTheScreen();
    expect(mockSchedule).not.toHaveBeenCalled();
  });
});
