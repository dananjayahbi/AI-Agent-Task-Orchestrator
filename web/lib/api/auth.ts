/**
 * Owner-session flow calls (MT-4.1-02 surface, now backed by the generated
 * client per MT-4.1-03 — the response types come from
 * `@/lib/api/generated/types.gen`, not hand-written copies).
 */
import { callApi } from '@/lib/api/client';
import { apiV1AuthLoginCreate, apiV1AuthLogoutCreate } from '@/lib/api/generated/sdk.gen';
import type { LoginRequest, OwnerSession } from '@/lib/api/generated/types.gen';
import type { SessionUser } from '@/lib/session/store';

/**
 * Exchange credentials for the backend session (HTTP-only cookie set by the
 * response — the app stores no credential itself, Section 12.2). The
 * response's `token` (the plaintext binding for bearer clients, Section 15.4)
 * is deliberately discarded: only the identity crosses into client state.
 */
export async function loginRequest(credentials: LoginRequest): Promise<SessionUser> {
  const session = await callApi<OwnerSession>(apiV1AuthLoginCreate({ body: credentials }));
  return { id: session.user.id, username: session.user.username };
}

/**
 * Revoke the backend session (idempotent server-side). CSRF header handled by
 * the generated client's request interceptor. An `AUTH_REQUIRED` here means
 * the session already expired — the caller still clears local state and
 * redirects (MT-4.1-02 acceptance).
 */
export async function logoutRequest(): Promise<void> {
  await callApi(apiV1AuthLogoutCreate());
}
