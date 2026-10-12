/**
 * TEMPORARY HTTP wrapper (MT-4.1-02).
 *
 * NFR-11 requires a single generated typed client (MT-4.1-03). That task's
 * dependency (schema-versioning conventions) has not landed yet, so this
 * narrow wrapper is the explicitly-sanctioned interim call surface from
 * MT-4.1-02's risk notes ("a temporary narrow login call clearly replaced in
 * the same WP"): it carries no hand-written endpoint/type catalog beyond the
 * auth payloads, and every call goes through the same-origin `/api/v1` proxy
 * (next.config.ts). Replace `lib/api/*` wholesale when the generated client
 * lands — see the WP changelog.
 */
import { CSRF_COOKIE_NAME, CSRF_HEADER_NAME, readCookie } from '@/lib/auth/cookies';
import { parseErrorEnvelope, type ErrorEnvelope } from '@/lib/errors/envelope';

/** Base path of the canonical contract (`schemas/openapi.yaml`). */
export const API_BASE_PATH = '/api/v1';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryable: boolean;
  readonly details: Record<string, unknown> | null;
  readonly correlationId: string;

  constructor(status: number, envelope: ErrorEnvelope | null) {
    // `envelope.message` stays on Error.message for logs — UI code must never
    // render it as primary text (Section 13.3; G-07); presentation is driven
    // by `code` through lib/errors (MT-4.1-04).
    super(envelope?.message ?? 'Request failed.');
    this.name = 'ApiError';
    this.status = status;
    this.code = envelope?.code ?? 'SERVER_ERROR';
    this.retryable = envelope?.retryable ?? status >= 500;
    this.details = envelope?.details ?? null;
    this.correlationId = envelope?.correlation_id ?? '';
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

type UnauthorizedHandler = () => void;

let unauthorizedHandler: UnauthorizedHandler | null = null;

/**
 * Register the silent `AUTH_REQUIRED` handler (Section 13.2 behaviour): the
 * session provider sets it once; tests inject spies. Unregistering passes
 * null.
 */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
}

/**
 * Perform an API request against the same-origin proxy. Non-2xx responses
 * become `ApiError`s parsed from the Section 9.2 envelope; a mid-session
 * `AUTH_REQUIRED` additionally fires the registered silent-redirect handler —
 * except on the login endpoint itself, where it is a credential failure the
 * form renders inline.
 */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? 'GET').toUpperCase();
  const headers = new Headers(init?.headers);
  if (init?.body !== undefined && init?.body !== null && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  // CSRF half of the session credentials: duplicate the csrftoken cookie into
  // the X-CSRFToken header for every mutation (MT-1.2-01 contract).
  if (method !== 'GET' && method !== 'HEAD') {
    const csrf = readCookie(CSRF_COOKIE_NAME);
    if (csrf) {
      headers.set(CSRF_HEADER_NAME, csrf);
    }
  }

  const response = await fetch(`${API_BASE_PATH}${path}`, {
    ...init,
    method,
    headers,
    credentials: 'include',
  });

  if (response.ok) {
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Non-JSON error body (proxy/infrastructure failure) → envelope-less.
  }
  const envelope = parseErrorEnvelope(body);
  const error = new ApiError(response.status, envelope);

  if (error.code === 'AUTH_REQUIRED' && !path.startsWith('/auth/login')) {
    unauthorizedHandler?.();
  }
  throw error;
}
