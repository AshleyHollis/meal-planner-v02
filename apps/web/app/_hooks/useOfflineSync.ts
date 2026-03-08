'use client';

import { useOfflineSyncContext } from '../_providers/OfflineSyncContext';

export function useOfflineSync() {
  return useOfflineSyncContext();
}
