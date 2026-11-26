import { PUSH_ADDRESS, PUSH_API } from '@/auth/push-address';
import { pushTexts, registerPush, ringOff, setRing } from '@/lib/push';

import { fakeErp } from '../../__tests__/fake-erp';

jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: jest.fn() }));
const mockStore = new Map<string, string>();
jest.mock('expo-secure-store', () => ({
  getItemAsync: async (k: string) => mockStore.get(k) ?? null,
  setItemAsync: async (k: string, v: string) => void mockStore.set(k, v),
  deleteItemAsync: async (k: string) => void mockStore.delete(k),
}));
let mockGranted = true;
let mockToken: (() => Promise<{ type: string; data: string }>) | null = null;
jest.mock('expo-notifications', () => ({
  requestPermissionsAsync: async () => ({ granted: mockGranted }),
  getDevicePushTokenAsync: () => (mockToken ? mockToken() : Promise.reject(new Error('no Firebase'))),
}));
jest.mock('expo-linking', () => ({ createURL: (p: string) => `erpmobile://${p.replace(/^\//, '')}` }));
const mockNative = { setPushTexts: jest.fn() };
jest.mock('../../../modules/approval-alert', () => ({
  get ApprovalAlert() {
    return mockNative; // read when used: the mock factory runs before this file's constants
  },
}));

const TOKEN = 'fcm-token-'.padEnd(160, 'x');
const serve = () => fakeErp({ [`${PUSH_API}.register_device`]: { body: { message: { ok: true } } } });

beforeEach(() => {
  mockStore.clear();
  mockGranted = true;
  mockToken = async () => ({ type: 'android', data: TOKEN });
  mockNative.setPushTexts.mockClear();
});

describe('registering this phone for alerts while the app is closed', () => {
  it('sends the FCM address to ERPNext by POST and keeps it for sign-out', async () => {
    const erp = serve();
    expect(await registerPush(erp.api)).toBe('registered');
    expect(erp.calls).toEqual([{ method: `${PUSH_API}.register_device`, args: { token: TOKEN, platform: 'android' }, post: true }]);
    expect(mockStore.get(PUSH_ADDRESS)).toBe(TOKEN);
  });

  it('alerts blocked by the person: nothing is sent', async () => {
    mockGranted = false;
    const erp = serve();
    expect(await registerPush(erp.api)).toBe('denied');
    expect(erp.calls).toEqual([]);
  });

  it('a build without the Firebase file: unavailable, nothing sent', async () => {
    mockToken = null;
    const erp = serve();
    expect(await registerPush(erp.api)).toBe('unavailable');
    expect(erp.calls).toEqual([]);
    expect(mockStore.has(PUSH_ADDRESS)).toBe(false);
  });

  it('the server refuses: the error reaches the caller and nothing is kept', async () => {
    const erp = fakeErp({ [`${PUSH_API}.register_device`]: { status: 417, body: {} } });
    await expect(registerPush(erp.api)).rejects.toThrow();
    expect(mockStore.has(PUSH_ADDRESS)).toBe(false);
  });
});

describe('what the phone writes alerts with', () => {
  it('areas by document type, area names, a link base, texts without names or amounts', async () => {
    const t = await pushTexts();
    expect(t.areas['Payment Entry']).toBe('payments');
    expect(t.areas['Field Attendance Entry']).toBe('attendance');
    expect(t.labels.payments).toBeTruthy();
    expect(t.base).toBe('erpmobile://');
    expect(t.approvalTitle).toContain('{area}');
    expect(t.ringOff).toEqual([]);
  });

  it('every approval rings by default; an area can become a normal alert and back, and the native part is told', async () => {
    expect(await ringOff()).toEqual([]);
    await setRing('hr', false);
    expect(await ringOff()).toEqual(['hr']);
    expect(JSON.parse(mockNative.setPushTexts.mock.calls.at(-1)[0]).ringOff).toEqual(['hr']);
    await setRing('hr', true);
    expect(await ringOff()).toEqual([]);
  });

  it('a damaged or foreign ring list is ignored', async () => {
    mockStore.set('push-ring-off', JSON.stringify(['hr', 'not-an-area', 42]));
    expect(await ringOff()).toEqual(['hr']);
  });
});
