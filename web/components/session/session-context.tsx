'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useSyncExternalStore,
  type ReactNode,
} from 'react';

import { setUnauthorizedHandler } from '@/lib/api/client';
import { performSessionExpired, performSignOut } from '@/lib/session/flows';
import { readSessionUser, saveSessionUser, type SessionUser } from '@/lib/session/store';

type SessionContextValue = {
  /** Non-secret identity shown in the chrome; null until hydrated/signed in. */
  user: SessionUser | null;
  signIn: (user: SessionUser) => void;
  /** Idempotent sign-out — see performSignOut (MT-4.1-02). */
  signOut: () => Promise<void>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

/** Cross-tab storage changes re-derive the snapshot; same-tab mutations notify below. */
function subscribeToStore(onStoreChange: () => void): () => void {
  window.addEventListener('storage', onStoreChange);
  return () => window.removeEventListener('storage', onStoreChange);
}

function serverSnapshot(): SessionUser | null {
  return null;
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [, notify] = useReducer((count: number) => count + 1, 0);
  const user = useSyncExternalStore(subscribeToStore, readSessionUser, serverSnapshot);

  useEffect(() => {
    // Wire the silent mid-session expiry redirect (Section 13.2:
    // AUTH_REQUIRED → login, no banner, no dead-end page).
    setUnauthorizedHandler(() => {
      performSessionExpired(
        `${window.location.pathname}${window.location.search}`,
        window.location,
      );
      notify();
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const signIn = useCallback((nextUser: SessionUser) => {
    saveSessionUser(nextUser);
    notify();
  }, []);

  const signOut = useCallback(async () => {
    await performSignOut(window.location);
    notify();
  }, []);

  const value = useMemo(() => ({ user, signIn, signOut }), [user, signIn, signOut]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (context === null) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
}
