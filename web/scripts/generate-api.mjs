#!/usr/bin/env node
/**
 * Generate `lib/api/generated/` from the canonical OpenAPI document
 * (MT-4.1-03; NFR-11; Section 19.6 — one document, two consumers).
 *
 * Pipeline: `schemas/openapi.yaml` (read-only — backend's MT-1.1-04 artifact)
 * → parsed with the `yaml` package → normalized JSON handed to
 * @hey-api/openapi-ts (pinned exact in package.json; its CLI currently emits
 * nothing for `.yaml` input, and feeding JSON keeps the conversion
 * deterministic and side-effect free). The intermediate file lives under
 * `node_modules/.cache/` (never committed) and is removed on exit.
 *
 * Usage:
 *   node scripts/generate-api.mjs [--input <yaml|json>] [--output <dir>]
 *
 * Defaults are the committed drift-gate paths; `--input`/`--output` exist for
 * the MT-4.1-03 tests (drift simulation and determinism runs against scratch
 * copies — the real document is never mutated).
 */
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { parse as parseYaml } from 'yaml';

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const repoRoot = path.resolve(webRoot, '..');

function readArgs(argv) {
  const options = {
    input: path.join(repoRoot, 'schemas', 'openapi.yaml'),
    output: path.join(webRoot, 'lib', 'api', 'generated'),
  };
  for (let i = 0; i < argv.length; i += 1) {
    const flag = argv[i];
    if (flag === '--input' || flag === '--output') {
      const value = argv[i + 1];
      if (value === undefined) {
        console.error(`generate:api: ${flag} requires a value`);
        process.exit(2);
      }
      i += 1;
      const resolved = path.resolve(webRoot, value);
      if (flag === '--input') options.input = resolved;
      else options.output = resolved;
    } else {
      console.error(`generate:api: unknown argument ${flag}`);
      process.exit(2);
    }
  }
  return options;
}

/** YAML or JSON in → deterministic JSON out (intermediate path is stable). */
function writeNormalizedInput(inputPath) {
  const cacheDir = path.join(webRoot, 'node_modules', '.cache', 'orchestrator-openapi');
  mkdirSync(cacheDir, { recursive: true });
  const target = path.join(cacheDir, 'input.json');
  const raw = readFileSync(inputPath, 'utf8');
  const document = inputPath.endsWith('.json') ? JSON.parse(raw) : parseYaml(raw);
  if (document === null || typeof document !== 'object' || document.paths === undefined) {
    console.error(
      `generate:api: ${inputPath} parsed but carries no paths — refusing to emit an empty client`,
    );
    process.exit(1);
  }
  // Key order comes straight from the document; JSON.stringify is stable for
  // the same input, which is what the drift gate compares against.
  writeFileSync(target, `${JSON.stringify(document)}\n`, 'utf8');
  return target;
}

function runGenerator(inputPath, outputPath) {
  const bin = path.join(webRoot, 'node_modules', '@hey-api', 'openapi-ts', 'bin', 'run.js');
  if (!existsSync(bin)) {
    console.error('generate:api: @hey-api/openapi-ts is not installed — run `npm ci --prefix web`');
    process.exit(1);
  }
  // Paths are passed relative to webRoot (forward slashes on every OS — the
  // generator bakes the input path into the output, so separators must not
  // differ between Windows dev machines and Linux CI) so nothing
  // machine-specific can leak into the generated output (Section 20.4 item 3).
  const relative = (target) => path.relative(webRoot, target).split(path.sep).join('/');
  const result = spawnSync(
    process.execPath,
    [bin, '-i', relative(inputPath), '-o', relative(outputPath), '--no-log-file'],
    { cwd: webRoot, stdio: 'inherit' },
  );
  if (result.error) {
    console.error(`generate:api: failed to launch the generator: ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function assertNonEmptyOutput(outputPath) {
  const index = path.join(outputPath, 'index.ts');
  if (!existsSync(index) || readFileSync(index, 'utf8').trim() === '') {
    console.error(
      `generate:api: the generator produced no output under ` +
        `${path.relative(webRoot, outputPath)} — refusing to leave an empty client in place`,
    );
    process.exit(1);
  }
}

const { input, output } = readArgs(process.argv.slice(2));
if (!existsSync(input)) {
  console.error(`generate:api: input document not found: ${input}`);
  process.exit(1);
}

const normalized = writeNormalizedInput(input);
try {
  runGenerator(normalized, output);
  assertNonEmptyOutput(output);
} finally {
  rmSync(normalized, { force: true });
}
