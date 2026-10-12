/**
 * API entry seam (MT-4.1-01, fulfilled by MT-4.1-03): everything the app
 * sends to the backend flows through this module. Endpoint functions and
 * contract types are re-exported from the generated client
 * (NFR-11 — one generated surface, no hand-written duplicate types;
 * Section 19.6), plus the small transport/error glue in `./client`.
 */
export { ApiError, callApi, isApiError, setUnauthorizedHandler } from '@/lib/api/client';
export { loginRequest, logoutRequest } from '@/lib/api/auth';

// Generated sdk — endpoint operations (call them through `callApi`).
export * from '@/lib/api/generated/sdk.gen';

// Generated contract types — request/response shapes straight from
// schemas/openapi.yaml.
export type * from '@/lib/api/generated/types.gen';
