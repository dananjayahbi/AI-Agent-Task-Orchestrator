/**
 * Return-path sanitising for the login flow (MT-4.1-02): after a successful
 * sign-in the user resumes at the `next` target — only same-origin absolute
 * paths are ever honoured, so an injected `//evil.example` or absolute URL
 * can never turn login into an open redirect.
 */
export function sanitizeReturnPath(next: string | undefined | null, fallback = '/'): string {
  if (!next) {
    return fallback;
  }
  if (!next.startsWith('/') || next.startsWith('//') || next.startsWith('/\\')) {
    return fallback;
  }
  if (next.startsWith('/login')) {
    return fallback;
  }
  return next;
}
