import type { NextConfig } from 'next';

/**
 * API base URL seam (MT-4.1-01; Section 20.4 item 3 — configuration, never a
 * hardcoded value in app code). The browser only ever talks to this app's own
 * origin: `/api/v1/*` is proxied server-side to the backend documented in
 * docs/plan/conventions/configuration.md — `ORCHESTRATOR_API_BASE_URL`,
 * documented default `http://localhost:8000/api/v1` (the value must include
 * the `/api/v1` base path). The same-origin proxy keeps session cookies and
 * CSRF mechanics identical between dev and prod (Section 12.2).
 */
const API_BASE_URL = process.env.ORCHESTRATOR_API_BASE_URL ?? 'http://localhost:8000/api/v1';

function apiUpstream(): string {
  let url: URL;
  try {
    url = new URL(API_BASE_URL);
  } catch {
    throw new Error(
      'ORCHESTRATOR_API_BASE_URL must be an absolute http(s) URL including the ' +
        `/api/v1 base path (see docs/plan/conventions/configuration.md); got: ${API_BASE_URL}`,
    );
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error(`ORCHESTRATOR_API_BASE_URL must be http(s); got: ${url.protocol}`);
  }
  return url.toString().replace(/\/+$/, '');
}

const nextConfig: NextConfig = {
  async rewrites() {
    const base = apiUpstream();
    return [{ source: '/api/v1/:path*', destination: `${base}/:path*` }];
  },
};

export default nextConfig;
