/**
 * Transport glue over the generated client (MT-4.1-03; NFR-11; Section 19.6).
 *
 * This module owns exactly three concerns that the OpenAPI document cannot
 * express — none of them endpoint or payload knowledge:
 *
 *  1. Runtime configuration of the generated client (same-origin base URL so
 *     every request goes through the next.config.ts `/api/v1/*` proxy from
 *     MT-4.1-01; explicit credentialed fetch for the HTTP-only session
 *     cookie, Section 12.2).
 *  2. The CSRF half of the session transport: the `csrftoken` cookie is
 *     duplicated into the `X-CSRFToken` header on every mutation
 *     (MT-1.2-01 contract, backend/apps/accounts/authentication.py).
 *  3. Normalization of the Section 9.2 error envelope into `ApiError` plus
 *     the silent `AUTH_REQUIRED` redirect hook (Section 13.3; MT-4.1-02/04).
 *
 * The previous temporary `apiFetch` wrapper is gone: every call now flows
 * through the generated sdk in `@/lib/api/generated` (enforced by
 * `tests/api/import-boundary.test.ts`).
 */
import { client as generatedClient } from '@/lib/api/generated/client.gen';
import { CSRF_COOKIE_NAME, CSRF_HEADER_NAME, readCookie } from '@/lib/auth/cookies';
import { parseErrorEnvelope, type ErrorEnvelope } from '@/lib/errors/envelope';

/**
 * The generated sdk paths already carry the `/api/v1` prefix, so the base is
 * just the page origin — requests stay same-origin and the Next rewrite
 * forwards them (MT-4.1-01 design note; no CORS dependency). `window` is
 * absent during SSR, where no calls are made (queries start client-side).
 */
function pageOrigin(): string {
  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin;
  }
  return '';
}

// The generated client.gen.ts bakes a placeholder baseUrl from the generator
// input path (see scripts/generate-api.mjs); the runtime value below always
// overrides it via setConfig — never rely on the baked constant.
generatedClient.setConfig({
  baseUrl: pageOrigin(),
  credentials: 'include',
});

// CSRF duplication for mutations. Registered once at module load; the
// interceptor sees the finished Request before it is sent.
generatedClient.interceptors.request.use((request) => {
  const method = request.method.toUpperCase();
  if (method !== 'GET' && method !== 'HEAD') {
    const csrf = readCookie(CSRF_COOKIE_NAME);
    if (csrf) {
      request.headers.set(CSRF_HEADER_NAME, csrf);
    }
  }
  return request;
});

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

/** The fields `callApi` consumes from every generated sdk result. */
export type GeneratedResult<T> = {
  data?: T;
  error?: unknown;
  request?: Request;
  response?: Response;
};

function requestPath(request: Request | undefined): string {
  if (request === undefined) {
    return '';
  }
  try {
    return new URL(request.url).pathname;
  } catch {
    return request.url;
  }
}

/**
 * Run one generated sdk operation and normalize its outcome:
 *
 * - success → the typed response `data`;
 * - Section 9.2 error → an `ApiError` carrying the canonical `code`
 *   (`resolveError` maps it to friendly copy — never raw server text);
 * - a mid-session `AUTH_REQUIRED` additionally fires the registered silent
 *   redirect — except on the login endpoint itself, where it is a credential
 *   failure the form renders inline (MT-4.1-02 behaviour, preserved).
 *
 * All UI code calls endpoints through `@/lib/api`, which re-exports the
 * generated sdk; this function is the single seam that turns a generated
 * result into app-visible success or failure.
 */
export async function callApi<T>(operation: Promise<GeneratedResult<T>>): Promise<T> {
  let result: GeneratedResult<T>;
  try {
    result = await operation;
  } catch (error) {
    // The generated client is configured without throwOnError; reaching here
    // means the failure happened before/around fetch (e.g. request build).
    if (isApiError(error)) {
      throw error;
    }
    throw new ApiError(0, null);
  }

  if (result.error === undefined) {
    return result.data as T;
  }

  const status = result.response?.status ?? 0;
  const envelope = parseErrorEnvelope(result.error);
  const error = new ApiError(status, envelope);

  if (error.code === 'AUTH_REQUIRED' && !requestPath(result.request).endsWith('/auth/login')) {
    unauthorizedHandler?.();
  }
  throw error;
}
