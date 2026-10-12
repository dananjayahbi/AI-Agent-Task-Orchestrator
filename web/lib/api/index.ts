export { apiFetch, ApiError, isApiError, setUnauthorizedHandler } from '@/lib/api/client';
export { loginRequest, logoutRequest } from '@/lib/api/auth';

/**
 * API entry seam (MT-4.1-01). Everything the app sends to the backend flows
 * through this module; when MT-4.1-03 generates the typed client from
 * `schemas/openapi.yaml`, the generated package replaces these exports so
 * consumers keep importing from `@/lib/api` (NFR-11 single-client rule).
 */
