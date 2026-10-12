/**
 * Client-side session identity (MT-4.1-02).
 *
 * The credential lives exclusively in the backend's HTTP-only cookies
 * (Section 12.2) — this store keeps only the non-secret identity shown in the
 * chrome (id + username), never the bearer binding and never any cookie
 * value. Cleared on logout and on mid-session `AUTH_REQUIRED`.
 *
 * Reads are memoized on the raw stored value so `useSyncExternalStore`
 * snapshots stay referentially stable (React rejects uncached snapshots).
 */
const STORAGE_KEY = 'orchestrator.web.session.user';

export type SessionUser = {
  id: number;
  username: string;
};

let cachedRaw: string | null = null;
let cachedUser: SessionUser | null = null;
let cacheInitialized = false;

function storage(): Storage | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function parseUser(raw: string | null): SessionUser | null {
  if (raw === null) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<SessionUser>;
    if (typeof parsed.id === 'number' && typeof parsed.username === 'string') {
      return { id: parsed.id, username: parsed.username };
    }
  } catch {
    // Corrupt entry → treat as signed out.
  }
  return null;
}

export function saveSessionUser(user: SessionUser): void {
  const raw = JSON.stringify(user);
  storage()?.setItem(STORAGE_KEY, raw);
  cachedRaw = raw;
  cachedUser = user;
  cacheInitialized = true;
}

export function readSessionUser(): SessionUser | null {
  const raw = storage()?.getItem(STORAGE_KEY) ?? null;
  if (!cacheInitialized || raw !== cachedRaw) {
    cachedRaw = raw;
    cachedUser = parseUser(raw);
    cacheInitialized = true;
  }
  return cachedUser;
}

export function clearSessionUser(): void {
  storage()?.removeItem(STORAGE_KEY);
  cachedRaw = null;
  cachedUser = null;
  cacheInitialized = true;
}
