#!/usr/bin/env node
/**
 * Typed-client drift gate (MT-4.1-03; WP-4.1 acceptance: "client
 * regeneration fails CI when schema drifts").
 *
 * Mirrors MT-1.1-04's OpenAPI snapshot gate UX (same workflow file,
 * `.github/workflows/lint-type.yaml`): regenerate → `git diff --exit-code`
 * over the committed client directory → fail on any difference, including
 * files a hand edit left behind and files the generator added or removed.
 *
 * Usage: node scripts/check-api-drift.mjs   (npm --prefix web run check:api)
 * Exit codes: 0 fresh, 1 drift or generation failure, 2 git unavailable.
 */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const clientDir = 'lib/api/generated';

const REMEDY = `
Typed API client drift detected in ${clientDir}/.

The committed client no longer matches a fresh generation from the canonical
OpenAPI document (schemas/openapi.yaml). To fix:

  npm --prefix web run generate:api

then review and commit the regenerated files. If schemas/openapi.yaml itself
changed, that change needs the Section 20.4 item 4 schema-diff review first
(CONTRIBUTING.md, "Regenerate OpenAPI snapshot") — never hand-edit files under
${clientDir}/; regeneration overwrites them.
`.trim();

function git(args) {
  const result = spawnSync('git', args, { cwd: webRoot, encoding: 'utf8' });
  if (result.error && result.error.code === 'ENOENT') {
    console.error('check:api: git is required for the drift gate but was not found on PATH.');
    process.exit(2);
  }
  return result;
}

// 1. Regenerate from the canonical document (fails the gate on generator error).
const generate = spawnSync(process.execPath, [path.join(webRoot, 'scripts', 'generate-api.mjs')], {
  cwd: webRoot,
  stdio: 'inherit',
});
if (generate.status !== 0) {
  console.error('\ncheck:api: generation failed — the gate stays red until it succeeds.');
  process.exit(generate.status ?? 1);
}

// 2. Committed vs fresh: tracked changes (`git diff --exit-code`) …
const diff = git(['diff', '--exit-code', '--', clientDir]);
let drifted = diff.status !== 0;
if (drifted && diff.stdout) {
  console.error(diff.stdout);
}

// 3. … and files git does not track yet (deleted/new — `git diff` misses those).
const status = git(['status', '--porcelain', '--', clientDir]);
if (status.status !== 0) {
  console.error(status.stderr ?? '');
  process.exit(1);
}
const untracked = (status.stdout ?? '').trim();
if (untracked !== '') {
  console.error(untracked);
  drifted = true;
}

if (drifted) {
  console.error(`\n${REMEDY}`);
  process.exit(1);
}

console.log('check:api: generated client matches schemas/openapi.yaml — no drift.');
