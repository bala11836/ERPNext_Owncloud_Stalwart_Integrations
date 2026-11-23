// Where the offline queue lives (build guide sections 5 and 8).
// Development build (Android APK, later iPhone): an SQLCipher-encrypted database; its random key lives in
// the Keychain / Keystore, on this device only. Expo Go has no SQLCipher, so there (and in tests) the queue
// is kept in memory only: nothing business-related reaches the phone's storage unencrypted.
import Constants, { ExecutionEnvironment } from 'expo-constants';
import * as Crypto from 'expo-crypto';
import * as SecureStore from 'expo-secure-store';
import * as SQLite from 'expo-sqlite';

import { type QueueItem, type QueueStore, memoryStore } from '@/lib/queue';

/** The part of an expo-sqlite database this store uses. */
export type Db = Pick<SQLite.SQLiteDatabase, 'execAsync' | 'getFirstAsync' | 'getAllAsync' | 'runAsync' | 'closeAsync'>;

const NAME = 'offline-queue.db';
const KEY = 'offline-db-key';
const toHex = (bytes: Uint8Array) => Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');

/**
 * Unlock `db` with `hexKey` (32 random bytes) and use it only if SQLCipher really encrypts it; otherwise
 * close it and return null, so the caller keeps the queue in memory instead of writing it unencrypted.
 */
export async function encryptedStore(db: Db, hexKey: string): Promise<QueueStore | null> {
  if (!/^[0-9a-f]{64}$/.test(hexKey)) throw new Error('invalid offline key');
  await db.execAsync(`PRAGMA key = "x'${hexKey}'";`); // must come before anything else touches the file
  const cipher = await db.getFirstAsync<{ cipher_version?: string }>('PRAGMA cipher_version;');
  if (!cipher?.cipher_version) {
    await db.closeAsync();
    return null;
  }
  await db.execAsync(
    'CREATE TABLE IF NOT EXISTS queue (id TEXT PRIMARY KEY NOT NULL, created_at INTEGER NOT NULL, body TEXT NOT NULL);',
  );
  return {
    all: async () =>
      (await db.getAllAsync<{ body: string }>('SELECT body FROM queue ORDER BY created_at')).map(
        (row) => JSON.parse(row.body) as QueueItem,
      ),
    put: async (item) => {
      await db.runAsync(
        'INSERT OR REPLACE INTO queue (id, created_at, body) VALUES (?, ?, ?)',
        item.id,
        item.createdAt,
        JSON.stringify(item),
      );
    },
    remove: async (id) => {
      await db.runAsync('DELETE FROM queue WHERE id = ?', id);
    },
    clear: async () => {
      await db.runAsync('DELETE FROM queue');
    },
  };
}

async function open(): Promise<QueueStore> {
  if (Constants.executionEnvironment === ExecutionEnvironment.StoreClient) return memoryStore(); // Expo Go
  let key = await SecureStore.getItemAsync(KEY);
  if (!key) {
    // A new key cannot read an old file: start a fresh one (it held at most a day of unsent items).
    key = toHex(Crypto.getRandomBytes(32));
    await SecureStore.setItemAsync(KEY, key, { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY });
    await SQLite.deleteDatabaseAsync(NAME).catch(() => {});
  }
  const hexKey = key;
  const tryOpen = async () => {
    const db = await SQLite.openDatabaseAsync(NAME);
    try {
      return await encryptedStore(db, hexKey);
    } catch (e) {
      await db.closeAsync().catch(() => {});
      throw e;
    }
  };
  try {
    return (await tryOpen()) ?? memoryStore();
  } catch {
    // The file does not open with this key (for example restored from another phone): replace it.
    await SQLite.deleteDatabaseAsync(NAME).catch(() => {});
    return (await tryOpen()) ?? memoryStore();
  }
}

let opened: Promise<QueueStore> | null = null;

/** The queue's store, opened once. Falls back to memory if the encrypted database cannot be used. */
export function offlineStore(): Promise<QueueStore> {
  opened ??= open().catch(() => memoryStore());
  return opened;
}

/** Sign-out (and later remote wipe): remove every queued item from the phone. */
export async function wipeOffline() {
  await (await offlineStore()).clear();
}
