import { describe, expect, it } from 'vitest';

import { evaluateRouteAccess } from '@/lib/auth/guard';
import { sanitizeReturnPath } from '@/lib/auth/return-path';

/**
 * Route-gate matrix (MT-4.1-02 acceptance): every Section 13.1 route except
 * Login is unreachable unauthenticated — redirecting with a return path —
 * while API paths always pass through to the authoritative backend.
 */
const PROTECTED_ROUTES = [
  '/',
  '/projects',
  '/projects/PID00001',
  '/projects/PID00001/board',
  '/projects/PID00001/tasks/PID00001-T00007',
  '/projects/PID00001/settings',
  '/review',
  '/agents',
  '/audit-log',
  '/settings',
] as const;

describe('evaluateRouteAccess', () => {
  it.each(PROTECTED_ROUTES)(
    'redirects unauthenticated visits to %s with a return path',
    (route) => {
      const decision = evaluateRouteAccess(route, false);
      expect(decision.kind).toBe('redirect');
      if (decision.kind !== 'redirect') {
        return;
      }
      expect(decision.to.startsWith('/login?next=')).toBe(true);
      expect(decodeURIComponent(decision.to.split('next=')[1])).toBe(route);
    },
  );

  it.each(PROTECTED_ROUTES)('allows authenticated visits to %s', (route) => {
    expect(evaluateRouteAccess(route, true)).toEqual({ kind: 'allow' });
  });

  it('keeps the query string in the return path', () => {
    const decision = evaluateRouteAccess('/review', false, '?sort=age');
    expect(decision).toEqual({
      kind: 'redirect',
      to: `/login?next=${encodeURIComponent('/review?sort=age')}`,
    });
  });

  it('shows login to unauthenticated visitors', () => {
    expect(evaluateRouteAccess('/login', false)).toEqual({ kind: 'allow' });
  });

  it('bounces authenticated visitors on /login to the Board', () => {
    expect(evaluateRouteAccess('/login', true)).toEqual({ kind: 'redirect', to: '/' });
  });

  it('never gates API paths — the backend answers AUTH_REQUIRED itself', () => {
    expect(evaluateRouteAccess('/api/v1/auth/login', false)).toEqual({ kind: 'allow' });
    expect(evaluateRouteAccess('/api/v1/projects', false)).toEqual({ kind: 'allow' });
    expect(evaluateRouteAccess('/api/v1/tasks/PID00001-T00001', true)).toEqual({
      kind: 'allow',
    });
  });
});

describe('sanitizeReturnPath', () => {
  it('accepts same-origin absolute paths', () => {
    expect(sanitizeReturnPath('/projects/PID00001/board')).toBe('/projects/PID00001/board');
  });

  it('falls back to the Board for missing or unsafe targets', () => {
    expect(sanitizeReturnPath(undefined)).toBe('/');
    expect(sanitizeReturnPath('')).toBe('/');
    expect(sanitizeReturnPath('//evil.example')).toBe('/');
    expect(sanitizeReturnPath('/\\evil.example')).toBe('/');
    expect(sanitizeReturnPath('https://evil.example')).toBe('/');
    expect(sanitizeReturnPath('/login')).toBe('/');
  });

  it('honours an explicit fallback', () => {
    expect(sanitizeReturnPath('//evil.example', '/review')).toBe('/review');
  });
});
