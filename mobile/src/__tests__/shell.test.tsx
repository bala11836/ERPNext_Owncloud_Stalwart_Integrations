import type { ReactNode } from 'react';
import { Text } from 'react-native';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import AppTabs from '@/app/(app)/_layout';
import Menu from '@/app/(app)/menu';
import Today from '@/app/(app)/index';
import { memoryStore } from '@/lib/queue';
import { ThemeProvider } from '@/theme';

jest.mock('@/auth/session', () => ({
  SignedOutError: class SignedOutError extends Error {},
  useAuth: () => ({ user: { name: 'Worker A', email: 'a@example.com', roles: [] }, api: jest.fn() }),
}));
const mockStore = memoryStore();
jest.mock('@/lib/offline-store', () => ({ offlineStore: async () => mockStore }));
jest.mock('@/lib/erp', () => ({
  ...jest.requireActual('@/lib/erp'),
  useErp: () => ({
    data: { message: { menus: [{ name: 'hr', label: 'Human Resources', app: 'hrms', items: [] }] } },
    error: null,
    loading: false,
    reload: jest.fn(),
  }),
}));

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;
const Stub = () => <Text>stub</Text>;
const app = {
  '(app)/_layout': AppTabs,
  '(app)/index': Today,
  '(app)/inbox': Stub,
  '(app)/my-hr': Stub,
  '(app)/menu': Menu,
  settings: () => <Text>Settings screen</Text>,
};

describe('app shell', () => {
  beforeEach(async () => {
    await mockStore.clear();
  });

  it('has the four tabs of owner decision 2, in order', async () => {
    await renderRouter(app, { initialUrl: '/', wrapper });
    const labels = screen.getAllByRole('button').map((b) => b.props.accessibilityLabel ?? '');
    const tabs = ['Today', 'Inbox', 'My HR', 'Menu'].map((name) => labels.findIndex((l) => l.startsWith(name)));
    expect(tabs.every((i) => i >= 0)).toBe(true);
    expect([...tabs].sort((a, b) => a - b)).toEqual(tabs);
  });

  it('Today greets the person and says nothing is waiting', async () => {
    await renderRouter(app, { initialUrl: '/', wrapper });
    expect(await screen.findByText('Hello, Worker A')).toBeOnTheScreen();
    expect(await screen.findByText('Nothing waiting to send')).toBeOnTheScreen();
  });

  it('Today counts what waits in the offline queue', async () => {
    for (const id of ['a', 'b']) {
      await mockStore.put({ id, method: 'm', args: {}, createdAt: 1, attempts: 0, state: 'waiting' });
    }
    await mockStore.put({ id: 'c', method: 'm', args: {}, createdAt: 1, attempts: 1, state: 'failed', error: 'refused' });
    await renderRouter(app, { initialUrl: '/', wrapper });
    expect(await screen.findByText('2 waiting to send: sent by itself when you are online')).toBeOnTheScreen();
  });

  it('Menu lists Settings first, then the role menus, and opens Settings', async () => {
    const router = await renderRouter(app, { initialUrl: '/menu', wrapper });
    expect(screen.getByText('Human Resources')).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Settings'));
    expect(await screen.findByText('Settings screen')).toBeOnTheScreen();
    expect(router.getPathname()).toBe('/settings');
  });
});
