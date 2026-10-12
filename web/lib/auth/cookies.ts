/**
 * Cookie and header names for the owner-session transport (Section 12.2;
 * MT-1.2-01's contract, consumed here): Django's HTTP-only `sessionid` cookie
 * carries the session; the non-HTTP-only `csrftoken` cookie is echoed back as
 * the `X-CSRFToken` header on session-authenticated mutations
 * (backend/apps/accounts/authentication.py).
 *
 * The web app stores no token itself — cookies are the only credential
 * (ADR-012 posture; FR-SEC-02).
 */
export const SESSION_COOKIE_NAME = 'sessionid';
export const CSRF_COOKIE_NAME = 'csrftoken';
export const CSRF_HEADER_NAME = 'X-CSRFToken';

/** Read a cookie value by name (browser only; null during SSR/tests). */
export function readCookie(name: string): string | null {
  if (typeof document === 'undefined') {
    return null;
  }
  const prefix = `${name}=`;
  for (const part of document.cookie.split('; ')) {
    if (part.startsWith(prefix)) {
      return decodeURIComponent(part.slice(prefix.length));
    }
  }
  return null;
}
