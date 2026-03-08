'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import { fetchSession } from '../_lib/session';
import type { SessionState, SessionUser } from '../_lib/types';

type SessionContextValue = {
  session: SessionState;
  user: SessionUser | null;
  refresh: () => void;
};

const SessionContext = createContext<SessionContextValue>({
  session: { status: 'loading' },
  user: null,
  refresh: () => {},
});

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionState>({ status: 'loading' });

  const bootstrap = useCallback(async (mode: 'initial' | 'retry' = 'initial') => {
    setSession({ status: mode === 'retry' ? 'retrying' : 'loading' });
    try {
      const nextSession = await fetchSession();
      setSession(nextSession);
    } catch (error) {
      setSession({
        status: 'error',
        message:
          error instanceof Error ? error.message : 'Could not reach the server.',
      });
    }
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const user =
    session.status === 'authenticated' ? session.user : null;

  return (
    <SessionContext.Provider
      value={{ session, user, refresh: () => void bootstrap('retry') }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSessionContext() {
  return useContext(SessionContext);
}
