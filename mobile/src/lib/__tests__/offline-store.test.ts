import { type Db, encryptedStore } from '@/lib/offline-store';
import type { QueueItem } from '@/lib/queue';

jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: jest.fn() }));

const KEY = 'ab'.repeat(32);

/** A fake SQLite database: records every statement; `cipher` is what PRAGMA cipher_version answers. */
function fakeDb(cipher: string) {
  const statements: string[] = [];
  const rows = new Map<string, { created_at: number; body: string }>();
  let closed = false;
  const db = {
    execAsync: async (sql: string) => void statements.push(sql),
    getFirstAsync: async (sql: string) => (statements.push(sql), sql.includes('cipher_version') ? { cipher_version: cipher } : null),
    getAllAsync: async (sql: string) => (
      statements.push(sql), [...rows.values()].sort((a, b) => a.created_at - b.created_at)
    ),
    runAsync: async (sql: string, ...params: (string | number)[]) => {
      statements.push(sql);
      if (sql.startsWith('INSERT')) rows.set(String(params[0]), { created_at: Number(params[1]), body: String(params[2]) });
      else if (sql.includes('WHERE id')) rows.delete(String(params[0]));
      else rows.clear();
      return { changes: 1, lastInsertRowId: 0 };
    },
    closeAsync: async () => void (closed = true),
  } as unknown as Db;
  return { db, statements, rows, isClosed: () => closed };
}

const item = (id: string, createdAt: number): QueueItem => ({
  id, method: 'm', args: { request_id: id }, createdAt, attempts: 0, state: 'waiting',
});

describe('encrypted offline store', () => {
  it('unlocks with the key before anything else and confirms encryption is on', async () => {
    const { db, statements } = fakeDb('4.6.1 community');
    expect((await encryptedStore(db, KEY))?.encrypted).toBe(true);
    expect(statements[0]).toBe(`PRAGMA key = "x'${KEY}'";`);
    expect(statements[1]).toBe('PRAGMA cipher_version;');
  });

  it('refuses a database without encryption (Expo Go, or a build without SQLCipher) and writes nothing', async () => {
    const { db, statements, isClosed } = fakeDb('');
    expect(await encryptedStore(db, KEY)).toBeNull();
    expect(isClosed()).toBe(true);
    expect(statements.some((s) => s.startsWith('CREATE') || s.startsWith('INSERT'))).toBe(false);
  });

  it('refuses a malformed key', async () => {
    await expect(encryptedStore(fakeDb('4.6.1').db, "x'; DROP")).rejects.toThrow('invalid offline key');
  });

  it('keeps, lists in order, removes and clears queue items', async () => {
    const store = (await encryptedStore(fakeDb('4.6.1').db, KEY))!;
    await store.put(item('b', 2));
    await store.put(item('a', 1));
    expect((await store.all()).map((i) => i.id)).toEqual(['a', 'b']);
    await store.remove('a');
    expect((await store.all()).map((i) => i.id)).toEqual(['b']);
    await store.clear();
    expect(await store.all()).toEqual([]);
  });

  it('saved answers live in the same encrypted file, older than a day are deleted, sign-out deletes all', async () => {
    const { db, statements } = fakeDb('4.6.1');
    const store = (await encryptedStore(db, KEY))!;
    expect(statements.some((s) => s.includes('CREATE TABLE IF NOT EXISTS saved'))).toBe(true);
    await store.keep('k', '{}', 5000, 1000);
    expect(statements.slice(-2)).toEqual([
      'DELETE FROM saved WHERE saved_at < ?',
      'INSERT OR REPLACE INTO saved (key, saved_at, body) VALUES (?, ?, ?)',
    ]);
    await store.clear();
    expect(statements.slice(-2)).toEqual(['DELETE FROM queue', 'DELETE FROM saved']);
  });
});

describe('offline store in Expo Go', () => {
  it('stays in memory: the encrypted database is never opened', async () => {
    jest.resetModules();
    jest.doMock('expo-constants', () => ({ __esModule: true, default: { executionEnvironment: 'storeClient' }, ExecutionEnvironment: { StoreClient: 'storeClient' } }));
    const openDatabaseAsync = jest.fn();
    jest.doMock('expo-sqlite', () => ({ openDatabaseAsync, deleteDatabaseAsync: jest.fn() }));
    const { offlineStore, offlineStorageKind } = jest.requireActual('@/lib/offline-store') as typeof import('@/lib/offline-store');
    const store = await offlineStore();
    await store.put(item('a', 1));
    expect((await store.all()).map((i) => i.id)).toEqual(['a']);
    expect(openDatabaseAsync).not.toHaveBeenCalled();
    await expect(offlineStorageKind()).resolves.toBe('memory');
    expect(store.encrypted).toBeUndefined();
  });
});
