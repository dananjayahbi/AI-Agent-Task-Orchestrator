import { logoutRequest } from '@/lib/api/auth';
import { clearSessionUser } from '@/lib/session/store';

/** Minimal navigation seam so flows are unit-testable without a browser. */
export type Navigator = {
  assign: (url: string) => void;
};

export const LOGIN_URL = '/login';

/**
 * Logout flow (MT-4.1-02 acceptance): revoke the backend session, clear the
 * local identity, land on login — regardless of whether the revoke reported
 * the session already expired (idempotent sign-out).
 */
export async function performSignOut(navigator: Navigator): Promise<void> {
  try {
    await logoutRequest();
  } catch {
    // Already expired / revoked — local clearing proceeds either way.
  }
  clearSessionUser();
  navigator.assign(LOGIN_URL);
}

/**
 * Mid-session expiry (Section 13.2): a canonical `AUTH_REQUIRED` from any
 * API call silently clears local state and returns to login carrying the
 * current path as the return target.
 */
export function performSessionExpired(returnTo: string, navigator: Navigator): void {
  clearSessionUser();
  navigator.assign(`${LOGIN_URL}?next=${encodeURIComponent(returnTo)}`);
}
