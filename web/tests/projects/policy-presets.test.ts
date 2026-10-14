/**
 * MT-4.10-03 drift pin: the client's policy-preset transcription must
 * equal WP-3.1's server library, byte for glob. The backend file is the
 * source of record — a preset edit there without a matching client edit
 * fails here (recorded in the WP changelog).
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

import { globProblem } from '@/lib/forms/project-schemas';
import {
  POLICY_PRESETS,
  POLICY_PRESET_IDS,
  PRESET_LIBRARY_VERSION,
} from '@/lib/projects/policy-presets';

// Vitest runs from `web/` — the backend library is the source of record.
const BACKEND_SOURCE = readFileSync(
  resolve(process.cwd(), '../backend/apps/projects/policy_presets.py'),
  'utf8',
);

type GlobFields = ['critical_path_globs', 'migration_path_globs', 'sensitive_config_globs'];
const GLOB_FIELDS: GlobFields = [
  'critical_path_globs',
  'migration_path_globs',
  'sensitive_config_globs',
];

function backendPresetBlock(presetId: string): string {
  const start = BACKEND_SOURCE.indexOf(`id="${presetId}"`);
  if (start < 0) {
    throw new Error(`preset ${presetId} missing from backend library`);
  }
  const nextPreset = BACKEND_SOURCE.indexOf(': Final[PolicyPreset]', start + 10);
  const presetsTable = BACKEND_SOURCE.indexOf('PRESETS: Final', start);
  const candidates = [nextPreset, presetsTable].filter((index) => index > start);
  const end = candidates.length > 0 ? Math.min(...candidates) : BACKEND_SOURCE.length;
  return BACKEND_SOURCE.slice(start, end);
}

function backendGlobs(block: string, field: string): string[] {
  const match = new RegExp(`${field}=\\(([\\s\\S]*?)\\n\\s*\\)`).exec(block);
  if (match === null) {
    throw new Error(`no ${field} tuple in backend block`);
  }
  return Array.from(match[1].matchAll(/"([^"]*)"/g), (entry) => entry[1]);
}

describe('policy preset transcription (MT-4.10-03)', () => {
  it('pins PRESET_LIBRARY_VERSION to the backend constant', () => {
    const match = /PRESET_LIBRARY_VERSION: Final\[int\] = (\d+)/.exec(BACKEND_SOURCE);
    expect(match).not.toBeNull();
    expect(PRESET_LIBRARY_VERSION).toBe(Number(match?.[1]));
  });

  it.each(POLICY_PRESET_IDS)('transcribes the %s preset exactly', (presetId) => {
    const block = backendPresetBlock(presetId);
    const client = POLICY_PRESETS[presetId];
    for (const field of GLOB_FIELDS) {
      // Verbatim: same entries in the same order (no sorting — drift in
      // order is drift a reviewer should see).
      expect(client[field]).toEqual(backendGlobs(block, field));
    }
  });

  it('every transcribed glob passes the Section 12.3 mirror (the server would accept it)', () => {
    for (const presetId of POLICY_PRESET_IDS) {
      const preset = POLICY_PRESETS[presetId];
      for (const field of GLOB_FIELDS) {
        for (const glob of preset[field]) {
          expect(`${presetId}:${glob}:${globProblem(glob)}`).toBe(`${presetId}:${glob}:null`);
        }
      }
    }
  });
});
