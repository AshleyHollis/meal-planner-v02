'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ApiError } from '../../_lib/api';
import {
  addAdHocLine,
  adjustGroceryLine,
  confirmGroceryList,
  deriveGroceryList,
  getGroceryList,
  getSyncConflict,
  rederiveGroceryList,
  removeGroceryLine,
  resolveSyncConflictKeepMine,
  resolveSyncConflictUseServer,
  uploadSyncMutations,
} from '../../_lib/grocery-api';
import {
  EMPTY_OFFLINE_QUEUE_STATE,
  createOfflineSyncScope,
  getOfflineSyncStatus,
  isConfirmedListSnapshotStatus,
} from '../../_lib/offline-sync';
import {
  getConflictOutcomeDescription,
  getConflictOutcomeLabel,
  getActiveLines,
  getConfirmationSummary,
  getRemovedLines,
  getReviewHeadline,
  getReviewSummary,
} from '../../_lib/grocery-ui';
import {
  applyOptimisticTripAdHocLine,
  applyOptimisticTripCompletion,
  applyOptimisticTripQuantity,
  getTripProgressSummary,
} from '../../_lib/trip-mode';
import type {
  GroceryLine,
  GroceryList,
  GroceryListStatus,
  OfflineConflictRecord,
  OfflineQueueState,
  OfflineSyncMutationRecord,
  SyncConflictDetail,
  SyncResolutionAction,
  SyncStatus,
} from '../../_lib/types';
import { useOfflineSync } from '../../_hooks/useOfflineSync';
import { useSession } from '../../_hooks/useSession';
import { LoadingState } from '../../_components/LoadingState';
import { ErrorState } from '../../_components/ErrorState';
import { EmptyState } from '../../_components/EmptyState';
import { SyncStatusBadge } from '../../_components/SyncStatusBadge';
import { randomUUID } from '../../_lib/uuid';
import { GroceryLineRow } from './GroceryLineRow';
import { AdHocItemForm } from './AdHocItemForm';
import { SyncConflictReviewModal } from './SyncConflictReviewModal';
import styles from './GroceryView.module.css';

function isoMonday(): string {
  const d = new Date();
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return d.toISOString().slice(0, 10);
}

type AsyncState<T> =
  | { status: 'loading' }
  | { status: 'ok'; data: T }
  | { status: 'error'; message: string };

const STATUS_LABELS: Record<GroceryListStatus, string> = {
  no_plan_confirmed: 'No confirmed plan',
  deriving: 'Deriving draft',
  draft: 'Draft list',
  stale_draft: 'Stale draft',
  confirming: 'Confirming',
  confirmed: 'Confirmed list',
  trip_in_progress: 'Trip sync active',
  trip_complete_pending_reconciliation: 'Trip results pending reconciliation',
};

const PENDING_QUEUE_STATUSES = new Set<SyncStatus>([
  'queued_offline',
  'syncing',
  'retrying',
  'failed_retryable',
]);

function canEditList(status: GroceryListStatus): boolean {
  return status === 'draft' || status === 'stale_draft';
}

function canRefreshList(status: GroceryListStatus): boolean {
  return status !== 'deriving' && status !== 'confirming';
}

function getRefreshLabel(status: GroceryListStatus): string {
  if (
    status === 'confirmed' ||
    status === 'trip_in_progress' ||
    status === 'trip_complete_pending_reconciliation'
  ) {
    return 'Create refreshed draft';
  }
  return 'Refresh draft';
}

function getStatusMessage(list: GroceryList): string | null {
  switch (list.status) {
    case 'deriving':
      return 'The backend is deriving this draft from the confirmed plan and current inventory snapshot.';
    case 'stale_draft':
      return 'Inventory or the confirmed plan changed after this draft was derived. Review what changed before you confirm this version.';
    case 'confirmed':
      return 'This confirmed list is ready for phone-first trip mode. Local edits stay on this device until they sync safely.';
    case 'trip_in_progress':
      return 'Trip mode is active for this confirmed snapshot. Remaining quantities, check-offs, and ad hoc items stay tied to the locked grocery-list version.';
    case 'trip_complete_pending_reconciliation':
      return 'Trip results are saved against this confirmed snapshot. Inventory reconciliation remains the next downstream step for this version.';
    case 'no_plan_confirmed':
      return 'Confirm a weekly plan before deriving grocery needs.';
    default:
      return 'Review derived lines, inventory offsets, warnings, and any quantity overrides before confirming the list.';
  }
}

function formatTimestamp(value: string | null): string | null {
  if (!value) {
    return null;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return parsed.toLocaleString();
}

function getMutationSurfaceCopy(status: SyncStatus): string | null {
  switch (status) {
    case 'queued_offline':
      return 'Saved offline on this phone.';
    case 'syncing':
      return 'Syncing now.';
    case 'retrying':
      return 'Waiting to retry.';
    case 'failed_retryable':
      return 'Retry needed.';
    case 'review_required':
      return 'Needs conflict review.';
    default:
      return null;
  }
}

function toUploadRecord(record: OfflineSyncMutationRecord) {
  return {
    client_mutation_id: record.clientMutationId,
    household_id: record.householdId,
    actor_id: record.actorId,
    aggregate_type: record.aggregateType,
    aggregate_id: record.aggregateId,
    provisional_aggregate_id: record.provisionalAggregateId,
    mutation_type: record.mutationType,
    payload: record.payload,
    base_server_version: record.baseServerVersion,
    device_timestamp: record.deviceTimestamp,
    local_queue_status: record.localQueueStatus,
  };
}

export function GroceryView() {
  const { user, session, refresh } = useSession();
  const {
    clearQueuedMutation,
    clearConflict,
    enqueueMutation,
    getLatestConfirmedListSnapshot,
    getQueueState,
    listConflicts,
    listQueuedMutations,
    markMutationSyncing,
    online,
    ready: offlineReady,
    preserveConflict,
    recordRetryableFailure,
    recordSyncOutcome,
    rememberConfirmedList,
  } = useOfflineSync();
  const [periodStart] = useState(() => isoMonday());
  const [state, setState] = useState<AsyncState<GroceryList | null>>({
    status: 'loading',
  });
  const [syncStatus, setSyncStatus] = useState<SyncStatus>('idle');
  const [offlineQueueState, setOfflineQueueState] = useState<OfflineQueueState>(
    EMPTY_OFFLINE_QUEUE_STATE
  );
  const [queuedMutations, setQueuedMutations] = useState<OfflineSyncMutationRecord[]>([]);
  const [localConflicts, setLocalConflicts] = useState<OfflineConflictRecord[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [selectedConflictId, setSelectedConflictId] = useState<string | null>(null);
  const [selectedConflictDetail, setSelectedConflictDetail] = useState<SyncConflictDetail | null>(null);
  const [conflictDetailLoading, setConflictDetailLoading] = useState(false);
  const [conflictDetailMessage, setConflictDetailMessage] = useState<string | null>(null);
  const [resolvingConflict, setResolvingConflict] = useState<{
    conflictId: string;
    action: SyncResolutionAction;
  } | null>(null);
  const syncInFlight = useRef(false);

  const refreshOfflineRuntime = useCallback(
    async (householdId: string) => {
      if (!offlineReady) {
        setOfflineQueueState(EMPTY_OFFLINE_QUEUE_STATE);
        setQueuedMutations([]);
        setLocalConflicts([]);
        return;
      }

      const [nextQueueState, nextQueuedMutations, nextConflicts] = await Promise.all([
        getQueueState(householdId),
        listQueuedMutations(householdId),
        listConflicts(householdId),
      ]);
      setOfflineQueueState(nextQueueState);
      setQueuedMutations(nextQueuedMutations);
      setLocalConflicts(nextConflicts);
    },
    [getQueueState, listConflicts, listQueuedMutations, offlineReady]
  );

  const load = useCallback(async () => {
    if (!user) {
      setState({ status: 'ok', data: null });
      setOfflineQueueState(EMPTY_OFFLINE_QUEUE_STATE);
      setQueuedMutations([]);
      setLocalConflicts([]);
      setMessage(null);
      setSelectedConflictId(null);
      setSelectedConflictDetail(null);
      setConflictDetailMessage(null);
      return;
    }

    setState({ status: 'loading' });
    setMessage(null);
    try {
      const list = await getGroceryList(user.activeHouseholdId, periodStart);
      setState({ status: 'ok', data: list });

      if (list) {
        await rememberConfirmedList(list);
      }

      await refreshOfflineRuntime(user.activeHouseholdId);
    } catch {
      try {
        if (!offlineReady) {
          throw new Error('Offline store not ready.');
        }

        const snapshot = await getLatestConfirmedListSnapshot(user.activeHouseholdId);
        if (snapshot) {
          setState({ status: 'ok', data: snapshot.groceryList });
          await refreshOfflineRuntime(user.activeHouseholdId);
          setMessage(
            online
              ? 'Could not refresh the server copy. Showing the last confirmed shopping snapshot saved on this device.'
              : 'Offline — showing the last confirmed shopping snapshot saved on this device.'
          );
          return;
        }
      } catch {
        // Fall through to the standard load error below.
      }

      setState({ status: 'error', message: 'Could not load grocery list.' });
    }
  }, [
    getLatestConfirmedListSnapshot,
    offlineReady,
    online,
    periodStart,
    refreshOfflineRuntime,
    rememberConfirmedList,
    user,
  ]);

  const selectedConflictRecord = useMemo(
    () =>
      selectedConflictId
        ? localConflicts.find((conflict) => conflict.conflict.conflictId === selectedConflictId) ?? null
        : null,
    [localConflicts, selectedConflictId]
  );

  useEffect(() => {
    void load();
  }, [load]);

  const syncQueuedTripMutations = useCallback(
    async (householdId: string, successMessage?: string) => {
      if (!offlineReady || !online || syncInFlight.current || syncStatus === 'resolving') {
        return false;
      }

      const pending = (await listQueuedMutations(householdId)).filter((mutation) =>
        PENDING_QUEUE_STATUSES.has(mutation.localQueueStatus)
      );

      if (pending.length === 0) {
        await refreshOfflineRuntime(householdId);
        return false;
      }

      syncInFlight.current = true;
      setSyncStatus('syncing');

      try {
        await Promise.all(
          pending.map((mutation) => markMutationSyncing(mutation.clientMutationId))
        );

        const outcomes = await uploadSyncMutations(
          householdId,
          pending.map((mutation) => toUploadRecord(mutation))
        );

        let appliedCount = 0;
        let reviewCount = 0;

        for (const outcome of outcomes) {
          if (outcome.outcome === 'failed_retryable' || outcome.retryable) {
            await recordRetryableFailure(
              outcome.clientMutationId,
              'Could not sync this trip change yet. It will retry.'
            );
            continue;
          }

          if (outcome.outcome.startsWith('review_required') && outcome.conflictId) {
            reviewCount += 1;
            const updated = await recordSyncOutcome(outcome.clientMutationId, outcome);
            const detail = await getSyncConflict(householdId, outcome.conflictId);
            const scope = updated?.scope ?? pending.find((entry) => entry.clientMutationId === outcome.clientMutationId)?.scope;
            if (scope) {
              await preserveConflict(detail, scope, outcome.clientMutationId);
            }
            continue;
          }

          appliedCount += 1;
          await recordSyncOutcome(outcome.clientMutationId, outcome);
          await clearQueuedMutation(outcome.clientMutationId);
        }

        const refreshedList = await getGroceryList(householdId, periodStart);
        if (refreshedList) {
          setState({ status: 'ok', data: refreshedList });
          await rememberConfirmedList(refreshedList);
        }

        await refreshOfflineRuntime(householdId);
        setSyncStatus('idle');
        if (reviewCount > 0) {
          setMessage(
            `${reviewCount} trip change${reviewCount === 1 ? '' : 's'} now need review before syncing can continue.`
          );
        } else if (appliedCount > 0 && successMessage) {
          setMessage(successMessage);
        }

        return appliedCount > 0;
      } catch (error) {
        if (error instanceof ApiError && error.status < 500) {
          setSyncStatus('error');
          setMessage(error.message);
          await refreshOfflineRuntime(householdId);
          return false;
        }

        await Promise.all(
          pending.map((mutation) =>
            recordRetryableFailure(
              mutation.clientMutationId,
              'Connection dropped while syncing trip changes.'
            )
          )
        );
        await refreshOfflineRuntime(householdId);
        setSyncStatus(online ? 'retrying' : 'offline');
        setMessage('Trip changes are still saved on this phone and will retry when the connection stabilizes.');
        return false;
      } finally {
        syncInFlight.current = false;
      }
    },
    [
      clearQueuedMutation,
      listQueuedMutations,
      markMutationSyncing,
      offlineReady,
      online,
      periodStart,
      preserveConflict,
      recordRetryableFailure,
      recordSyncOutcome,
      refreshOfflineRuntime,
      rememberConfirmedList,
      syncStatus,
    ]
  );

  useEffect(() => {
    if (!user || !online || !offlineReady) {
      return;
    }

    void syncQueuedTripMutations(user.activeHouseholdId);
  }, [offlineReady, online, syncQueuedTripMutations, user]);

  useEffect(() => {
    if (!selectedConflictRecord) {
      setSelectedConflictDetail(null);
      setConflictDetailLoading(false);
      setConflictDetailMessage(null);
      return;
    }

    let cancelled = false;
    setSelectedConflictDetail(selectedConflictRecord.conflict);
    setConflictDetailMessage(
      online
        ? null
        : 'Showing the detail saved on this phone. Reconnect to refresh the latest server comparison.'
    );

    if (!user || !online) {
      return () => {
        cancelled = true;
      };
    }

    setConflictDetailLoading(true);
    void getSyncConflict(user.activeHouseholdId, selectedConflictRecord.conflict.conflictId)
      .then(async (detail) => {
        if (cancelled) {
          return;
        }
        setSelectedConflictDetail(detail);
        await preserveConflict(
          detail,
          selectedConflictRecord.scope,
          selectedConflictRecord.localMutation?.clientMutationId
        );
        await refreshOfflineRuntime(user.activeHouseholdId);
        if (!cancelled) {
          setConflictDetailMessage(null);
          setConflictDetailLoading(false);
        }
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        setConflictDetailLoading(false);
        setConflictDetailMessage(
          'Showing the saved detail from this phone because the latest server comparison could not be refreshed.'
        );
      });

    return () => {
      cancelled = true;
    };
  }, [online, preserveConflict, refreshOfflineRuntime, selectedConflictRecord, user]);

  async function runListMutation(
    action: () => Promise<GroceryList>,
    successMessage: string,
    options?: { onSuccess?: () => void }
  ) {
    setSyncStatus('syncing');
    setMessage(null);

    try {
      const nextList = await action();
      setState({ status: 'ok', data: nextList });
      await rememberConfirmedList(nextList);
      if (user) {
        await refreshOfflineRuntime(user.activeHouseholdId);
      }
      setSyncStatus('idle');
      setMessage(successMessage);
      options?.onSuccess?.();
    } catch (error) {
      if (
        error instanceof ApiError ||
        (typeof navigator !== 'undefined' && navigator.onLine)
      ) {
        setSyncStatus('error');
        setMessage(error instanceof Error ? error.message : 'Could not update the grocery list.');
        return;
      }

      setSyncStatus('offline');
      setMessage('Offline mutations for trip mode will queue on this device once SYNC-03 lands.');
    }
  }

  async function queueTripMutation(
    nextList: GroceryList,
    input: {
      aggregateType: 'grocery_line' | 'grocery_list';
      aggregateId: string | null;
      provisionalAggregateId: string | null;
      mutationType: string;
      payload: Record<string, unknown>;
    },
    queuedMessage: string,
    syncedMessage: string
  ) {
    if (!user || state.status !== 'ok' || !state.data) {
      return;
    }

    const scope = createOfflineSyncScope(state.data);
    if (!scope) {
      setSyncStatus('error');
      setMessage('Trip mode needs a confirmed-list snapshot before this phone can save changes.');
      return;
    }

    setState({ status: 'ok', data: nextList });
    await rememberConfirmedList(nextList);

    await enqueueMutation({
      clientMutationId: randomUUID(),
      householdId: user.activeHouseholdId,
      actorId: user.userId,
      aggregateType: input.aggregateType,
      aggregateId: input.aggregateId,
      provisionalAggregateId: input.provisionalAggregateId,
      mutationType: input.mutationType,
      payload: input.payload,
      baseServerVersion: state.data.currentVersionNumber,
      deviceTimestamp: new Date().toISOString(),
      localQueueStatus: 'queued_offline',
      scope,
    });

    await refreshOfflineRuntime(user.activeHouseholdId);

    if (!online) {
      setSyncStatus('offline');
      setMessage(queuedMessage);
      return;
    }

    setSyncStatus('queued_offline');
    await syncQueuedTripMutations(user.activeHouseholdId, syncedMessage);
  }

  async function handleResolveConflict(action: SyncResolutionAction) {
    if (!user || !selectedConflictRecord || !selectedConflictDetail) {
      return;
    }

    const conflictId = selectedConflictRecord.conflict.conflictId;
    const localMutationId =
      selectedConflictRecord.localMutation?.clientMutationId ??
      selectedConflictRecord.conflict.localMutationId;

    setResolvingConflict({ conflictId, action });
    setSyncStatus('resolving');
    setMessage(null);
    setConflictDetailMessage(null);

    try {
      const resolutionMutationId = randomUUID();
      const nextList =
        action === 'keep_mine'
          ? await resolveSyncConflictKeepMine(
              user.activeHouseholdId,
              conflictId,
              resolutionMutationId,
              selectedConflictDetail.currentServerVersion
            )
          : await resolveSyncConflictUseServer(
              user.activeHouseholdId,
              conflictId,
              resolutionMutationId
            );

      setState({ status: 'ok', data: nextList });
      await rememberConfirmedList(nextList);
      if (localMutationId) {
        await clearQueuedMutation(localMutationId);
      }
      await clearConflict(conflictId);
      await refreshOfflineRuntime(user.activeHouseholdId);
      setSelectedConflictId(null);
      setSelectedConflictDetail(null);
      setConflictDetailMessage(null);
      setSyncStatus(action === 'keep_mine' ? 'resolved_keep_mine' : 'resolved_use_server');
      setMessage(
        action === 'keep_mine'
          ? 'Kept your saved trip change and refreshed this phone from the latest server state.'
          : 'Accepted the server copy and refreshed this phone to match it.'
      );
    } catch (error) {
      setSyncStatus('error');
      const errorMessage =
        error instanceof Error ? error.message : 'Could not resolve this saved sync issue.';
      setConflictDetailMessage(errorMessage);
      setMessage(errorMessage);
      await refreshOfflineRuntime(user.activeHouseholdId);
    } finally {
      setResolvingConflict(null);
    }
  }

  async function handleDerive() {
    if (!user) {
      return;
    }

    await runListMutation(
      () => deriveGroceryList(user.activeHouseholdId, periodStart, randomUUID()),
      'Derived a grocery draft from the confirmed plan and current inventory.'
    );
  }

  async function handleRefreshDraft() {
    if (!user || state.status !== 'ok' || !state.data) {
      return;
    }

    const groceryListId = state.data.groceryListId;
    const priorStatus = state.data.status;
    const priorSummary = getReviewSummary(state.data);

    await runListMutation(
      () =>
        rederiveGroceryList(user.activeHouseholdId, groceryListId, periodStart, randomUUID()),
      priorStatus === 'confirmed' ||
        priorStatus === 'trip_in_progress' ||
        priorStatus === 'trip_complete_pending_reconciliation'
        ? 'Created a refreshed grocery draft while preserving the confirmed list version.'
        : priorSummary.overrideCount > 0
          ? 'Refreshed the grocery draft and preserved existing quantity overrides for review.'
          : 'Refreshed the grocery draft from the latest confirmed plan and inventory.'
    );
  }

  async function handleConfirm() {
    if (!user || state.status !== 'ok' || !state.data) {
      return;
    }

    const groceryListId = state.data.groceryListId;
    await runListMutation(
      () => confirmGroceryList(user.activeHouseholdId, groceryListId, randomUUID()),
      'Confirmed this grocery list for shopping. This version is now locked from edits.',
      { onSuccess: () => setConfirmOpen(false) }
    );
  }

  async function handleAddAdHoc(name: string, quantity: number, unit: string, note?: string) {
    if (!user || state.status !== 'ok' || !state.data) {
      return;
    }

    if (canEditList(state.data.status)) {
      const groceryListId = state.data.groceryListId;
      await runListMutation(
        () =>
          addAdHocLine(
            user.activeHouseholdId,
            groceryListId,
            name,
            quantity,
            unit,
            randomUUID(),
            note
          ),
        'Added the ad hoc grocery item to the current draft.'
      );
      return;
    }

    if (!isConfirmedListSnapshotStatus(state.data.status)) {
      return;
    }

    const provisionalLineId = `local-${randomUUID()}`;
    const nextList = applyOptimisticTripAdHocLine(state.data, {
      provisionalLineId,
      name,
      quantity,
      unit,
      note,
    });

    await queueTripMutation(
      nextList,
      {
        aggregateType: 'grocery_list',
        aggregateId: state.data.groceryListId,
        provisionalAggregateId: provisionalLineId,
        mutationType: 'add_ad_hoc',
        payload: {
          grocery_list_id: state.data.groceryListId,
          ingredient_name: name,
          shopping_quantity: quantity,
          unit,
          ad_hoc_note: note?.trim() ? note.trim() : null,
        },
      },
      `Saved ${name} on this phone. It will sync when the connection is ready.`,
      `Added ${name} to the trip list.`
    );
  }

  async function handleAdjustLine(line: GroceryLine, quantity: number, note?: string) {
    if (!user || state.status !== 'ok' || !state.data) {
      return;
    }

    if (canEditList(state.data.status)) {
      const groceryListId = state.data.groceryListId;
      await runListMutation(
        () =>
          adjustGroceryLine(
            user.activeHouseholdId,
            groceryListId,
            line.groceryLineId,
            quantity,
            randomUUID(),
            note
          ),
        `Updated ${line.name} to ${quantity} ${line.unit}.`
      );
      return;
    }

    if (!isConfirmedListSnapshotStatus(state.data.status)) {
      return;
    }

    const nextList = applyOptimisticTripQuantity(state.data, line.groceryLineId, quantity, note);
    await queueTripMutation(
      nextList,
      {
        aggregateType: 'grocery_line',
        aggregateId: line.groceryLineId,
        provisionalAggregateId: null,
        mutationType: 'adjust_quantity',
        payload: {
          grocery_list_id: state.data.groceryListId,
          grocery_line_id: line.groceryLineId,
          quantity_to_buy: quantity,
          user_adjustment_note: note?.trim() ? note.trim() : null,
        },
      },
      `Saved ${line.name} at ${quantity} ${line.unit} on this phone.`,
      `Updated ${line.name} to ${quantity} ${line.unit}.`
    );
  }

  async function handleRemoveLine(line: GroceryLine) {
    if (!user || state.status !== 'ok' || !state.data || !canEditList(state.data.status)) {
      return;
    }

    const groceryListId = state.data.groceryListId;
    await runListMutation(
      () =>
        removeGroceryLine(
          user.activeHouseholdId,
          groceryListId,
          line.groceryLineId,
          randomUUID()
        ),
      `Removed ${line.name} from the current draft.`
    );
  }

  async function handleTripComplete(line: GroceryLine) {
    if (state.status !== 'ok' || !state.data || !isConfirmedListSnapshotStatus(state.data.status)) {
      return;
    }

    const nextList = applyOptimisticTripCompletion(state.data, line.groceryLineId);
    await queueTripMutation(
      nextList,
      {
        aggregateType: 'grocery_line',
        aggregateId: line.groceryLineId,
        provisionalAggregateId: null,
        mutationType: 'remove_line',
        payload: {
          grocery_list_id: state.data.groceryListId,
          grocery_line_id: line.groceryLineId,
        },
      },
      `Marked ${line.name} done on this phone. It will sync when the connection is ready.`,
      `Marked ${line.name} done.`
    );
  }

  const list = state.status === 'ok' ? state.data : null;
  const tripMode = Boolean(list && isConfirmedListSnapshotStatus(list.status));
  const statusMessage = list ? getStatusMessage(list) : null;
  const derivedAt = formatTimestamp(list?.lastDerivedAt ?? null);
  const confirmedAt = formatTimestamp(list?.confirmedAt ?? null);
  const editable = list ? canEditList(list.status) : false;
  const refreshable = list ? canRefreshList(list.status) : false;
  const activeLines = useMemo(() => (list ? getActiveLines(list) : []), [list]);
  const removedLines = useMemo(() => (list ? getRemovedLines(list) : []), [list]);
  const reviewSummary = useMemo(() => (list ? getReviewSummary(list) : null), [list]);
  const tripSummary = useMemo(() => (list ? getTripProgressSummary(list) : null), [list]);
  const reviewHeadline = list ? getReviewHeadline(list) : null;
  const runtimeSyncStatus = getOfflineSyncStatus(offlineQueueState, online);
  const effectiveSyncStatus =
    syncStatus === 'idle' || syncStatus === 'offline' ? runtimeSyncStatus : syncStatus;
  const actionBusy = syncStatus === 'syncing' || syncStatus === 'resolving';
  const offlineRuntimeMessage = useMemo(() => {
    if (!list || !tripMode || !offlineReady) {
      return null;
    }

    if (!online) {
      return 'Offline — this phone is using the saved confirmed-list snapshot. Trip changes will queue until reconnect.';
    }
    if (offlineQueueState.reviewRequiredCount > 0 || offlineQueueState.conflictCount > 0) {
      return `${offlineQueueState.reviewRequiredCount || offlineQueueState.conflictCount} saved sync issue(s) still need review before queued trip changes can finish syncing.`;
    }
    if (offlineQueueState.retryingCount > 0) {
      return `${offlineQueueState.retryingCount} queued trip change(s) are waiting to retry once the connection stabilizes.`;
    }
    if (offlineQueueState.queuedCount > 0) {
      return `${offlineQueueState.queuedCount} trip change(s) are queued locally and ready for upload.`;
    }
    if (offlineQueueState.latestSnapshotSavedAt) {
      return `Confirmed trip snapshot saved locally at ${formatTimestamp(
        offlineQueueState.latestSnapshotSavedAt
      )}.`;
    }

    return null;
  }, [list, offlineQueueState, offlineReady, online, tripMode]);

  const lineSyncState = useMemo(() => {
    const map = new Map<string, { status: SyncStatus; copy: string | null }>();

    for (const mutation of [...queuedMutations].reverse()) {
      const key =
        mutation.aggregateType === 'grocery_line'
          ? mutation.aggregateId
          : mutation.provisionalAggregateId;
      if (!key || map.has(key)) {
        continue;
      }
      map.set(key, {
        status: mutation.localQueueStatus,
        copy: getMutationSurfaceCopy(mutation.localQueueStatus),
      });
    }

    for (const conflict of localConflicts) {
      const key =
        conflict.localMutation?.aggregateId ??
        conflict.localMutation?.provisionalAggregateId ??
        conflict.conflict.aggregate.aggregateId;
      if (!key || map.has(key)) {
        continue;
      }
      map.set(key, {
        status: 'review_required',
        copy: conflict.conflict.summary,
      });
    }

    return map;
  }, [localConflicts, queuedMutations]);

  if (session.status === 'loading') {
    return <LoadingState label="Loading grocery list…" />;
  }

  if (session.status === 'error') {
    return <ErrorState message={session.message} onRetry={refresh} />;
  }

  if (!user) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>Grocery List</h1>
        </div>
        <EmptyState
          icon="🔐"
          title="Sign in to review the grocery list"
          description="The grocery view depends on the API-owned session bootstrap and confirmed plan contracts."
        />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>{tripMode ? 'Trip mode' : 'Grocery List'}</h1>
          <p className={styles.subtitle}>
            {tripMode
              ? 'Phone-first shopping over the confirmed-list snapshot, with honest local sync status.'
              : 'Review the draft, understand the traceability, and confirm a stable shopping version.'}
          </p>
        </div>
        <SyncStatusBadge status={effectiveSyncStatus} />
      </div>

      {message && <p className={styles.message}>{message}</p>}
      {offlineRuntimeMessage && <p className={styles.message}>{offlineRuntimeMessage}</p>}

      {state.status === 'loading' && <LoadingState label="Loading grocery list…" />}
      {state.status === 'error' && <ErrorState message={state.message} onRetry={load} />}

      {state.status === 'ok' && !list && (
        <>
          <EmptyState
            icon="🛒"
            title="No grocery draft yet"
            description="Confirm a weekly plan, then derive a grocery draft from the approved backend contract."
          />
          <div className={styles.actionRow}>
            <button
              className={styles.primaryAction}
              onClick={() => void handleDerive()}
              disabled={actionBusy}
              type="button"
            >
              Derive grocery draft
            </button>
          </div>
        </>
      )}

      {state.status === 'ok' && list && reviewSummary && (
        <>
          <section className={`${styles.hero} ${tripMode ? styles.tripHero : ''}`}>
            <div className={styles.statusRow}>
              <span className={styles.statusBadge}>{STATUS_LABELS[list.status]}</span>
              <span className={styles.meta}>Version {list.currentVersionNumber}</span>
              {list.derivedFromPlanId && <span className={styles.meta}>Plan {list.derivedFromPlanId}</span>}
              {list.confirmedPlanVersion !== null && (
                <span className={styles.meta}>Plan version {list.confirmedPlanVersion}</span>
              )}
              {list.isStale && <span className={styles.staleBadge}>Needs review</span>}
            </div>

            {tripMode ? (
              <h2 className={styles.reviewHeadline}>
                {list.status === 'confirmed'
                  ? 'Confirmed snapshot is ready for shopping on this phone.'
                  : 'Trip mode is active. Keep moving even if the connection drops.'}
              </h2>
            ) : (
              reviewHeadline && <h2 className={styles.reviewHeadline}>{reviewHeadline}</h2>
            )}
            {statusMessage && <p className={styles.helperText}>{statusMessage}</p>}

            <div className={styles.metaGrid}>
              <span className={styles.meta}>Week of {list.planPeriodStart}</span>
              {list.planPeriodEnd && <span className={styles.meta}>Ends {list.planPeriodEnd}</span>}
              {derivedAt && <span className={styles.meta}>Derived {derivedAt}</span>}
              {confirmedAt && <span className={styles.meta}>Confirmed {confirmedAt}</span>}
            </div>

            <div className={styles.summaryGrid}>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>{tripMode ? 'Remaining lines' : 'Shopping lines'}</span>
                <strong className={styles.summaryValue}>
                  {tripMode ? tripSummary?.remainingLineCount ?? 0 : reviewSummary.activeLineCount}
                </strong>
                <p className={styles.summaryCopy}>
                  {tripMode
                    ? 'Still active on this trip snapshot.'
                    : 'Current active lines for this review.'}
                </p>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>{tripMode ? 'Done on this phone' : 'Derived vs. ad hoc'}</span>
                <strong className={styles.summaryValue}>
                  {tripMode
                    ? tripSummary?.completedLineCount ?? 0
                    : `${reviewSummary.derivedLineCount} / ${reviewSummary.adHocLineCount}`}
                </strong>
                <p className={styles.summaryCopy}>
                  {tripMode
                    ? 'Completed lines stay visible in the trip history section.'
                    : 'Derived lines first, ad hoc additions preserved.'}
                </p>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>{tripMode ? 'Queued locally' : 'Overrides'}</span>
                <strong className={styles.summaryValue}>
                  {tripMode ? offlineQueueState.queuedCount + offlineQueueState.retryingCount : reviewSummary.overrideCount}
                </strong>
                <p className={styles.summaryCopy}>
                  {tripMode
                    ? 'Saved on this device and waiting to sync or retry.'
                    : 'Manual quantity reviews still active on this draft.'}
                </p>
              </article>
              <article className={styles.summaryCard}>
                <span className={styles.summaryLabel}>{tripMode ? 'Needs review' : 'Warnings'}</span>
                <strong className={styles.summaryValue}>
                  {tripMode
                    ? offlineQueueState.reviewRequiredCount || offlineQueueState.conflictCount
                    : reviewSummary.warningCount}
                </strong>
                <p className={styles.summaryCopy}>
                  {tripMode
                    ? 'Conflict-safe sync stops here instead of guessing.'
                    : 'Incomplete meal slots surfaced honestly, without guessing.'}
                </p>
              </article>
            </div>
          </section>

          {list.isStale && !tripMode && (
            <section className={`${styles.noticePanel} ${styles.stalePanel}`} aria-label="Stale grocery draft warning">
              <h2 className={styles.sectionTitle}>Stale draft</h2>
              <p className={styles.noticeText}>
                Plan or inventory inputs changed after this draft was derived. Refresh to review the latest needs before you confirm.
              </p>
            </section>
          )}

          {tripMode && (
            <section className={styles.tripPanel} aria-label="Trip mode summary">
              <div>
                <h2 className={styles.sectionTitle}>Trip sync summary</h2>
                <p className={styles.helperText}>
                  Large touch targets keep this list usable one-handed. Quantity changes queue as intent-based edits over the confirmed snapshot instead of silently overwriting shared state.
                </p>
              </div>
              {online && offlineQueueState.queuedCount + offlineQueueState.retryingCount > 0 && (
                <button
                  className={styles.secondaryAction}
                  type="button"
                  onClick={() => void syncQueuedTripMutations(user.activeHouseholdId, 'Synced saved trip changes.')}
                  disabled={actionBusy}
                >
                  Sync saved changes
                </button>
              )}
            </section>
          )}

          {tripMode &&
            (offlineQueueState.retryingCount > 0 || offlineQueueState.failedRetryableCount > 0) && (
              <section className={styles.noticePanel} aria-label="Retrying trip sync changes">
                <h2 className={styles.sectionTitle}>Retrying saved changes</h2>
                <p className={styles.helperText}>
                  These are connection or service retries, not review-required conflicts. The app
                  will keep retrying automatically while the connection stabilizes.
                </p>
              </section>
            )}

          {list.incompleteSlotWarnings.length > 0 && !tripMode && (
            <section className={styles.warningPanel} aria-label="Grocery derivation warnings">
              <h2 className={styles.sectionTitle}>Incomplete meal warnings</h2>
              <p className={styles.helperText}>
                {list.incompleteSlotWarnings.length} meal
                {list.incompleteSlotWarnings.length === 1 ? '' : 's'} could not fully contribute grocery needs. Add ad hoc lines for anything you know is still missing.
              </p>
              <ul className={styles.warningList} role="list">
                {list.incompleteSlotWarnings.map((warning) => (
                  <li key={`${warning.mealSlotId}-${warning.reason}`} className={styles.warningItem}>
                    <strong>{warning.mealName ?? `Meal slot ${warning.mealSlotId}`}</strong>
                    <span>{warning.message ?? 'Missing ingredient data prevented a full derivation.'}</span>
                    <span className={styles.warningReason}>Reason: {warning.reason.replaceAll('_', ' ')}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {tripMode && localConflicts.length > 0 && (
            <section className={styles.conflictPanel} aria-label="Trip sync issues">
              <div className={styles.conflictPanelHeader}>
                <div>
                  <h2 className={styles.sectionTitle}>Saved sync issues</h2>
                  <p className={styles.helperText}>
                    Review-required conflicts pause automatic replay for that saved change. Retry
                    states above will recover on their own, but these items need an explicit choice.
                  </p>
                </div>
                <span className={styles.conflictCountBadge}>
                  {localConflicts.length} review item{localConflicts.length === 1 ? '' : 's'}
                </span>
              </div>
              <ul className={styles.conflictList} role="list">
                {localConflicts.map((conflict) => {
                  const opening = selectedConflictId === conflict.conflict.conflictId;
                  return (
                    <li key={conflict.conflict.conflictId} className={styles.conflictItem}>
                      <div className={styles.conflictItemHeader}>
                        <strong>{conflict.conflict.summary}</strong>
                        <span className={styles.conflictOutcomePill}>
                          {getConflictOutcomeLabel(conflict.conflict.outcome)}
                        </span>
                      </div>
                      <p className={styles.conflictItemCopy}>
                        {getConflictOutcomeDescription(conflict.conflict.outcome)}
                      </p>
                      <div className={styles.conflictMetaRow}>
                        <span>{conflict.conflict.mutationType.replaceAll('_', ' ')}</span>
                        <span>Base v{conflict.conflict.baseServerVersion ?? 'unknown'}</span>
                        <span>Server v{conflict.conflict.currentServerVersion}</span>
                      </div>
                      <button
                        className={styles.secondaryAction}
                        type="button"
                        disabled={actionBusy}
                        onClick={() => setSelectedConflictId(conflict.conflict.conflictId)}
                      >
                        {opening ? 'Reviewing details' : 'Review details'}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          <div className={styles.actionRow}>
            {refreshable && (
              <button
                className={styles.secondaryAction}
                onClick={() => void handleRefreshDraft()}
                disabled={actionBusy}
                type="button"
              >
                {getRefreshLabel(list.status)}
              </button>
            )}
            {editable && (
              <button
                className={styles.primaryAction}
                onClick={() => setConfirmOpen(true)}
                disabled={actionBusy}
                type="button"
              >
                Review and confirm
              </button>
            )}
          </div>

          {list.status === 'deriving' && <LoadingState label="Deriving grocery draft…" />}

          {activeLines.length > 0 ? (
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>
                {tripMode ? 'Trip shopping list' : 'Review shopping lines'}{' '}
                <span className={styles.count}>{activeLines.length}</span>
              </h2>
              {tripMode && (
                <p className={styles.helperText}>
                  Use the quick buttons for one-handed edits, or open details when you need the meal trace and inventory context.
                </p>
              )}
              <ul className={styles.list} role="list">
                {activeLines.map((line) => {
                  const lineStatus = lineSyncState.get(line.groceryLineId);
                  return (
                    <GroceryLineRow
                      key={line.groceryLineId}
                      line={line}
                      editable={editable || tripMode}
                      disabled={actionBusy}
                      mode={tripMode ? 'trip' : 'review'}
                      syncStatus={lineStatus?.status ?? null}
                      pendingCopy={lineStatus?.copy ?? null}
                      onAdjust={handleAdjustLine}
                      onQuickAdjust={tripMode ? (tripLine, quantity) => handleAdjustLine(tripLine, quantity) : undefined}
                      onRemove={handleRemoveLine}
                      onComplete={tripMode ? handleTripComplete : undefined}
                    />
                  );
                })}
              </ul>
            </section>
          ) : (
            <EmptyState
              icon="✅"
              title={tripMode ? 'Trip list is clear on this phone' : 'No active shopping lines in this version'}
              description={
                tripMode
                  ? 'Every active line has been marked done, or this confirmed snapshot was already covered by inventory.'
                  : 'The confirmed plan may already be covered by inventory, or every draft line has been removed after review.'
              }
            />
          )}

          {removedLines.length > 0 && (
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>
                {tripMode ? 'Done on this phone' : 'Removed from this draft'}{' '}
                <span className={styles.count}>{removedLines.length}</span>
              </h2>
              <p className={styles.helperText}>
                {tripMode
                  ? 'Completed lines stay visible so the shopper can double-check what already happened, even before sync finishes.'
                  : 'These lines were intentionally removed from the draft. A later refresh can restore derived lines if they are still needed.'}
              </p>
              <ul className={styles.list} role="list">
                {removedLines.map((line) => (
                  <GroceryLineRow
                    key={line.groceryLineId}
                    line={line}
                    mode={tripMode ? 'trip' : 'review'}
                    syncStatus={lineSyncState.get(line.groceryLineId)?.status ?? null}
                    pendingCopy={lineSyncState.get(line.groceryLineId)?.copy ?? null}
                  />
                ))}
              </ul>
            </section>
          )}

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>{tripMode ? 'Quick add during the trip' : 'Add ad hoc items'}</h2>
            <p className={styles.helperText}>
              {tripMode
                ? 'Capture forgotten items with minimal typing. The new line stays local first, then syncs onto the confirmed trip snapshot.'
                : 'Capture household extras or ingredients from incomplete meals without losing them on refresh.'}
            </p>
            {(editable || tripMode) ? (
              <AdHocItemForm
                onAdd={handleAddAdHoc}
                disabled={actionBusy}
                mode={tripMode ? 'trip' : 'review'}
              />
            ) : (
              <p className={styles.helperText}>
                Ad hoc items can only be added while the grocery list is still a draft or an active confirmed trip snapshot.
              </p>
            )}
          </section>
        </>
      )}

      {confirmOpen && list && reviewSummary && (
        <div className={styles.modalOverlay} role="presentation" onClick={() => setConfirmOpen(false)}>
          <div
            className={styles.modal}
            role="dialog"
            aria-modal="true"
            aria-labelledby="grocery-confirm-title"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 id="grocery-confirm-title" className={styles.modalTitle}>
              Confirm grocery list
            </h2>
            <p className={styles.modalCopy}>{getConfirmationSummary(list)}</p>
            <ul className={styles.modalChecklist}>
              <li>This confirmed version becomes the stable shopping list for the trip.</li>
              {reviewSummary.warningCount > 0 && (
                <li>{reviewSummary.warningCount} incomplete meal warning(s) are still visible on this draft.</li>
              )}
              {reviewSummary.overrideCount > 0 && (
                <li>{reviewSummary.overrideCount} line(s) have quantity overrides that will carry into the confirmed list.</li>
              )}
              {list.isStale && <li>This draft is stale. Refreshing first is recommended, but you can still confirm the current review.</li>}
            </ul>
            <div className={styles.modalActions}>
              <button
                className={styles.secondaryAction}
                type="button"
                onClick={() => setConfirmOpen(false)}
                disabled={actionBusy}
              >
                Cancel
              </button>
              <button
                className={styles.primaryAction}
                type="button"
                onClick={() => void handleConfirm()}
                disabled={actionBusy}
              >
                Confirm for shopping
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedConflictDetail && (
        <SyncConflictReviewModal
          conflict={selectedConflictDetail}
          loading={conflictDetailLoading}
          message={conflictDetailMessage}
          resolvingAction={
            resolvingConflict?.conflictId === selectedConflictDetail.conflictId
              ? resolvingConflict.action
              : null
          }
          onClose={() => {
            if (!resolvingConflict) {
              setSelectedConflictId(null);
            }
          }}
          onResolve={handleResolveConflict}
        />
      )}
    </div>
  );
}
