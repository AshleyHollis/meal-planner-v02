'use client';

import type { SyncStatus } from '../_lib/types';
import styles from './SyncStatusBadge.module.css';

const LABELS: Record<SyncStatus, string> = {
  idle: 'Saved',
  syncing: 'Syncing…',
  conflict: 'Conflict',
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
