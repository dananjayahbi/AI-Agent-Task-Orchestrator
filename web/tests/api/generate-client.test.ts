/**
 * Generation gate tests (MT-4.1-03; WP-4.1 acceptance: "client regeneration
 * fails CI when schema drifts"):
 *
 *  1. determinism — two runs over the same document produce identical output
 *     (the property `check:api`'s `git diff --exit-code` relies on);
 *  2. drift simulation — a mutated copy of schemas/openapi.yaml generates a
 *     different client, so a fresh generation against a stale commit fails
 *     the gate (the mutated document is a scratch copy; the canonical file
 *     is never written);
 *  3. hand-edit detection — regeneration overwrites edits under
 *     lib/api/generated, so a hand-edited committed client diffs and fails.
 *
 * Scratch output lives under node_modules/.cache (never committed); the real
 * `check:api` gate runs in CI on `.github/workflows/lint-type.yaml`.
 */
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterAll, describe, expect, it } from 'vitest';

import { parse as parseYaml } from 'yaml';

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const repoRoot = path.resolve(webRoot, '..');
const generateScript = path.join(webRoot, 'scripts', 'generate-api.mjs');
const scratchRoot = path.join(webRoot, 'node_modules', '.cache', 'api-gen-tests');

const TEST_TIMEOUT_MS = 120_000;

function runGenerate(args: string[]): void {
  const result = spawnSync(process.execPath, [generateScript, ...args], {
    cwd: webRoot,
    stdio: 'ignore',
  });
  if (result.status !== 0) {
    throw new Error(`generate-api.mjs exited with status ${result.status} (${args.join(' ')})`);
  }
}

/** relPath → content hash for every file under dir (empty map when missing). */
function hashDir(dir: string): Map<string, string> {
  const hashes = new Map<string, string>();
  if (!exists(dir)) return hashes;
  const walk = (current: string) => {
    for (const entry of readdirSync(current)) {
      const full = path.join(current, entry);
      if (statSync(full).isDirectory()) {
        walk(full);
      } else {
        const rel = path.relative(dir, full).split(path.sep).join('/');
        hashes.set(rel, createHash('sha256').update(readFileSync(full)).digest('hex'));
      }
    }
  };
  walk(dir);
  return hashes;
}

function exists(target: string): boolean {
  try {
    return statSync(target) !== undefined;
  } catch {
    return false;
  }
}

afterAll(() => {
  rmSync(scratchRoot, { recursive: true, force: true });
});

describe('typed client generation gate (MT-4.1-03)', () => {
  it(
    'is deterministic: two runs over the canonical document produce identical output',
    () => {
      mkdirSync(scratchRoot, { recursive: true });
      const run1 = path.join(scratchRoot, 'run1');
      const run2 = path.join(scratchRoot, 'run2');
      runGenerate(['--output', run1]);
      runGenerate(['--output', run2]);

      const first = hashDir(run1);
      const second = hashDir(run2);
      expect(first.size).toBeGreaterThan(10);
      expect([...second.keys()].sort()).toEqual([...first.keys()].sort());
      for (const [file, hash] of first) {
        expect(second.get(file), `nondeterministic output for ${file}`).toBe(hash);
      }
    },
    TEST_TIMEOUT_MS,
  );

  it(
    'fails the drift comparison when the schema changes (mutated document → different client)',
    () => {
      mkdirSync(scratchRoot, { recursive: true });
      // Copy + mutate the canonical document (string-level, so the copy keeps
      // the original structure): one renamed query parameter is enough to
      // change the generated surface.
      const canonical = readFileSync(path.join(repoRoot, 'schemas', 'openapi.yaml'), 'utf8');
      const mutated = canonical.replace('name: page_size', 'name: page_size_mutated');
      expect(mutated).not.toBe(canonical);
      expect(parseYaml(mutated)).toBeTruthy(); // still a valid document
      const mutatedDoc = path.join(scratchRoot, 'mutated-openapi.yaml');
      writeFileSync(mutatedDoc, mutated, 'utf8');

      const baseline = path.join(scratchRoot, 'baseline');
      const drifted = path.join(scratchRoot, 'drifted');
      runGenerate(['--output', baseline]);
      runGenerate(['--input', mutatedDoc, '--output', drifted]);

      const fresh = hashDir(baseline);
      const afterChange = hashDir(drifted);
      // Equivalent of `git diff --exit-code -- lib/api/generated` in CI:
      // a schema change makes the fresh generation differ from the committed
      // one, so the gate turns red until `generate:api` output is recommitted.
      expect(afterChange).not.toEqual(fresh);
    },
    TEST_TIMEOUT_MS,
  );

  it(
    'overwrites hand edits (regeneration restores the committed surface)',
    () => {
      mkdirSync(scratchRoot, { recursive: true });
      const out = path.join(scratchRoot, 'hand-edit');
      runGenerate(['--output', out]);

      const sdkFile = path.join(out, 'sdk.gen.ts');
      const pristine = readFileSync(sdkFile, 'utf8');
      writeFileSync(sdkFile, `${pristine}\n// hand edit that must not survive\n`, 'utf8');

      runGenerate(['--output', out]);
      // The edit is gone — so a committed hand edit differs from a fresh
      // generation and `check:api` fails it in CI.
      expect(readFileSync(sdkFile, 'utf8')).toBe(pristine);
    },
    TEST_TIMEOUT_MS,
  );
});
