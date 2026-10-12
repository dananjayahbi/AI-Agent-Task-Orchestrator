/**
 * TEMPORARY narrow auth calls (MT-4.1-02) — the interim seam named by
 * MT-4.1-02's risk notes until MT-4.1-03 generates the typed client from
 * `schemas/openapi.yaml`. Field names below mirror the contract:
 * LoginRequest {username, password} → OwnerSession {token, expires_at, user};
 * POST /auth/logout → Revoked {revoked_at} (schemas/openapi.yaml).
 */
import { apiFetch } from '@/lib/api/client';
import type { SessionUser } from '@/lib/session/store';

export type LoginCredentials = {
  username: string;
  password: string;
};

type LoginResponse = {
  token: string;
  expires_at: string;
  user: { id: number; username: string };
};

/**
 * Exchange credentials for the backend session (HTTP-only cookie set by the
 * response — the app stores no credential itself, Section 12.2). The
 * response's `token` (the plaintext binding for bearer clients, Section 15.4)
 * is deliberately discarded: only the identity crosses into client state.
 */
export async function loginRequest(credentials: LoginCredentials): Promise<SessionUser> {
  const session = await apiFetch<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
  return { id: session.user.id, username: session.user.username };
}

/**
 * Revoke the backend session (idempotent server-side). CSRF header handled by
 * apiFetch. An `AUTH_REQUIRED` here means the session already expired — the
 * caller still clears local state and redirects (MT-4.1-02 acceptance).
 */
export async function logoutRequest(): Promise<void> {
  await apiFetch<unknown>('/auth/logout', { method: 'POST' });
}
