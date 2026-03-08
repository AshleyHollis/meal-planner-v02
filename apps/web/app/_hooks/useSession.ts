'use client';

import { useSessionContext } from '../_providers/SessionContext';

export function useSession() {
  return useSessionContext();
}
