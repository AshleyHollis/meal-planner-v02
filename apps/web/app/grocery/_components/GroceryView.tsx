'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  addAdHocLine,
  checkGroceryLine,
  getGroceryList,
} from '../../_lib/grocery-api';
import type { GroceryList, SyncStatus } from '../../_lib/types';
import { useSession } from '../../_hooks/useSession';
import { LoadingState } from '../../_components/LoadingState';
import { ErrorState } from '../../_components/ErrorState';
import { EmptyState } from '../../_components/EmptyState';
import { SyncStatusBadge } from '../../_components/SyncStatusBadge';
import { randomUUID } from '../../_lib/uuid';
import { GroceryLineRow } from './GroceryLineRow';
import { AdHocItemForm } from './AdHocItemForm';
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

const STATUS_LABELS: Record<GroceryList['status'], string> = {
  deriving: 'Deriving',
  current: 'Draft list',
  shopping: 'Confirmed for trip',
  completed: 'Trip completed',
};

export function GroceryView() {
  const { user, session, refresh } = useSession();
  const [periodStart] = useState(() => isoMonday());
  const [state, setState] = useState<AsyncState<GroceryList | null>>({
    status: 'loading',
  });
  const [syncStatus, setSyncStatus] = useState<SyncStatus>('idle');
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) {
      setState({ status: 'ok', data: null });
      return;
    }

    setState({ status: 'loading' });
    try {
      const list = await getGroceryList(user.householdId, periodStart);
      setState({ status: 'ok', data: list });
    } catch {
      setState({ status: 'error', message: 'Could not load grocery list.' });
    }
  }, [user, periodStart]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleToggle(lineId: string, checked: boolean) {
    if (!user || state.status !== 'ok' || !state.data) return;

    const clientMutationId = randomUUID();
    const previousList = state.data;

    setSyncStatus('syncing');
    setMessage(null);
    setState((prev) => {
      if (prev.status !== 'ok' || !prev.data) return prev;
      return {
        status: 'ok',
        data: {
          ...prev.data,
          lines: prev.data.lines.map((line) =>
            line.groceryLineId === lineId ? { ...line, checked } : line
          ),
        },
      };
    });

    try {
      await checkGroceryLine(
        user.householdId,
        previousList.groceryListId,
        lineId,
        checked,
        clientMutationId
      );
      setSyncStatus('idle');
    } catch (error) {
      setState({ status: 'ok', data: previousList });
      setSyncStatus('error');
      setMessage(error instanceof Error ? error.message : 'Could not update the grocery line.');
    }
  }

  async function handleAddAdHoc(name: string, quantity: number, unit: string) {
    if (!user || state.status !== 'ok' || !state.data) return;

    setSyncStatus('syncing');
    setMessage(null);

    try {
      await addAdHocLine(
        user.householdId,
        state.data.groceryListId,
        name,
        quantity,
        unit,
        randomUUID()
      );
      await load();
      setSyncStatus('idle');
    } catch (error) {
      setSyncStatus('error');
      setMessage(error instanceof Error ? error.message : 'Could not add the grocery item.');
    }
  }

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

  const list = state.status === 'ok' ? state.data : null;
  const pending = list?.lines.filter((line) => !line.checked) ?? [];
  const done = list?.lines.filter((line) => line.checked) ?? [];

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>Grocery List</h1>
        <SyncStatusBadge status={syncStatus} />
      </div>

      {message && <p className={styles.message}>{message}</p>}

      {state.status === 'loading' && <LoadingState label="Loading grocery list…" />}
      {state.status === 'error' && <ErrorState message={state.message} onRetry={load} />}

      {state.status === 'ok' && !list && (
        <EmptyState
          icon="🛒"
          title="No grocery list yet"
          description="Confirm a weekly plan to derive a grocery draft. Draft and confirmed list lifecycles will appear here once the grocery contract is available."
        />
      )}

      {state.status === 'ok' && list && (
        <>
          <div className={styles.statusRow}>
            <span className={styles.statusBadge}>{STATUS_LABELS[list.status]}</span>
            <span className={styles.meta}>Version {list.currentVersionNumber}</span>
            {list.reviewState === 'draft' && (
              <span className={styles.meta}>Review before trip</span>
            )}
            {list.derivedFromPlanId && (
              <span className={styles.meta}>Plan {list.derivedFromPlanId}</span>
            )}
            {list.isStale && <span className={styles.staleBadge}>List may be stale</span>}
          </div>

          {list.status === 'deriving' && (
            <p className={styles.helperText}>
              Grocery derivation is still running. Derived lines and ad hoc items will settle into
              the next list version when the backend contract finishes processing.
            </p>
          )}

          {pending.length > 0 && (
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>
                To buy <span className={styles.count}>{pending.length}</span>
              </h2>
              <ul className={styles.list} role="list">
                {pending.map((line) => (
                  <GroceryLineRow
                    key={line.groceryLineId}
                    line={line}
                    onToggle={handleToggle}
                  />
                ))}
              </ul>
            </section>
          )}

          {done.length > 0 && (
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>
                Done <span className={styles.count}>{done.length}</span>
              </h2>
              <ul className={styles.list} role="list">
                {done.map((line) => (
                  <GroceryLineRow
                    key={line.groceryLineId}
                    line={line}
                    onToggle={handleToggle}
                  />
                ))}
              </ul>
            </section>
          )}

          {pending.length === 0 && done.length === 0 && (
            <EmptyState
              icon="✅"
              title="List is empty"
              description="All done, or no ingredients from the confirmed plan produced grocery lines yet."
            />
          )}

          <AdHocItemForm onAdd={handleAddAdHoc} disabled={syncStatus === 'syncing'} />
        </>
      )}
    </div>
  );
}
