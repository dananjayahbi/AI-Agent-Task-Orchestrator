/**
 * Error-envelope parsing (MT-4.1-02 wiring; shape owned by MT-0.5-02 /
 * parent plan Section 9.2 — five fields, canonical `code`).
 *
 * The canonical wire shape nests the five fields under `error` (Section 9.2
 * example, backend/apps/core/errors.py), and `schemas/openapi.yaml`'s
 * `ErrorEnvelope` component now declares exactly that nesting (the flat
 * rendering was a contract bug, closed at the Wave 2 end-of-wave gate). The
 * parser still accepts a flat top-level body as a defensive fallback for
 * cached or older responses.
 */
export type ErrorEnvelope = {
  code: string;
  message: string;
  retryable: boolean;
  details: Record<string, unknown> | null;
  correlation_id: string;
};

function asEnvelope(value: unknown): ErrorEnvelope | null {
  if (typeof value !== 'object' || value === null) {
    return null;
  }
  const record = value as Record<string, unknown>;
  if (typeof record.code !== 'string' || record.code === '') {
    return null;
  }
  return {
    code: record.code,
    message: typeof record.message === 'string' ? record.message : '',
    retryable: record.retryable === true,
    details:
      typeof record.details === 'object' && record.details !== null
        ? (record.details as Record<string, unknown>)
        : null,
    correlation_id: typeof record.correlation_id === 'string' ? record.correlation_id : '',
  };
}

/** Parse a non-2xx response body into the envelope, or null when unusable. */
export function parseErrorEnvelope(body: unknown): ErrorEnvelope | null {
  if (typeof body !== 'object' || body === null) {
    return null;
  }
  const nested = (body as Record<string, unknown>).error;
  if (nested !== undefined) {
    return asEnvelope(nested);
  }
  return asEnvelope(body);
}
