import { ERROR_CATALOG, GENERIC_ERROR, isErrorCode, type ErrorEntry } from '@/lib/errors/catalog';

/**
 * Friendly error resolution (MT-4.1-04): the single entry point every UI
 * surface uses. Input is envelope-shaped (`ErrorEnvelope`, `ApiError`, or
 * anything duck-typed with `code` + correlation id); the server's `message`
 * is intentionally never read — presentation copy comes only from the
 * catalog, and unknown codes degrade to the generic entry plus the
 * envelope's `correlation_id` for support (Section 13.3; G-07).
 */
export type FriendlyError = ErrorEntry & {
  code: string;
  /** Envelope `correlation_id` for support; '' when absent. */
  requestId: string;
};

type ErrorLike = {
  code?: unknown;
  correlation_id?: unknown;
  correlationId?: unknown;
};

function readCorrelationId(input: unknown): string {
  if (typeof input !== 'object' || input === null) {
    return '';
  }
  const record = input as ErrorLike;
  if (typeof record.correlationId === 'string') {
    return record.correlationId;
  }
  if (typeof record.correlation_id === 'string') {
    return record.correlation_id;
  }
  return '';
}

export function resolveError(input: unknown): FriendlyError {
  const code =
    typeof input === 'object' && input !== null && typeof (input as ErrorLike).code === 'string'
      ? ((input as ErrorLike).code as string)
      : '';
  const requestId = readCorrelationId(input);

  if (isErrorCode(code)) {
    return { ...ERROR_CATALOG[code], code, requestId };
  }
  return { ...GENERIC_ERROR, code, requestId };
}
