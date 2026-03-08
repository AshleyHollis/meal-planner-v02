'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../../_lib/api';
import {
  getInventory,
  getInventoryHistory,
  getInventoryItemDetail,
  mutateInventory,
} from '../../_lib/inventory-api';
import {
  describeItemFreshness,
  formatMutationType,
  formatQuantityWithUnit,
  formatStorageLocation,
} from '../../_lib/inventory-trust';
import type {
  InventoryConflictDetail,
  InventoryHistoryPage,
  InventoryItem,
  InventoryItemDetail,
  InventoryMutationRequest,
  MutationReceipt,
  StorageLocation,
} from '../../_lib/types';
import { useSession } from '../../_hooks/useSession';
import { EmptyState } from '../../_components/EmptyState';
import { ErrorState } from '../../_components/ErrorState';
import { LoadingState } from '../../_components/LoadingState';
import { SyncStatusBadge } from '../../_components/SyncStatusBadge';
import { randomUUID } from '../../_lib/uuid';
import { AddItemForm, type AddItemValues } from './AddItemForm';
import { InventoryItemRow } from './InventoryItemRow';
import { InventoryTrustPanel } from './InventoryTrustPanel';
import { LocationTabs } from './LocationTabs';
import styles from './InventoryView.module.css';

type AsyncState<T> =
  | { status: 'loading' }
  | { status: 'ok'; data: T }
  | { status: 'error'; message: string };

type PanelState<T> = { status: 'idle' } | AsyncState<T>;

type MessageTone = 'info' | 'success' | 'warning' | 'error';

type BannerMessage = {
  tone: MessageTone;
  text: string;
};

const HISTORY_PAGE_SIZE = 6;

function conflictMessage(error: ApiError): string {
  const detail = error.detail as InventoryConflictDetail | undefined;
  if (detail?.code === 'stale_inventory_version') {
    const currentVersion =
      detail.currentVersion ??
      ((detail as InventoryConflictDetail & { current_version?: number }).current_version ??
        'unknown');
    return `${detail.message} Server version is now ${currentVersion}. Reloaded the latest item state so you can retry safely.`;
  }
  return error.message;
}

function inventoryErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError && error.status === 401) {
    return 'Your session is no longer active. Retry session bootstrap and reload inventory.';
  }

  if (error instanceof ApiError && error.status === 403) {
    return 'This session is not allowed to access the active household inventory.';
  }

  return error instanceof Error ? error.message : fallback;
}

function mergeHistoryPage(
  current: InventoryHistoryPage,
  next: InventoryHistoryPage
): InventoryHistoryPage {
  return {
    ...next,
    entries: [...current.entries, ...next.entries],
  };
}

export function InventoryView() {
  const { user, session, refresh } = useSession();
  const [location, setLocation] = useState<StorageLocation>('fridge');
  const [state, setState] = useState<AsyncState<InventoryItem[]>>({
    status: 'loading',
  });
  const [detailState, setDetailState] = useState<PanelState<InventoryItemDetail>>({
    status: 'idle',
  });
  const [historyState, setHistoryState] = useState<PanelState<InventoryHistoryPage>>({
    status: 'idle',
  });
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [loadingMoreHistory, setLoadingMoreHistory] = useState(false);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'conflict' | 'error'>('idle');
  const [message, setMessage] = useState<BannerMessage | null>(null);
  const selectedItemIdRef = useRef<string | null>(null);

  const clearSelection = useCallback(() => {
    selectedItemIdRef.current = null;
    setSelectedItemId(null);
    setDetailState({ status: 'idle' });
    setHistoryState({ status: 'idle' });
    setLoadingMoreHistory(false);
  }, []);

  const load = useCallback(async () => {
    if (session.status !== 'authenticated' || !user) {
      setState({ status: 'ok', data: [] });
      return;
    }

    setState({ status: 'loading' });
    try {
      const items = await getInventory(location);
      setState({ status: 'ok', data: items });
    } catch (error) {
      setState({
        status: 'error',
        message: inventoryErrorMessage(error, 'Could not load inventory.'),
      });
    }
  }, [location, session.status, user]);

  const loadTrustPanel = useCallback(async (itemId: string) => {
    selectedItemIdRef.current = itemId;
    setSelectedItemId(itemId);
    setDetailState({ status: 'loading' });
    setHistoryState({ status: 'loading' });
    setLoadingMoreHistory(false);

    const [detailResult, historyResult] = await Promise.allSettled([
      getInventoryItemDetail(itemId),
      getInventoryHistory(itemId, { limit: HISTORY_PAGE_SIZE, offset: 0 }),
    ]);

    if (selectedItemIdRef.current !== itemId) {
      return null;
    }

    if (detailResult.status === 'fulfilled') {
      setDetailState({ status: 'ok', data: detailResult.value });
    } else {
      setDetailState({
        status: 'error',
        message: inventoryErrorMessage(detailResult.reason, 'Could not load item details.'),
      });
    }

    if (historyResult.status === 'fulfilled') {
      setHistoryState({ status: 'ok', data: historyResult.value });
    } else {
      setHistoryState({
        status: 'error',
        message: inventoryErrorMessage(historyResult.reason, 'Could not load item history.'),
      });
    }

    return detailResult.status === 'fulfilled' ? detailResult.value : null;
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    clearSelection();
  }, [clearSelection, location]);

  async function refreshAfterMutation(itemId: string) {
    await load();
    return loadTrustPanel(itemId);
  }

  async function runMutation(
    item: InventoryItemDetail,
    mutation: InventoryMutationRequest,
    onSuccess: (receipt: MutationReceipt, refreshedItem: InventoryItemDetail | null) => BannerMessage
  ) {
    if (!user) return;

    setSyncStatus('syncing');
    setMessage(null);

    try {
      const receipt = await mutateInventory(user.activeHouseholdId, mutation);
      const refreshedItem = await refreshAfterMutation(item.inventoryItemId);
      setSyncStatus('idle');

      if (receipt.isDuplicate) {
        setMessage({
          tone: 'info',
          text:
            receipt.message ??
            'That retry was already accepted earlier. No duplicate history entry was created.',
        });
        return;
      }

      setMessage(onSuccess(receipt, refreshedItem));
    } catch (error) {
      await refreshAfterMutation(item.inventoryItemId);
      if (error instanceof ApiError && error.status === 409) {
        setSyncStatus('conflict');
        setMessage({ tone: 'warning', text: conflictMessage(error) });
        return;
      }
      setSyncStatus('error');
      setMessage({
        tone: 'error',
        text: inventoryErrorMessage(error, 'Could not save inventory change.'),
      });
    }
  }

  async function handleAdd(values: AddItemValues) {
    if (!user) return;

    setSyncStatus('syncing');
    setMessage(null);

    try {
      const receipt = await mutateInventory(user.activeHouseholdId, {
        clientMutationId: randomUUID(),
        mutationType: 'create_item',
        payload: {
          name: values.name,
          quantityOnHand: values.quantity,
          primaryUnit: values.unit,
          storageLocation: values.location,
          freshnessBasis: values.freshnessBasis,
          expiryDate: values.expiryDate || null,
          estimatedExpiryDate: values.estimatedExpiryDate || null,
          freshnessNote: values.freshnessNote || null,
        },
      });
      await load();
      setSyncStatus('idle');
      setMessage({
        tone: receipt.isDuplicate ? 'info' : 'success',
        text: receipt.isDuplicate
          ? 'That create retry was already accepted earlier.'
          : `Added ${values.name} with ${describeItemFreshness({
              freshnessBasis: values.freshnessBasis,
              expiryDate: values.expiryDate || null,
              estimatedExpiryDate: values.estimatedExpiryDate || null,
              freshnessNote: values.freshnessNote || null,
            } as InventoryItem)}.`,
      });
    } catch (error) {
      setSyncStatus('error');
      setMessage({
        tone: 'error',
        text: inventoryErrorMessage(error, 'Could not save inventory item.'),
      });
    }
  }

  async function handleArchive(item: InventoryItem) {
    if (!user) return;

    setSyncStatus('syncing');
    setMessage(null);

    try {
      const receipt = await mutateInventory(user.activeHouseholdId, {
        clientMutationId: randomUUID(),
        mutationType: 'archive_item',
        inventoryItemId: item.inventoryItemId,
        lastKnownVersion: item.serverVersion,
        payload: {},
      });
      await load();
      clearSelection();
      setSyncStatus('idle');
      setMessage({
        tone: receipt.isDuplicate ? 'info' : 'success',
        text: receipt.isDuplicate
          ? 'That archive retry was already accepted earlier.'
          : `Archived ${item.name}. Its history remains available through committed events.`,
      });
    } catch (error) {
      await load();
      if (error instanceof ApiError && error.status === 409) {
        setSyncStatus('conflict');
        setMessage({ tone: 'warning', text: conflictMessage(error) });
        return;
      }
      setSyncStatus('error');
      setMessage({
        tone: 'error',
        text: inventoryErrorMessage(error, 'Could not archive inventory item.'),
      });
    }
  }

  async function handleSelect(item: InventoryItem) {
    if (selectedItemId === item.inventoryItemId) {
      clearSelection();
      return;
    }

    setMessage(null);
    await loadTrustPanel(item.inventoryItemId);
  }

  async function handleLoadMoreHistory() {
    if (!selectedItemId || historyState.status !== 'ok') {
      return;
    }

    setLoadingMoreHistory(true);
    try {
      const nextPage = await getInventoryHistory(selectedItemId, {
        limit: HISTORY_PAGE_SIZE,
        offset: historyState.data.entries.length,
      });
      setHistoryState({
        status: 'ok',
        data: mergeHistoryPage(historyState.data, nextPage),
      });
    } catch (error) {
      setMessage({
        tone: 'error',
        text: inventoryErrorMessage(error, 'Could not load older history yet.'),
      });
    } finally {
      setLoadingMoreHistory(false);
    }
  }

  if (session.status === 'loading' || session.status === 'retrying') {
    return (
      <LoadingState
        label={
          session.status === 'retrying'
            ? 'Retrying household session…'
            : 'Loading inventory…'
        }
      />
    );
  }

  if (session.status === 'error') {
    return <ErrorState message={session.message} onRetry={refresh} />;
  }

  if (session.status === 'unauthorized') {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>Inventory</h1>
        </div>
        <ErrorState message={session.message} onRetry={refresh} />
      </div>
    );
  }

  if (session.status === 'unauthenticated') {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>Inventory</h1>
        </div>
        <EmptyState
          icon="🔐"
          title="Sign in to view inventory"
          description={session.message}
          action={
            <button className={styles.retryButton} onClick={refresh} type="button">
              Retry session
            </button>
          }
        />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const selectedDetail = detailState.status === 'ok' ? detailState.data : null;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Inventory</h1>
          <p className={styles.subtitle}>
            Review quantity, freshness, moves, and correction chains without rewriting committed
            history.
          </p>
        </div>
        <SyncStatusBadge status={syncStatus} />
      </div>

      {message && (
        <p className={`${styles.message} ${styles[`message${message.tone[0]?.toUpperCase()}${message.tone.slice(1)}`]}`}>
          {message.text}
        </p>
      )}

      <LocationTabs active={location} onChange={setLocation} />

      {state.status === 'loading' && <LoadingState label="Loading inventory…" />}
      {state.status === 'error' && <ErrorState message={state.message} onRetry={load} />}
      {state.status === 'ok' && (
        <>
          {state.data.length === 0 ? (
            <EmptyState
              icon="🗄️"
              title="Nothing here yet"
              description="Add items with quantity, storage location, and freshness basis so later inventory mutations can carry trustworthy versioned state."
            />
          ) : (
            <ul className={styles.list} role="list">
              {state.data.map((item) => (
                <InventoryItemRow
                  key={item.inventoryItemId}
                  item={item}
                  isSelected={item.inventoryItemId === selectedItemId}
                  onReview={handleSelect}
                  onArchive={handleArchive}
                />
              ))}
            </ul>
          )}

          {selectedItemId && detailState.status === 'loading' && (
            <LoadingState label="Loading trust details…" />
          )}

          {selectedItemId && detailState.status === 'error' && (
            <ErrorState
              message={detailState.message}
              onRetry={() => void loadTrustPanel(selectedItemId)}
            />
          )}

          {selectedDetail && historyState.status !== 'idle' && (
            <InventoryTrustPanel
              item={selectedDetail}
              historyState={historyState}
              loadingMoreHistory={loadingMoreHistory}
              disabled={syncStatus === 'syncing'}
              onRetryHistory={() => void loadTrustPanel(selectedDetail.inventoryItemId)}
              onLoadMoreHistory={() => void handleLoadMoreHistory()}
              onQuantitySubmit={(values) =>
                runMutation(
                  selectedDetail,
                  {
                    clientMutationId: randomUUID(),
                    mutationType: values.mutationType,
                    inventoryItemId: selectedDetail.inventoryItemId,
                    lastKnownVersion: selectedDetail.serverVersion,
                    payload: {
                      quantity: values.quantity,
                      reasonCode: values.reasonCode,
                      note: values.note || null,
                    },
                  },
                  (_, refreshedItem) => ({
                    tone: 'success',
                    text:
                      refreshedItem
                        ? `${formatMutationType(values.mutationType)} saved. ${refreshedItem.name} is now ${formatQuantityWithUnit(
                            refreshedItem.quantityOnHand,
                            refreshedItem.primaryUnit
                          )}.`
                        : 'Saved quantity change.',
                  })
                )
              }
              onMetadataSubmit={(values) =>
                runMutation(
                  selectedDetail,
                  {
                    clientMutationId: randomUUID(),
                    mutationType: 'set_metadata',
                    inventoryItemId: selectedDetail.inventoryItemId,
                    lastKnownVersion: selectedDetail.serverVersion,
                    payload: {
                      name: values.name,
                      freshnessBasis: values.freshnessBasis,
                      expiryDate: values.expiryDate || null,
                      estimatedExpiryDate: values.estimatedExpiryDate || null,
                      freshnessNote: values.freshnessNote || null,
                      note: values.note || null,
                    },
                  },
                  (_, refreshedItem) => ({
                    tone: 'success',
                    text:
                      refreshedItem
                        ? `Saved metadata. ${describeItemFreshness(refreshedItem)} now applies to ${refreshedItem.name}.`
                        : 'Saved metadata.',
                  })
                )
              }
              onMoveSubmit={(values) =>
                runMutation(
                  selectedDetail,
                  {
                    clientMutationId: randomUUID(),
                    mutationType: 'move_location',
                    inventoryItemId: selectedDetail.inventoryItemId,
                    lastKnownVersion: selectedDetail.serverVersion,
                    payload: {
                      storageLocation: values.storageLocation,
                      note: values.note || null,
                    },
                  },
                  (_, refreshedItem) => ({
                    tone: 'success',
                    text:
                      refreshedItem
                        ? `${refreshedItem.name} moved to ${formatStorageLocation(
                            refreshedItem.storageLocation
                          )}. ${
                            refreshedItem.storageLocation !== location
                              ? `This ${formatStorageLocation(location).toLowerCase()} tab will no longer list it.`
                              : ''
                          }`
                        : 'Saved location move.',
                  })
                )
              }
              onCorrectionSubmit={(values) =>
                runMutation(
                  selectedDetail,
                  {
                    clientMutationId: randomUUID(),
                    mutationType: 'correction',
                    inventoryItemId: selectedDetail.inventoryItemId,
                    lastKnownVersion: selectedDetail.serverVersion,
                    payload: {
                      deltaQuantity: values.deltaQuantity,
                      correctsAdjustmentId: values.correctsAdjustmentId,
                      note: values.note,
                    },
                  },
                  (_, refreshedItem) => ({
                    tone: 'success',
                    text:
                      refreshedItem
                        ? `Recorded a compensating correction. ${refreshedItem.name} is now ${formatQuantityWithUnit(
                            refreshedItem.quantityOnHand,
                            refreshedItem.primaryUnit
                          )}, and the original event remains visible in history.`
                        : 'Recorded a compensating correction.',
                  })
                )
              }
            />
          )}

          <AddItemForm defaultLocation={location} onAdd={handleAdd} disabled={syncStatus === 'syncing'} />
        </>
      )}
    </div>
  );
}
