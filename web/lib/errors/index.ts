/**
 * Error-mapping module (MT-4.1-04) — one shared source (Section 19.6).
 * Import from `@/lib/errors` everywhere UI explains a failure.
 */
export {
  CANONICAL_ERROR_CODES,
  ERROR_CATALOG,
  GENERIC_ERROR,
  isErrorCode,
  type ErrorCode,
  type ErrorEntry,
  type Presentation,
} from '@/lib/errors/catalog';
export { resolveError, type FriendlyError } from '@/lib/errors/resolve';
export { parseErrorEnvelope, type ErrorEnvelope } from '@/lib/errors/envelope';
