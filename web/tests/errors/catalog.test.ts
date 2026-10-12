import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { parse } from 'yaml';
import { describe, expect, it } from 'vitest';

import {
  CANONICAL_ERROR_CODES,
  ERROR_CATALOG,
  GENERIC_ERROR,
  isErrorCode,
} from '@/lib/errors/catalog';
import { resolveError } from '@/lib/errors/resolve';

/**
 * Catalog completeness gate (MT-4.1-04 acceptance; Section 19.6's two-sided
 * rule): the published `CodeEnum` in `schemas/openapi.yaml` (MT-1.1-04's
 * artifact) and the web mapping must stay in lockstep — a new backend code
 * fails this suite until a friendly entry lands here.
 */
function publishedCodes(): string[] {
  // Tests run with cwd = web/ (npm --prefix web run test).
  const openapiPath = resolve(process.cwd(), '../schemas/openapi.yaml');
  const document = parse(readFileSync(openapiPath, 'utf8')) as {
    components: { schemas: { CodeEnum: { enum: string[] } } };
  };
  return document.components.schemas.CodeEnum.enum;
}

describe('error catalog vs the published OpenAPI code list', () => {
  it('maps every published code, with none invented', () => {
    const published = publishedCodes();
    const mapped = [...CANONICAL_ERROR_CODES].sort();

    expect(published.slice().sort()).toEqual(mapped);
    expect(published.every((code) => isErrorCode(code))).toBe(true);
  });

  it('gives every catalog code a distinct friendly message and title', () => {
    for (const code of CANONICAL_ERROR_CODES) {
      const entry = ERROR_CATALOG[code];
      expect(entry.message.length).toBeGreaterThan(0);
      expect(entry.title.length).toBeGreaterThan(0);
      expect(['redirect', 'inline', 'toast', 'state']).toContain(entry.presentation);
    }
    const messages = CANONICAL_ERROR_CODES.map((code) => ERROR_CATALOG[code].message);
    expect(new Set(messages).size).toBe(messages.length);
  });
});

describe('resolveError', () => {
  it('resolves a catalog code to its friendly entry with the correlation id', () => {
    const friendly = resolveError({
      code: 'AUTH_FORBIDDEN_PROJECT',
      message: 'internal authorization detail',
      correlation_id: 'corr-403',
    });

    expect(friendly.code).toBe('AUTH_FORBIDDEN_PROJECT');
    expect(friendly.title).toBe(ERROR_CATALOG.AUTH_FORBIDDEN_PROJECT.title);
    expect(friendly.message).toBe(ERROR_CATALOG.AUTH_FORBIDDEN_PROJECT.message);
    expect(friendly.presentation).toBe('state');
    expect(friendly.requestId).toBe('corr-403');
  });

  it('accepts the camelCase ApiError shape too', () => {
    const friendly = resolveError({ code: 'RATE_LIMITED', correlationId: 'corr-429' });
    expect(friendly.message).toBe(ERROR_CATALOG.RATE_LIMITED.message);
    expect(friendly.requestId).toBe('corr-429');
  });

  it('degrades unknown codes to the generic message plus request id (Section 13.3)', () => {
    const friendly = resolveError({
      code: 'FUTURE_BACKEND_CODE',
      message: 'raw server text that must never render',
      correlation_id: 'corr-unknown',
    });

    expect(friendly.title).toBe(GENERIC_ERROR.title);
    expect(friendly.message).toBe(GENERIC_ERROR.message);
    expect(friendly.presentation).toBe('state');
    expect(friendly.requestId).toBe('corr-unknown');
    expect(friendly.message).not.toContain('raw server text');
  });

  it('degrades unusable input without a request id', () => {
    expect(resolveError(null)).toMatchObject({ message: GENERIC_ERROR.message, requestId: '' });
    expect(resolveError(new Error('internal stack'))).toMatchObject({
      message: GENERIC_ERROR.message,
      requestId: '',
    });
  });

  it('never surfaces the raw envelope message for catalog codes (G-07)', () => {
    const serverText = 'SequelizeConnectionError: connect ECONNREFUSED 10.0.0.5';
    for (const code of CANONICAL_ERROR_CODES) {
      const friendly = resolveError({ code, message: serverText, correlation_id: 'c1' });
      expect(friendly.message).not.toBe(serverText);
      expect(friendly.message).not.toContain('ECONNREFUSED');
    }
  });
});
