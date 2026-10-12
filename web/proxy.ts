import { NextResponse, type NextRequest } from 'next/server';

import { SESSION_COOKIE_NAME } from '@/lib/auth/cookies';
import { evaluateRouteAccess } from '@/lib/auth/guard';

/**
 * Session gate for the Section 13.1 routes (MT-4.1-02; Next.js proxy — the
 * renamed middleware convention in Next 16). Presence of the HTTP-only
 * `sessionid` cookie is a UX gate only: the backend stays authoritative
 * (every API call verifies the live session row and answers `AUTH_REQUIRED`,
 * which the client turns into a silent login redirect — Section 13.2).
 */
export default function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const decision = evaluateRouteAccess(pathname, request.cookies.has(SESSION_COOKIE_NAME), search);
  if (decision.kind === 'redirect') {
    return NextResponse.redirect(new URL(decision.to, request.url));
  }
  return NextResponse.next();
}

export const config = {
  // Everything except Next's own static assets (dotted paths are files).
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};
