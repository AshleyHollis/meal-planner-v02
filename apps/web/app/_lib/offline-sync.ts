import type {
  GroceryConfirmedListBootstrap,
  GroceryList,
  GroceryListStatus,
  OfflineConflictRecord,
  OfflineConfirmedListSnapshot,
  OfflineInventorySnapshot,
  OfflineMealPlanContext,
  OfflineQueueState,
  OfflineSyncMutationRecord,
  OfflineSyncScope,
  QueueableSyncMutation,
  SyncAggregateRef,
  SyncConflictDetail,
  SyncMutationOutcome,
  SyncStatus,
} from './types';

const OFFLINE_SYNC_DATABASE_NAME = 'meal-planner-offline-sync';
const OFFLINE_SYNC_DATABASE_VERSION = 1;

const STORE_NAMES = {
  confirmedSnapshots: 'confirmedSnapshots',
  mealPlanContexts: 'mealPlanContexts',
  inventorySnapshots: 'inventorySnapshots',
  queuedMutations: 'queuedMutations',
  conflicts: 'conflicts',
} as const;

type StoreName = (typeof STORE_NAMES)[keyof typeof STORE_NAMES];

type StoredConfirmedListSnapshot = Omit<
  OfflineConfirmedListSnapshot,
  'mealPlanContext' | 'inventorySnapshot'
>;

type QueueableSyncMutationInput = QueueableSyncMutation & {
  scope: OfflineSyncScope;
};

type ConflictRecordInput = {
  conflict: SyncConflictDetail;
  scope: OfflineSyncScope;
  localMutation: OfflineSyncMutationRecord | null;
};

type OfflineRecordDriver = {
  get<T>(storeName: StoreName, key: string): Promise<T | null>;
  getAll<T>(storeName: StoreName): Promise<T[]>;
  put<T>(storeName: StoreName, key: string, value: T): Promise<void>;
  delete(storeName: StoreName, key: string): Promise<void>;
};

export const EMPTY_OFFLINE_QUEUE_STATE: OfflineQueueState = {
  queuedCount: 0,
  retryingCount: 0,
  failedRetryableCount: 0,
  reviewRequiredCount: 0,
  conflictCount: 0,
  latestSnapshotSavedAt: null,
};

function cloneValue<T>(value: T): T {
  if (typeof globalThis.structuredClone === 'function') {
    return globalThis.structuredClone(value);
  }

  return JSON.parse(JSON.stringify(value)) as T;
}

function sortNewestFirst<T extends { savedAt?: string; storedAt?: string; createdAt?: string }>(
  values: T[]
): T[] {
  return [...values].sort((left, right) => {
    const leftValue = left.savedAt ?? left.storedAt ?? left.createdAt ?? '';
    const rightValue = right.savedAt ?? right.storedAt ?? right.createdAt ?? '';
    return rightValue.localeCompare(leftValue);
  });
}

function sortOldestFirst<T extends { createdAt: string }>(values: T[]): T[] {
  return [...values].sort((left, right) => left.createdAt.localeCompare(right.createdAt));
}

function createStoreMap(): Map<StoreName, Map<string, unknown>> {
  return new Map<StoreName, Map<string, unknown>>([
    [STORE_NAMES.confirmedSnapshots, new Map()],
    [STORE_NAMES.mealPlanContexts, new Map()],
    [STORE_NAMES.inventorySnapshots, new Map()],
    [STORE_NAMES.queuedMutations, new Map()],
    [STORE_NAMES.conflicts, new Map()],
  ]);
}

export function createInMemoryOfflineSyncDriver(): OfflineRecordDriver {
  const stores = createStoreMap();

  return {
    async get<T>(storeName: StoreName, key: string): Promise<T | null> {
      const value = stores.get(storeName)?.get(key);
      return value === undefined ? null : cloneValue(value as T);
    },

    async getAll<T>(storeName: StoreName): Promise<T[]> {
      const values = Array.from(stores.get(storeName)?.values() ?? []);
      return values.map((value) => cloneValue(value as T));
    },

    async put<T>(storeName: StoreName, key: string, value: T): Promise<void> {
      stores.get(storeName)?.set(key, cloneValue(value));
    },

    async delete(storeName: StoreName, key: string): Promise<void> {
      stores.get(storeName)?.delete(key);
    },
  };
}

function readRequest<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error('IndexedDB request failed.'));
  });
}

function awaitTransaction(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error ?? new Error('IndexedDB transaction failed.'));
    transaction.onabort = () => reject(transaction.error ?? new Error('IndexedDB transaction aborted.'));
  });
}

export function createIndexedDbOfflineSyncDriver(indexedDb: IDBFactory): OfflineRecordDriver {
  let databasePromise: Promise<IDBDatabase> | null = null;

  function getDatabase(): Promise<IDBDatabase> {
    if (!databasePromise) {
      databasePromise = new Promise((resolve, reject) => {
        const request = indexedDb.open(
          OFFLINE_SYNC_DATABASE_NAME,
          OFFLINE_SYNC_DATABASE_VERSION
        );

        request.onupgradeneeded = () => {
          const database = request.result;
          for (const storeName of Object.values(STORE_NAMES)) {
            if (!database.objectStoreNames.contains(storeName)) {
              database.createObjectStore(storeName);
            }
          }
        };

        request.onsuccess = () => resolve(request.result);
        request.onerror = () =>
          reject(request.error ?? new Error('Could not open IndexedDB database.'));
      });
    }

    return databasePromise;
  }

  return {
    async get<T>(storeName: StoreName, key: string): Promise<T | null> {
      const database = await getDatabase();
      const transaction = database.transaction(storeName, 'readonly');
      const store = transaction.objectStore(storeName);
      const value = await readRequest(store.get(key));
      await awaitTransaction(transaction);
      return value === undefined ? null : cloneValue(value as T);
    },

    async getAll<T>(storeName: StoreName): Promise<T[]> {
      const database = await getDatabase();
      const transaction = database.transaction(storeName, 'readonly');
      const store = transaction.objectStore(storeName);
      const values = await readRequest(store.getAll());
      await awaitTransaction(transaction);
      return (values as T[]).map((value) => cloneValue(value));
    },

    async put<T>(storeName: StoreName, key: string, value: T): Promise<void> {
      const database = await getDatabase();
      const transaction = database.transaction(storeName, 'readwrite');
      const store = transaction.objectStore(storeName);
      store.put(cloneValue(value), key);
      await awaitTransaction(transaction);
    },

    async delete(storeName: StoreName, key: string): Promise<void> {
      const database = await getDatabase();
      const transaction = database.transaction(storeName, 'readwrite');
      const store = transaction.objectStore(storeName);
      store.delete(key);
      await awaitTransaction(transaction);
    },
  };
}

export function createDefaultOfflineSyncDriver(): OfflineRecordDriver {
  if (typeof indexedDB !== 'undefined') {
    return createIndexedDbOfflineSyncDriver(indexedDB);
  }

  return createInMemoryOfflineSyncDriver();
}

export function isConfirmedListSnapshotStatus(status: GroceryListStatus): boolean {
  return (
    status === 'confirmed' ||
    status === 'trip_in_progress' ||
    status === 'trip_complete_pending_reconciliation'
  );
}

export function getOfflineSnapshotKey(scope: OfflineSyncScope): string {
  return `${scope.householdId}:${scope.groceryListVersionId}`;
}

export function createOfflineSyncScope(list: GroceryList): OfflineSyncScope | null {
  if (!isConfirmedListSnapshotStatus(list.status) || !list.currentVersionId) {
    return null;
  }

  const aggregate: SyncAggregateRef = {
    aggregateType: 'grocery_list',
    aggregateId: list.groceryListId,
    aggregateVersion: list.currentVersionNumber,
    provisionalAggregateId: null,
  };

  return {
    householdId: list.householdId,
    groceryListId: list.groceryListId,
    groceryListVersionId: list.currentVersionId,
    planPeriodStart: list.planPeriodStart,
    tripState: list.tripState,
    aggregate,
  };
}

export function createConfirmedListBootstrap(
  list: GroceryList,
  savedAt = new Date().toISOString()
): GroceryConfirmedListBootstrap | null {
  const scope = createOfflineSyncScope(list);

  if (!scope) {
    return null;
  }

  return {
    householdId: list.householdId,
    groceryListId: list.groceryListId,
    groceryListVersionId: list.currentVersionId ?? scope.groceryListVersionId,
    groceryListStatus: list.status,
    tripState: list.tripState,
    aggregate: scope.aggregate,
    confirmedAt: list.confirmedAt ?? savedAt,
    confirmedPlanVersion: list.confirmedPlanVersion,
    inventorySnapshotReference: list.inventorySnapshotReference,
    incompleteSlotWarnings: list.incompleteSlotWarnings,
    lines: list.lines,
  };
}

export function createOfflineMealPlanContext(
  list: GroceryList,
  scope: OfflineSyncScope,
  savedAt = new Date().toISOString()
): OfflineMealPlanContext {
  return {
    snapshotKey: getOfflineSnapshotKey(scope),
    householdId: scope.householdId,
    groceryListId: scope.groceryListId,
    groceryListVersionId: scope.groceryListVersionId,
    planPeriodStart: list.planPeriodStart,
    planPeriodEnd: list.planPeriodEnd,
    derivedFromPlanId: list.derivedFromPlanId,
    confirmedPlanVersion: list.confirmedPlanVersion,
    savedAt,
  };
}

export function createOfflineInventorySnapshot(
  list: GroceryList,
  scope: OfflineSyncScope,
  savedAt = new Date().toISOString()
): OfflineInventorySnapshot {
  return {
    snapshotKey: getOfflineSnapshotKey(scope),
    householdId: scope.householdId,
    groceryListId: scope.groceryListId,
    groceryListVersionId: scope.groceryListVersionId,
    inventorySnapshotReference: list.inventorySnapshotReference,
    savedAt,
  };
}

export function createConfirmedListSnapshot(
  list: GroceryList,
  savedAt = new Date().toISOString()
): OfflineConfirmedListSnapshot | null {
  const scope = createOfflineSyncScope(list);
  const bootstrap = createConfirmedListBootstrap(list, savedAt);

  if (!scope || !bootstrap) {
    return null;
  }

  return {
    snapshotKey: getOfflineSnapshotKey(scope),
    scope,
    savedAt,
    bootstrap,
    groceryList: cloneValue(list),
    mealPlanContext: createOfflineMealPlanContext(list, scope, savedAt),
    inventorySnapshot: createOfflineInventorySnapshot(list, scope, savedAt),
  };
}

export function createQueuedMutationRecord(
  mutation: QueueableSyncMutationInput,
  createdAt = new Date().toISOString()
): OfflineSyncMutationRecord {
  return {
    ...cloneValue(mutation),
    snapshotKey: getOfflineSnapshotKey(mutation.scope),
    retryCount: 0,
    lastAttemptAt: null,
    nextRetryAt: null,
    lastError: null,
    createdAt,
    updatedAt: createdAt,
  };
}

export function getRetryDelayMs(retryCount: number): number {
  const step = Math.max(1, retryCount);
  return Math.min(30_000 * 2 ** (step - 1), 5 * 60_000);
}

export function markQueuedMutationSyncing(
  mutation: OfflineSyncMutationRecord,
  attemptedAt = new Date().toISOString()
): OfflineSyncMutationRecord {
  return {
    ...mutation,
    localQueueStatus: 'syncing',
    lastAttemptAt: attemptedAt,
    updatedAt: attemptedAt,
  };
}

export function markQueuedMutationRetryable(
  mutation: OfflineSyncMutationRecord,
  message: string,
  attemptedAt = new Date().toISOString()
): OfflineSyncMutationRecord {
  const retryCount = mutation.retryCount + 1;
  const nextRetryAt = new Date(
    new Date(attemptedAt).getTime() + getRetryDelayMs(retryCount)
  ).toISOString();

  return {
    ...mutation,
    retryCount,
    lastAttemptAt: attemptedAt,
    nextRetryAt,
    lastError: message,
    localQueueStatus: 'retrying',
    updatedAt: attemptedAt,
  };
}

export function applySyncOutcomeToMutation(
  mutation: OfflineSyncMutationRecord,
  outcome: SyncMutationOutcome,
  updatedAt = new Date().toISOString()
): OfflineSyncMutationRecord {
  const nextStatus: SyncStatus =
    outcome.outcome === 'failed_retryable'
      ? 'failed_retryable'
      : outcome.outcome.startsWith('review_required')
        ? 'review_required'
        : 'synced';

  return {
    ...mutation,
    aggregateType: outcome.aggregate.aggregateType,
    aggregateId: outcome.aggregate.aggregateId || mutation.aggregateId,
    provisionalAggregateId:
      outcome.aggregate.provisionalAggregateId ?? mutation.provisionalAggregateId,
    baseServerVersion:
      outcome.authoritativeServerVersion ?? outcome.aggregate.aggregateVersion ?? mutation.baseServerVersion,
    localQueueStatus: nextStatus,
    lastAttemptAt: updatedAt,
    nextRetryAt: nextStatus === 'failed_retryable' ? mutation.nextRetryAt : null,
    lastError: nextStatus === 'failed_retryable' ? mutation.lastError : null,
    updatedAt,
  };
}

export function createOfflineConflictRecord(
  input: ConflictRecordInput,
  storedAt = new Date().toISOString()
): OfflineConflictRecord {
  return {
    conflict: cloneValue(input.conflict),
    scope: cloneValue(input.scope),
    snapshotKey: getOfflineSnapshotKey(input.scope),
    localMutation: input.localMutation ? cloneValue(input.localMutation) : null,
    storedAt,
    updatedAt: storedAt,
  };
}

export function getOfflineSyncStatus(
  queueState: OfflineQueueState,
  online: boolean
): SyncStatus {
  if (!online) {
    return 'offline';
  }
  if (queueState.reviewRequiredCount > 0 || queueState.conflictCount > 0) {
    return 'review_required';
  }
  if (queueState.retryingCount > 0) {
    return 'retrying';
  }
  if (queueState.failedRetryableCount > 0) {
    return 'failed_retryable';
  }
  if (queueState.queuedCount > 0) {
    return 'queued_offline';
  }
  return 'idle';
}

async function assembleConfirmedListSnapshot(
  driver: OfflineRecordDriver,
  snapshot: StoredConfirmedListSnapshot | null
): Promise<OfflineConfirmedListSnapshot | null> {
  if (!snapshot) {
    return null;
  }

  const [mealPlanContext, inventorySnapshot] = await Promise.all([
    driver.get<OfflineMealPlanContext>(STORE_NAMES.mealPlanContexts, snapshot.snapshotKey),
    driver.get<OfflineInventorySnapshot>(STORE_NAMES.inventorySnapshots, snapshot.snapshotKey),
  ]);

  return {
    ...snapshot,
    mealPlanContext:
      mealPlanContext ??
      createOfflineMealPlanContext(snapshot.groceryList, snapshot.scope, snapshot.savedAt),
    inventorySnapshot:
      inventorySnapshot ??
      createOfflineInventorySnapshot(snapshot.groceryList, snapshot.scope, snapshot.savedAt),
  };
}

export type OfflineSyncStore = ReturnType<typeof createOfflineSyncStore>;

export function createOfflineSyncStore(driver: OfflineRecordDriver = createDefaultOfflineSyncDriver()) {
  return {
    async saveConfirmedListSnapshot(snapshot: OfflineConfirmedListSnapshot): Promise<void> {
      const storedSnapshot: StoredConfirmedListSnapshot = {
        snapshotKey: snapshot.snapshotKey,
        scope: snapshot.scope,
        savedAt: snapshot.savedAt,
        bootstrap: snapshot.bootstrap,
        groceryList: snapshot.groceryList,
      };

      await Promise.all([
        driver.put(STORE_NAMES.confirmedSnapshots, snapshot.snapshotKey, storedSnapshot),
        driver.put(
          STORE_NAMES.mealPlanContexts,
          snapshot.mealPlanContext.snapshotKey,
          snapshot.mealPlanContext
        ),
        driver.put(
          STORE_NAMES.inventorySnapshots,
          snapshot.inventorySnapshot.snapshotKey,
          snapshot.inventorySnapshot
        ),
      ]);
    },

    async getConfirmedListSnapshot(snapshotKey: string): Promise<OfflineConfirmedListSnapshot | null> {
      const snapshot = await driver.get<StoredConfirmedListSnapshot>(
        STORE_NAMES.confirmedSnapshots,
        snapshotKey
      );
      return assembleConfirmedListSnapshot(driver, snapshot);
    },

    async getLatestConfirmedListSnapshot(
      householdId: string
    ): Promise<OfflineConfirmedListSnapshot | null> {
      const snapshots = await driver.getAll<StoredConfirmedListSnapshot>(
        STORE_NAMES.confirmedSnapshots
      );
      const latest = sortNewestFirst(
        snapshots.filter((snapshot) => snapshot.scope.householdId === householdId)
      )[0];

      return assembleConfirmedListSnapshot(driver, latest ?? null);
    },

    async listConfirmedListSnapshots(householdId: string): Promise<OfflineConfirmedListSnapshot[]> {
      const snapshots = await driver.getAll<StoredConfirmedListSnapshot>(
        STORE_NAMES.confirmedSnapshots
      );
      const assembled = await Promise.all(
        sortNewestFirst(
          snapshots.filter((snapshot) => snapshot.scope.householdId === householdId)
        ).map((snapshot) => assembleConfirmedListSnapshot(driver, snapshot))
      );

      return assembled.filter(
        (snapshot): snapshot is OfflineConfirmedListSnapshot => snapshot !== null
      );
    },

    async enqueueMutation(mutation: OfflineSyncMutationRecord): Promise<void> {
      await driver.put(STORE_NAMES.queuedMutations, mutation.clientMutationId, mutation);
    },

    async getQueuedMutation(clientMutationId: string): Promise<OfflineSyncMutationRecord | null> {
      return driver.get<OfflineSyncMutationRecord>(STORE_NAMES.queuedMutations, clientMutationId);
    },

    async listQueuedMutations(householdId: string): Promise<OfflineSyncMutationRecord[]> {
      const mutations = await driver.getAll<OfflineSyncMutationRecord>(
        STORE_NAMES.queuedMutations
      );
      return sortOldestFirst(
        mutations.filter((mutation) => mutation.householdId === householdId)
      );
    },

    async saveConflict(conflict: OfflineConflictRecord): Promise<void> {
      await driver.put(STORE_NAMES.conflicts, conflict.conflict.conflictId, conflict);
    },

    async listConflicts(householdId: string): Promise<OfflineConflictRecord[]> {
      const conflicts = await driver.getAll<OfflineConflictRecord>(STORE_NAMES.conflicts);
      return sortNewestFirst(
        conflicts.filter((conflict) => conflict.scope.householdId === householdId)
      );
    },

    async clearConflict(conflictId: string): Promise<void> {
      await driver.delete(STORE_NAMES.conflicts, conflictId);
    },

    async markMutationSyncing(
      clientMutationId: string,
      attemptedAt = new Date().toISOString()
    ): Promise<OfflineSyncMutationRecord | null> {
      const mutation = await this.getQueuedMutation(clientMutationId);
      if (!mutation) {
        return null;
      }

      const updated = markQueuedMutationSyncing(mutation, attemptedAt);
      await this.enqueueMutation(updated);
      return updated;
    },

    async recordRetryableFailure(
      clientMutationId: string,
      message: string,
      attemptedAt = new Date().toISOString()
    ): Promise<OfflineSyncMutationRecord | null> {
      const mutation = await this.getQueuedMutation(clientMutationId);
      if (!mutation) {
        return null;
      }

      const updated = markQueuedMutationRetryable(mutation, message, attemptedAt);
      await this.enqueueMutation(updated);
      return updated;
    },

    async recordSyncOutcome(
      clientMutationId: string,
      outcome: SyncMutationOutcome,
      updatedAt = new Date().toISOString()
    ): Promise<OfflineSyncMutationRecord | null> {
      const mutation = await this.getQueuedMutation(clientMutationId);
      if (!mutation) {
        return null;
      }

      const updated = applySyncOutcomeToMutation(mutation, outcome, updatedAt);
      await this.enqueueMutation(updated);
      return updated;
    },

    async getQueueState(householdId: string): Promise<OfflineQueueState> {
      const [mutations, conflicts, latestSnapshot] = await Promise.all([
        this.listQueuedMutations(householdId),
        this.listConflicts(householdId),
        this.getLatestConfirmedListSnapshot(householdId),
      ]);

      const queueState = { ...EMPTY_OFFLINE_QUEUE_STATE };
      queueState.latestSnapshotSavedAt = latestSnapshot?.savedAt ?? null;

      for (const mutation of mutations) {
        switch (mutation.localQueueStatus) {
          case 'queued_offline':
          case 'syncing':
            queueState.queuedCount += 1;
            break;
          case 'retrying':
            queueState.retryingCount += 1;
            break;
          case 'failed_retryable':
            queueState.failedRetryableCount += 1;
            break;
          case 'review_required':
            queueState.reviewRequiredCount += 1;
            break;
          default:
            break;
        }
      }

      queueState.conflictCount = conflicts.filter(
        (conflict) => conflict.conflict.resolutionStatus === 'pending'
      ).length;

      return queueState;
    },

    async clearQueuedMutation(clientMutationId: string): Promise<void> {
      await driver.delete(STORE_NAMES.queuedMutations, clientMutationId);
    },
  };
}
