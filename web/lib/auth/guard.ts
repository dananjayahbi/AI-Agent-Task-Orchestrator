/**
 * Pure route-access decision for the proxy gate (MT-4.1-02; Section 13.1
 * route map). Kept free of Next.js imports so the full redirect matrix is
 * unit-testable (every Section 13.1 route except Login must bounce
 * unauthenticated visitors to the login page with a return path).
 */
export type RouteAccess = { kind: 'allow' } | { kind: 'redirect'; to: string };

/** Login route (the only public page). */
export const LOGIN_PATH = '/login';
/** Board/Overview landing after a successful sign-in (Section 13.1). */
export const HOME_PATH = '/';

/**
 * Classify an API request: the backend is authoritative for API paths — a
 * missing session there must surface as the `AUTH_REQUIRED` envelope from the
 * API itself, never as an HTML redirect (MT-4.1-02 risk note).
 */
export function isApiPath(pathname: string): boolean {
  return pathname === '/api' || pathname.startsWith('/api/');
}

/**
 * Decide what the proxy does for *pathname* (plus optional `search` query
 * string) given the session-cookie presence:
 *
 * * API paths always pass through (server-side authority);
 * * `/login` with a session bounces to the Board;
 * * every other path without a session redirects to `/login` carrying the
 *   full return path (path + query) so login can resume there.
 */
export function evaluateRouteAccess(
  pathname: string,
  hasSession: boolean,
  search = '',
): RouteAccess {
  if (isApiPath(pathname)) {
    return { kind: 'allow' };
  }
  if (pathname === LOGIN_PATH) {
    return hasSession ? { kind: 'redirect', to: HOME_PATH } : { kind: 'allow' };
  }
  if (hasSession) {
    return { kind: 'allow' };
  }
  return { kind: 'redirect', to: loginRedirectUrl(`${pathname}${search}`) };
}

/** Build the login URL for *returnTo*, including the `next` query parameter. */
export function loginRedirectUrl(returnTo: string): string {
  return `${LOGIN_PATH}?next=${encodeURIComponent(returnTo)}`;
}
