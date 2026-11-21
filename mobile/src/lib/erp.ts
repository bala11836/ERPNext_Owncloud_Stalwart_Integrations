import { useEffect, useState } from 'react';

import { SignedOutError, useAuth } from '@/auth/session';

type Api = ReturnType<typeof useAuth>['api'];

/** Read ERPNext JSON as the signed-in user; turns ERPNext errors into short, plain messages. */
export async function getJson<T>(api: Api, path: string): Promise<T> {
  let res: Response;
  try {
    res = await api(path);
  } catch (e) {
    if (e instanceof SignedOutError) throw e;
    throw new Error("Can't reach ERPNext. Check your internet connection.");
  }
  if (res.ok) return (await res.json()) as T;
  if (res.status === 403) throw new Error("You don't have permission to see this in ERPNext.");
  if (res.status === 404) throw new Error('Not found in ERPNext.');
  throw new Error(`ERPNext error (${res.status}). Try again.`);
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
