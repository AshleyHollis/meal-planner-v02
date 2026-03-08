'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import {
  createConfirmedListSnapshot,
  createOfflineConflictRecord,
  createOfflineSyncStore,
  createQueuedMutationRecord,
  EMPTY_OFFLINE_QUEUE_STATE,
} from '../_lib/offline-sync';
import type {
  GroceryList,
  OfflineConflictRecord,
  OfflineConfirmedListSnapshot,
  OfflineQueueState,
  OfflineSyncMutationRecord,
  OfflineSyncScope,
  QueueableSyncMutation,
  SyncConflictDetail,
  SyncMutationOutcome,
} from '../_lib/types';

type QueueMutationInput = QueueableSyncMutation & {
  scope: OfflineSyncScope;
};

type OfflineSyncContextValue = {
  ready: boolean;
  online: boolean;
  rememberConfirmedList: (list: GroceryList) => Promise<OfflineConfirmedListSnapshot | null>;
  getLatestConfirmedListSnapshot: (
    householdId: string
  ) => Promise<OfflineConfirmedListSnapshot | null>;
  getQueueState: (householdId: string) => Promise<OfflineQueueState>;
  listQueuedMutations: (householdId: string) => Promise<OfflineSyncMutationRecord[]>;
  enqueueMutation: (
    mutation: QueueMutationInput,
    queuedAt?: string
  ) => Promise<OfflineSyncMutationRecord>;
  markMutationSyncing: (
    clientMutationId: string,
    attemptedAt?: string
  ) => Promise<OfflineSyncMutationRecord | null>;
  recordRetryableFailure: (
    clientMutationId: string,
    message: string,
    attemptedAt?: string
  ) => Promise<OfflineSyncMutationRecord | null>;
  recordSyncOutcome: (
    clientMutationId: string,
    outcome: SyncMutationOutcome,
    updatedAt?: string
  ) => Promise<OfflineSyncMutationRecord | null>;
  preserveConflict: (
    conflict: SyncConflictDetail,
    scope: OfflineSyncScope,
    localMutationId?: string,
    storedAt?: string
  ) => Promise<OfflineConflictRecord>;
  listConflicts: (householdId: string) => Promise<OfflineConflictRecord[]>;
  clearConflict: (conflictId: string) => Promise<void>;
  clearQueuedMutation: (clientMutationId: string) => Promise<void>;
};

const OfflineSyncContext = createContext<OfflineSyncContextValue>({
  ready: false,
  online: true,
  rememberConfirmedList: async () => null,
  getLatestConfirmedListSnapshot: async () => null,
  getQueueState: async () => EMPTY_OFFLINE_QUEUE_STATE,
  listQueuedMutations: async () => [],
  enqueueMutation: async () => {
    throw new Error('Offline sync runtime is not ready.');
  },
  markMutationSyncing: async () => null,
  recordRetryableFailure: async () => null,
  recordSyncOutcome: async () => null,
  preserveConflict: async (conflict, scope, _localMutationId, storedAt) =>
    createOfflineConflictRecord(
      {
        conflict,
        scope,
        localMutation: null,
      },
      storedAt
    ),
  listConflicts: async () => [],
  clearConflict: async () => {},
  clearQueuedMutation: async () => {},
});

export function OfflineSyncProvider({ children }: { children: ReactNode }) {
  const store = useMemo(() => createOfflineSyncStore(), []);
  const [ready, setReady] = useState(false);
  const [online, setOnline] = useState(() =>
    typeof navigator === 'undefined' ? true : navigator.onLine
  );

  useEffect(() => {
    setReady(true);

    if (typeof window === 'undefined') {
      return;
    }

    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const rememberConfirmedList = useCallback(
    async (list: GroceryList) => {
      const snapshot = createConfirmedListSnapshot(list);

      if (!snapshot) {
        return null;
      }

      await store.saveConfirmedListSnapshot(snapshot);
      return snapshot;
    },
    [store]
  );

  const getLatestConfirmedListSnapshot = useCallback(
    async (householdId: string) => store.getLatestConfirmedListSnapshot(householdId),
    [store]
  );

  const getQueueState = useCallback(
    async (householdId: string) => store.getQueueState(householdId),
    [store]
  );

  const listQueuedMutations = useCallback(
    async (householdId: string) => store.listQueuedMutations(householdId),
    [store]
  );

  const enqueueMutation = useCallback(
    async (mutation: QueueMutationInput, queuedAt?: string) => {
      const record = createQueuedMutationRecord(
        mutation,
        queuedAt ?? new Date().toISOString()
      );
      await store.enqueueMutation(record);
      return record;
    },
    [store]
  );

  const markMutationSyncing = useCallback(
    async (clientMutationId: string, attemptedAt?: string) =>
      store.markMutationSyncing(clientMutationId, attemptedAt),
    [store]
  );

  const recordRetryableFailure = useCallback(
    async (clientMutationId: string, message: string, attemptedAt?: string) =>
      store.recordRetryableFailure(clientMutationId, message, attemptedAt),
    [store]
  );

  const recordSyncOutcome = useCallback(
    async (
      clientMutationId: string,
      outcome: SyncMutationOutcome,
      updatedAt?: string
    ) => store.recordSyncOutcome(clientMutationId, outcome, updatedAt),
    [store]
  );

  const preserveConflict = useCallback(
    async (
      conflict: SyncConflictDetail,
      scope: OfflineSyncScope,
      localMutationId?: string,
      storedAt?: string
    ) => {
      const localMutation = localMutationId
        ? await store.getQueuedMutation(localMutationId)
        : null;
      const record = createOfflineConflictRecord(
        {
          conflict,
          scope,
          localMutation,
        },
        storedAt
      );
      await store.saveConflict(record);
      return record;
    },
    [store]
  );

  const listConflicts = useCallback(
    async (householdId: string) => store.listConflicts(householdId),
    [store]
  );

  const clearConflict = useCallback(
    async (conflictId: string) => store.clearConflict(conflictId),
    [store]
  );

  const clearQueuedMutation = useCallback(
    async (clientMutationId: string) => store.clearQueuedMutation(clientMutationId),
    [store]
  );

  return (
    <OfflineSyncContext.Provider
      value={{
        ready,
        online,
        rememberConfirmedList,
        getLatestConfirmedListSnapshot,
        getQueueState,
        listQueuedMutations,
        enqueueMutation,
        markMutationSyncing,
        recordRetryableFailure,
        recordSyncOutcome,
        preserveConflict,
        listConflicts,
        clearConflict,
        clearQueuedMutation,
      }}
    >
      {children}
    </OfflineSyncContext.Provider>
  );
}

export function useOfflineSyncContext() {
  return useContext(OfflineSyncContext);
}
