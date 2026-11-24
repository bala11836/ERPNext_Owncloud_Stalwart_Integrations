import { openableUrl } from '@/lib/alerts';

jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: jest.fn() }));
jest.mock('expo-notifications', () => ({ AndroidImportance: { HIGH: 4 } }));
jest.mock('expo-router', () => ({ router: { push: jest.fn() } }));

describe('an alert opens only the app approval screens', () => {
  it('the Inbox and an approval card', () => {
    expect(openableUrl('/inbox')).toBe('/inbox');
    expect(openableUrl('/approvals/Payment Entry/PE-0412')).toBe('/approvals/Payment Entry/PE-0412');
  });
  it('nothing else: other screens, web addresses, query parts, non-text', () => {
    for (const url of ['/settings', 'https://example.com', '//example.com/inbox', '/inbox?x=1', '/approvals/a#b', 42, null, undefined]) {
      expect(openableUrl(url)).toBeNull();
    }
  });
});
