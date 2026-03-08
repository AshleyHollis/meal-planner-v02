'use client';

import type { SyncStatus } from '../_lib/types';
import styles from './SyncStatusBadge.module.css';

const LABELS: Record<SyncStatus, string> = {
  idle: 'Saved',
  queued_offline: 'Queued offline',
  syncing: 'Syncing…',
  synced: 'Synced',
  retrying: 'Retrying…',
  failed_retryable: 'Retry failed',
  conflict: 'Conflict',
  review_required: 'Review required',
  resolving: 'Resolving…',
  resolved_keep_mine: 'Kept mine',
  resolved_use_server: 'Used server',
  error: 'Sync error',
  offline: 'Offline',
};

type Props = {
  status: SyncStatus;
};

export function SyncStatusBadge({ status }: Props) {
  if (status === 'idle') return null;

  return (
    <span
      className={`${styles.badge} ${styles[status]}`}
      role="status"
      aria-live="polite"
    >
      {LABELS[status]}
    </span>
  );
}
