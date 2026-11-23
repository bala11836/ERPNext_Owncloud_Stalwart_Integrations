import { useEffect, useState } from 'react';
import type { z } from 'zod';

import { SignedOutError, useAuth } from '@/auth/session';
import { t } from '@/i18n';

export type Api = ReturnType<typeof useAuth>['api'];

/** No connection to ERPNext: worth trying again later (the offline queue keeps the item). */
export class OfflineError extends Error {}

/** ERPNext answered with an error. `retry`: a server or rate problem, not a refusal of the request itself. */
export class ServerError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
  get retry() {
    return this.status >= 500 || this.status === 429;
  }
}

/** ERPNext's own message for a refused request (frappe.throw), as plain text, if it sent one. */
function serverMessage(body: unknown): string | null {
  try {
    const raw = (body as { _server_messages?: string })?._server_messages;
    const first = raw ? (JSON.parse(JSON.parse(raw)[0]) as { message?: string }).message : null;
    return first ? first.replace(/<[^>]*>/g, '').trim() || null : null;
  } catch {
    return null;
  }
}

async function send(api: Api, path: string, init?: RequestInit): Promise<unknown> {
  let res: Response;
  try {
    res = await api(path, init);
  } catch (e) {
    if (e instanceof SignedOutError) throw e;
    throw new OfflineError(t('erp.offline'));
  }
  const body: unknown = await res.json().catch(() => null);
  if (res.ok) {
    if (body === null) throw new ServerError(t('erp.unexpected'), res.status);
    return body;
  }
  const own = serverMessage(body);
  if (res.status === 403) throw new ServerError(own ?? t('erp.forbidden'), 403);
  if (res.status === 404) throw new ServerError(t('erp.notFound'), 404);
  throw new ServerError(own ?? t('erp.failed', { status: res.status }), res.status);
}

/** Read ERPNext JSON as the signed-in user; turns ERPNext errors into short, plain messages. */
export async function getJson<T>(api: Api, path: string): Promise<T> {
  return (await send(api, path)) as T;
}

/**
 * Call a whitelisted ERPNext method as the signed-in user and check the answer against `schema`
 * before anything uses it. GET puts `args` in the address; POST sends them as JSON (writes are POST).
 * An answer of the wrong shape is an error shown to the person, never used.
 */
export async function callErp<S extends z.ZodType>(
  api: Api,
  method: string,
  schema: S,
  args: Record<string, unknown> = {},
  { post = false }: { post?: boolean } = {},
): Promise<z.infer<S>> {
  const path = `/api/method/${method}`;
  const query = new URLSearchParams(
    Object.entries(args).map(([k, v]) => [k, typeof v === 'string' ? v : JSON.stringify(v)]),
  ).toString();
  const body = post
    ? await send(api, path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(args),
      })
    : await send(api, query ? `${path}?${query}` : path);
  const checked = schema.safeParse((body as { message?: unknown } | null)?.message);
  if (!checked.success) throw new ServerError(t('erp.unexpected'), 200);
  return checked.data;
}

// In-memory only: makes going back instant. Cleared on sign-out. Nothing business-related is written
// to disk until the encrypted store lands (rule 7).
// ponytail: no offline copy of lists/records yet; needs the encrypted SQLite store (development build).
const cache = new Map<string, unknown>();
export const clearErpCache = () => cache.clear();

/** GET once per path (and per reload). While loading or after an error, the last good copy is shown. */
export function useErp<T>(path: string | null) {
  const { api } = useAuth();
  const [attempt, setAttempt] = useState(0);
  const key = path ? `${path}#${attempt}` : null;
  const [result, setResult] = useState<{ key: string | null; data?: T; error?: string }>({ key: null });

  useEffect(() => {
    if (!path || !key) return;
    let live = true;
    getJson<T>(api, path).then(
      (d) => {
        cache.set(path, d);
        if (live) setResult({ key, data: d });
      },
      (e: unknown) => {
        if (live) setResult({ key, error: e instanceof Error ? e.message : 'Something went wrong' });
      },
    );
    return () => {
      live = false;
    };
  }, [api, path, key]);

  const fresh = result.key === key;
  return {
    data: (fresh ? result.data : undefined) ?? (path ? (cache.get(path) as T | undefined) : undefined),
    error: fresh ? (result.error ?? null) : null,
    loading: !!path && !fresh,
    reload: () => setAttempt((n) => n + 1),
  };
}

export type Boot = {
  user: { email: string; full_name: string };
  roles: string[];
  menus: { name: string; label: string; app?: string; items: MenuItem[] }[];
};
export type MenuItem = { type: 'section'; label: string } | { type: 'doctype'; label: string; doctype: string };

export const BOOT_PATH = '/api/method/erpnext_drive_integrations.onboarding.api.bootstrap';

export type DocField = {
  fieldname: string;
  fieldtype: string;
  label?: string;
  options?: string;
  hidden?: 0 | 1;
  in_list_view?: 0 | 1;
};
export type DocMeta = {
  name: string;
  title_field?: string;
  is_submittable?: 0 | 1;
  /** Settings-style doctype: one record, named like the doctype; there is no list. */
  issingle?: 0 | 1;
  /** Built on the fly by its app; ERPNext's list API can't page through it. */
  is_virtual?: 0 | 1;
  fields: DocField[];
};

export const metaPath = (doctype: string) =>
  `/api/method/frappe.desk.form.load.getdoctype?doctype=${encodeURIComponent(doctype)}`;

/** getdoctype returns the doctype's meta plus its child tables' metas. */
export function useMeta(doctype: string) {
  const res = useErp<{ docs: DocMeta[] }>(metaPath(doctype));
  const metas = res.data?.docs ?? [];
  return { ...res, meta: metas.find((m) => m.name === doctype), metas };
}
