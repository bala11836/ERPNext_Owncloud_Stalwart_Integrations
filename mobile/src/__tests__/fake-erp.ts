// Test helper (not a test): a fake ERPNext `api` that answers per whitelisted method, recording each call.
import type { Api } from '@/lib/erp';

export type Answer = { status?: number; body: unknown };
export type Call = { method: string; args: Record<string, unknown>; post: boolean };

export function fakeErp(answers: Record<string, Answer | ((args: Record<string, unknown>) => Answer)>) {
  const calls: Call[] = [];
  const api: Api = async (path, init) => {
    const [base, query] = path.split('?');
    const method = base.replace('/api/method/', '');
    const post = init?.method === 'POST';
    const args: Record<string, unknown> = post
      ? JSON.parse(String(init?.body ?? '{}'))
      : Object.fromEntries([...new URLSearchParams(query ?? '')].map(([k, v]) => [k, v]));
    calls.push({ method, args, post });
    const found = answers[method];
    const answer = typeof found === 'function' ? found(args) : (found ?? { status: 404, body: {} });
    const status = answer.status ?? 200;
    return { ok: status < 300, status, json: async () => answer.body } as Response;
  };
  return { api, calls };
}

/** ERPNext's error body for frappe.throw. */
export const thrown = (message: string) => ({ _server_messages: JSON.stringify([JSON.stringify({ message })]) });
