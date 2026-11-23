import { z } from 'zod';

import { type Api, OfflineError, ServerError, callErp, getJson } from '@/lib/erp';

jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: jest.fn() }));
const { SignedOutError } = jest.requireMock('@/auth/session') as { SignedOutError: new (m: string) => Error };

type Call = { path: string; init?: RequestInit };

/** A fake signed-in `api`: answers with `status` and `body` (or throws `error`), recording each call. */
function fakeApi(status: number, body: unknown, error?: Error) {
  const calls: Call[] = [];
  const api: Api = async (path, init) => {
    calls.push({ path, init });
    if (error) throw error;
    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => {
        if (body === undefined) throw new SyntaxError('not JSON');
        return body;
      },
    } as Response;
  };
  return { api, calls };
}

const Site = z.object({ name: z.string(), radius_m: z.number() });
// ERPNext's error body for frappe.throw: a JSON list of JSON strings.
const thrown = (message: string) => ({ _server_messages: JSON.stringify([JSON.stringify({ message })]) });

describe('callErp', () => {
  it('reads a method with its arguments in the address and returns the checked answer', async () => {
    const { api, calls } = fakeApi(200, { message: { name: 'Site 1', radius_m: 150 } });
    await expect(callErp(api, 'app.api.site', Site, { name: 'Site 1', limit: 5 })).resolves.toEqual({
      name: 'Site 1',
      radius_m: 150,
    });
    expect(calls[0].path).toBe('/api/method/app.api.site?name=Site+1&limit=5');
    expect(calls[0].init).toBeUndefined();
  });

  it('writes with POST and a JSON body', async () => {
    const { api, calls } = fakeApi(200, { message: { name: 'Site 1', radius_m: 150 } });
    await callErp(api, 'app.api.save', Site, { payload: { a: 1 } }, { post: true });
    expect(calls[0].init?.method).toBe('POST');
    expect(JSON.parse(String(calls[0].init?.body))).toEqual({ payload: { a: 1 } });
  });

  it('never uses an answer of the wrong shape', async () => {
    const { api } = fakeApi(200, { message: { name: 'Site 1', radius_m: '150' } });
    await expect(callErp(api, 'app.api.site', Site)).rejects.toThrow('does not understand');
  });

  it("shows ERPNext's own reason when it refuses, and does not retry it", async () => {
    const { api } = fakeApi(417, thrown('Take a <b>selfie</b> to check in.'));
    const error = await callErp(api, 'app.api.check_in', Site, {}, { post: true }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ServerError);
    expect((error as ServerError).message).toBe('Take a selfie to check in.');
    expect((error as ServerError).retry).toBe(false);
  });

  it('marks server trouble as worth retrying', async () => {
    const { api } = fakeApi(503, null);
    const error = (await callErp(api, 'app.api.site', Site).catch((e: unknown) => e)) as ServerError;
    expect(error.retry).toBe(true);
    expect(error.message).toBe('ERPNext error (503). Try again.');
  });

  it('turns a lost connection into OfflineError and lets sign-out pass through', async () => {
    await expect(callErp(fakeApi(0, null, new TypeError('Network request failed')).api, 'm', Site)).rejects.toBeInstanceOf(
      OfflineError,
    );
    await expect(callErp(fakeApi(0, null, new SignedOutError('x')).api, 'm', Site)).rejects.toBeInstanceOf(SignedOutError);
  });

  it('refuses an OK answer that is not JSON', async () => {
    await expect(getJson(fakeApi(200, undefined).api, '/api/resource/X')).rejects.toThrow('does not understand');
  });
});
