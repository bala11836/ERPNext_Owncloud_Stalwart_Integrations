import type { ReactNode } from 'react';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import Settings from '@/app/settings';
import { ThemeProvider } from '@/theme';

jest.mock('@/auth/session', () => ({
  SignedOutError: class SignedOutError extends Error {},
  useAuth: () => ({ user: { name: 'Worker A', email: 'a@example.com', roles: ['Employee'] }, signOut: jest.fn() }),
}));
jest.mock('@/lib/offline-store', () => ({ offlineStorageKind: async () => 'encrypted' }));
const mockSaved = new Map<string, string>();
jest.mock('expo-secure-store', () => ({
  getItemAsync: async (k: string) => mockSaved.get(k) ?? null,
  setItemAsync: async (k: string, v: string) => void mockSaved.set(k, v),
}));

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;
const open = () => renderRouter({ index: Settings }, { initialUrl: '/', wrapper });

describe('settings', () => {
  beforeEach(() => mockSaved.clear());

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
    expect(screen.getByText('Outdoor mode: OFF')).toBeOnTheScreen();
    await fireEvent.press(screen.getByRole('switch', { name: /Outdoor mode/ }));
    expect(screen.getByText('Outdoor mode: ON')).toBeOnTheScreen();
    expect(mockSaved.get('outdoor-mode')).toBe('1');
  });

  it('starts in Outdoor mode when it was left on', async () => {
    mockSaved.set('outdoor-mode', '1');
    await open();
    expect(await screen.findByText('Outdoor mode: ON')).toBeOnTheScreen();
  });
});
