import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  AUDITOR_RULES,
  CODER_RULES,
  DEFAULT_LEASE_MINUTES,
  PROJECT_RULES_MAX_CHARS,
  checkpointIntervalMinutes,
  normalizeProjectRules,
  renderRulesPreview,
} from '@/lib/projects/agent-rules';

// Vitest runs from `web/` — the bridge module is the WP-2.7 source of
// record (Section 20.5: the preview must not diverge from delivery).
const BRIDGE_SOURCE = readFileSync(
  resolve(process.cwd(), '../bridge/src/orchestrator_bridge/rules.py'),
  'utf8',
);

/** Extract a Python `tuple[str, ...]` constant, joining implicit string
 * concatenations; string-aware so parens inside rule text don't break the
 * block scan. */
function parsePythonTuple(name: string): string[] {
  const marker = `${name}: Final[tuple[str, ...]] = (`;
  const markerAt = BRIDGE_SOURCE.indexOf(marker);
  expect(markerAt, `${name} present in bridge rules.py`).toBeGreaterThan(-1);
  const openAt = BRIDGE_SOURCE.indexOf('(', markerAt);
  let depth = 0;
  let inString = false;
  let quote = '';
  let closeAt = -1;
  for (let i = openAt; i < BRIDGE_SOURCE.length; i += 1) {
    const ch = BRIDGE_SOURCE[i];
    if (inString) {
      if (ch === '\\') {
        i += 1;
        continue;
      }
      if (ch === quote) {
        inString = false;
      }
      continue;
    }
    if (ch === '"' || ch === "'") {
      inString = true;
      quote = ch;
      continue;
    }
    if (ch === '(') {
      depth += 1;
    } else if (ch === ')') {
      depth -= 1;
      if (depth === 0) {
        closeAt = i;
        break;
      }
    }
  }
  expect(closeAt, `${name} block closed`).toBeGreaterThan(openAt);
  const body = BRIDGE_SOURCE.slice(openAt + 1, closeAt);
  const items: string[] = [];
  let current = '';
  inString = false;
  quote = '';
  for (let i = 0; i < body.length; i += 1) {
    const ch = body[i];
    if (inString) {
      current += ch;
      if (ch === '\\') {
        current += body[i + 1];
        i += 1;
        continue;
      }
      if (ch === quote) {
        inString = false;
      }
      continue;
    }
    if (ch === '"' || ch === "'") {
      inString = true;
      quote = ch;
      current += ch;
      continue;
    }
    if (ch === ',') {
      if (current.trim()) {
        items.push(current.trim());
      }
      current = '';
      continue;
    }
    current += ch;
  }
  if (current.trim()) {
    items.push(current.trim());
  }
  return items.map((raw) => {
    const literals = raw.match(/"(?:[^"\\]|\\.)*"/g);
    expect(literals, `string literals in ${raw}`).not.toBeNull();
    return (literals ?? []).map((lit) => JSON.parse(lit) as string).join('');
  });
}

function pyIntConst(name: string): number {
  const match = BRIDGE_SOURCE.match(new RegExp(`${name}: Final = (\\d+)`));
  expect(match, `${name} present in bridge rules.py`).not.toBeNull();
  return Number(match?.[1]);
}

describe('agent rules transcription (Section 10.6 / WP-2.7 drift pin)', () => {
  it('pins the eight coder rules verbatim and in order', () => {
    expect(CODER_RULES).toEqual(parsePythonTuple('CODER_RULES'));
    expect(CODER_RULES).toHaveLength(8);
  });

  it('pins the four auditor obligations verbatim and in order', () => {
    expect(AUDITOR_RULES).toEqual(parsePythonTuple('AUDITOR_RULES'));
    expect(AUDITOR_RULES).toHaveLength(4);
  });

  it('pins the lease default and the project-rules cap', () => {
    expect(DEFAULT_LEASE_MINUTES).toBe(pyIntConst('DEFAULT_LEASE_MINUTES'));
    expect(PROJECT_RULES_MAX_CHARS).toBe(pyIntConst('PROJECT_RULES_MAX_CHARS'));
    expect(DEFAULT_LEASE_MINUTES).toBe(45);
    expect(PROJECT_RULES_MAX_CHARS).toBe(8000);
  });

  it('derives the checkpoint cadence as one third of the lease, min 1', () => {
    expect(checkpointIntervalMinutes(45)).toBe(15);
    expect(checkpointIntervalMinutes(6)).toBe(2);
    expect(checkpointIntervalMinutes(5)).toBe(1);
    expect(checkpointIntervalMinutes(1)).toBe(1);
    expect(checkpointIntervalMinutes(0)).toBe(1);
  });

  it('normalises project rules like the bridge: strip controls, cap with marker', () => {
    expect(
      normalizeProjectRules(
        'a' + String.fromCharCode(0) + 'b\r\nkeep\tc' + String.fromCharCode(127) + 'd  ',
      ),
    ).toBe('ab\nkeep\tcd');
    const over = 'x'.repeat(PROJECT_RULES_MAX_CHARS + 10);
    const capped = normalizeProjectRules(over);
    expect(capped.endsWith('\n[project rules truncated: limit reached]')).toBe(true);
    expect(capped.startsWith('x'.repeat(PROJECT_RULES_MAX_CHARS))).toBe(true);
  });

  it('renders the coder block with generic slots and appends project rules', () => {
    const preview = renderRulesPreview('coder', 'Owner rule A');
    expect(preview.startsWith('Coder rules (Section 10.6):')).toBe(true);
    expect(preview).toContain('the branch returned by claim_task');
    expect(preview).toContain("the task's test command (from get_task_details)");
    expect(preview).toContain('at least every 15 minutes');
    expect(preview.indexOf('Project rules:')).toBeGreaterThan(
      preview.indexOf('8. Provide a clear'),
    );
    expect(preview.endsWith('Owner rule A')).toBe(true);
  });

  it('renders auditor rules without slots and omits an empty project section', () => {
    const preview = renderRulesPreview('auditor', '   \n  ');
    expect(preview.startsWith('Auditor rules (Section 10.6):')).toBe(true);
    expect(preview).toContain("1. Run the project's full test and lint matrix.");
    expect(preview).not.toContain('Project rules:');
    expect(preview).not.toContain('{branch}');
  });
});
