/**
 * Import-boundary test (MT-4.1-03; NFR-11; Section 19.6) — the app talks to
 * the backend only through the generated client:
 *
 *  1. no hand-written `fetch(` transport outside `lib/api/generated/`;
 *  2. no hand-written endpoint literals (`/api/v1…`) outside the generated
 *     client — the contract owns paths, not app code;
 *  3. the removed temporary wrapper (`apiFetch`) stays gone;
 *  4. the `@/lib/api` barrel re-exports the generated surface.
 *
 * `lib/api/client.ts` is the documented non-API helper (transport glue:
 * runtime config, CSRF header, error normalization) and carries neither
 * endpoint knowledge nor payload types.
 */
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const generatedDir = path.join(webRoot, 'lib', 'api', 'generated');

/** Shipped application source (tests and scripts are tooling, not product). */
const sourceRoots = ['app', 'components', 'lib'];

function listSourceFiles(): string[] {
  const files: string[] = [];
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir)) {
      const full = path.join(dir, entry);
      if (statSync(full).isDirectory()) {
        if (full === generatedDir) continue; // machine-owned output, allowlisted
        walk(full);
        continue;
      }
      if (/\.(ts|tsx)$/.test(entry)) files.push(full);
    }
  };
  for (const root of sourceRoots) walk(path.join(webRoot, root));
  return files;
}

const sourceFiles = listSourceFiles();
const relative = (file: string) => path.relative(webRoot, file).split(path.sep).join('/');

/** Strip comments so the rules police code, not prose about code. */
function codeOnly(file: string): string {
  return readFileSync(file, 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '');
}

describe('API import boundary (generated-client-only access)', () => {
  it('scans a non-trivial amount of application source', () => {
    expect(sourceFiles.length).toBeGreaterThan(10);
    expect(existsSync(path.join(generatedDir, 'index.ts'))).toBe(true);
  });

  it('has no hand-written fetch() calls outside the generated client', () => {
    const offenders = sourceFiles.filter((file) => /\bfetch\s*\(/.test(codeOnly(file)));
    expect(
      offenders.map(relative),
      'fetch wrappers violate NFR-11 — use callApi(<generated sdk fn>) via @/lib/api',
    ).toEqual([]);
  });

  it('has no hand-written endpoint path literals outside the generated client', () => {
    const offenders = sourceFiles.filter((file) => codeOnly(file).includes("'/api/v1"));
    expect(
      offenders.map(relative),
      'endpoint paths come from schemas/openapi.yaml via the generated sdk, never hand-written',
    ).toEqual([]);
  });

  it('keeps the temporary apiFetch wrapper removed', () => {
    const offenders = sourceFiles.filter((file) => /\bapiFetch\b/.test(codeOnly(file)));
    expect(offenders.map(relative), 'apiFetch was replaced wholesale by MT-4.1-03').toEqual([]);
  });

  it('routes the @/lib/api barrel through the generated sdk and types', () => {
    const barrel = readFileSync(path.join(webRoot, 'lib', 'api', 'index.ts'), 'utf8');
    expect(barrel).toContain('@/lib/api/generated/sdk.gen');
    expect(barrel).toContain('@/lib/api/generated/types.gen');
  });
});
