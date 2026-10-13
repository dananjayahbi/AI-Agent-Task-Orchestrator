/**
 * Allowed-move map tests (MT-4.4-01; `npm test -- -t allowed-move`).
 *
 * Table-driven over the full 6×6 source×target matrix (every pair resolves
 * to exactly one verdict), plus one spot assertion per Section 13.2 bullet,
 * canonical-key discipline (ADR-010), and stable rejection explanations
 * (the "rejected with an explanation" WP-4.4 exit criterion starts here).
 */
import { describe, expect, it } from 'vitest';

import {
  evaluateMove,
  MOVE_MAP,
  REJECTED_AGENT_OWNED_EXPLANATION,
  REJECTED_NOT_OWNER_VALID_EXPLANATION,
  REJECTED_SAME_STATE_EXPLANATION,
} from '@/lib/board/move-map';
import { BOARD_STATES, STATE_LABELS, type BoardState } from '@/lib/board/states';

type Expected =
  | { kind: 'allowed'; action: 'publish' | 'unpublish' }
  | { kind: 'dialog'; dialog: 'approve_merge' | 'request_changes' }
  | { kind: 'rejected'; reason: 'agent_owned' | 'same_state' | 'not_owner_valid' };

/**
 * Section 13.2 rules as a literal table: a plan change that is not mirrored
 * here fails the test (drift guard against Section 8.2).
 */
const MATRIX: Record<BoardState, Record<BoardState, Expected>> = {
  draft: {
    draft: { kind: 'rejected', reason: 'same_state' },
    pending: { kind: 'allowed', action: 'publish' },
    in_progress: { kind: 'rejected', reason: 'agent_owned' },
    to_be_audited: { kind: 'rejected', reason: 'agent_owned' },
    in_human_review: { kind: 'rejected', reason: 'not_owner_valid' },
    completed: { kind: 'rejected', reason: 'not_owner_valid' },
  },
  pending: {
    draft: { kind: 'allowed', action: 'unpublish' },
    pending: { kind: 'rejected', reason: 'same_state' },
    in_progress: { kind: 'rejected', reason: 'agent_owned' },
    to_be_audited: { kind: 'rejected', reason: 'agent_owned' },
    in_human_review: { kind: 'rejected', reason: 'not_owner_valid' },
    completed: { kind: 'rejected', reason: 'not_owner_valid' },
  },
  in_progress: {
    draft: { kind: 'rejected', reason: 'agent_owned' },
    pending: { kind: 'rejected', reason: 'agent_owned' },
    in_progress: { kind: 'rejected', reason: 'agent_owned' },
    to_be_audited: { kind: 'rejected', reason: 'agent_owned' },
    in_human_review: { kind: 'rejected', reason: 'agent_owned' },
    completed: { kind: 'rejected', reason: 'agent_owned' },
  },
  to_be_audited: {
    draft: { kind: 'rejected', reason: 'agent_owned' },
    pending: { kind: 'rejected', reason: 'agent_owned' },
    in_progress: { kind: 'rejected', reason: 'agent_owned' },
    to_be_audited: { kind: 'rejected', reason: 'agent_owned' },
    in_human_review: { kind: 'rejected', reason: 'agent_owned' },
    completed: { kind: 'rejected', reason: 'agent_owned' },
  },
  in_human_review: {
    draft: { kind: 'rejected', reason: 'not_owner_valid' },
    pending: { kind: 'dialog', dialog: 'request_changes' },
    in_progress: { kind: 'rejected', reason: 'agent_owned' },
    to_be_audited: { kind: 'rejected', reason: 'agent_owned' },
    in_human_review: { kind: 'rejected', reason: 'same_state' },
    completed: { kind: 'dialog', dialog: 'approve_merge' },
  },
  completed: {
    draft: { kind: 'rejected', reason: 'not_owner_valid' },
    pending: { kind: 'rejected', reason: 'not_owner_valid' },
    in_progress: { kind: 'rejected', reason: 'agent_owned' },
    to_be_audited: { kind: 'rejected', reason: 'agent_owned' },
    in_human_review: { kind: 'rejected', reason: 'not_owner_valid' },
    completed: { kind: 'rejected', reason: 'same_state' },
  },
};

const AGENT_OWNED: readonly BoardState[] = ['in_progress', 'to_be_audited'];

function allPairs(): [BoardState, BoardState][] {
  const pairs: [BoardState, BoardState][] = [];
  for (const source of BOARD_STATES) {
    for (const target of BOARD_STATES) {
      pairs.push([source, target]);
    }
  }
  return pairs;
}

describe('allowed-move map (MT-4.4-01)', () => {
  it('resolves every canonical state pair to exactly one defined verdict', () => {
    const pairs = allPairs();
    expect(pairs).toHaveLength(BOARD_STATES.length * BOARD_STATES.length);
    for (const [source, target] of pairs) {
      const pair = `${source} -> ${target}`;
      const verdict = evaluateMove(source, target);
      const expected = MATRIX[source][target];
      expect(verdict, pair).toBeDefined();
      expect(['allowed', 'dialog', 'rejected'], pair).toContain(verdict.kind);
      expect(verdict.kind, pair).toBe(expected.kind);
      if (expected.kind === 'rejected') {
        // Rejection copy is asserted separately as stable exported strings.
        expect(verdict.kind, pair).toBe('rejected');
        if (verdict.kind === 'rejected') {
          expect(verdict.reason, pair).toBe(expected.reason);
          expect(verdict.explanation.trim().length, pair).toBeGreaterThan(0);
        }
      } else {
        expect(verdict, pair).toEqual(expected);
      }
    }
  });

  it('builds the full MOVE_MAP matrix with no undefined cell', () => {
    expect(Object.keys(MOVE_MAP)).toEqual([...BOARD_STATES]);
    for (const source of BOARD_STATES) {
      const row = MOVE_MAP[source];
      expect(Object.keys(row), source).toEqual([...BOARD_STATES]);
      for (const target of BOARD_STATES) {
        expect(row[target], `${source} -> ${target}`).toBeDefined();
      }
    }
  });

  it('allows exactly draft ⇄ pending with publish/unpublish (Section 13.2 bullet 1)', () => {
    expect(evaluateMove('draft', 'pending')).toEqual({ kind: 'allowed', action: 'publish' });
    expect(evaluateMove('pending', 'draft')).toEqual({ kind: 'allowed', action: 'unpublish' });
    const allowedPairs = allPairs().filter(([s, t]) => evaluateMove(s, t).kind === 'allowed');
    expect(allowedPairs).toEqual([
      ['draft', 'pending'],
      ['pending', 'draft'],
    ]);
  });

  it('maps in_human_review → completed to the approve-and-merge confirmation', () => {
    expect(evaluateMove('in_human_review', 'completed')).toEqual({
      kind: 'dialog',
      dialog: 'approve_merge',
    });
  });

  it('maps in_human_review → pending to the request-changes/reassign dialog', () => {
    expect(evaluateMove('in_human_review', 'pending')).toEqual({
      kind: 'dialog',
      dialog: 'request_changes',
    });
  });

  it('treats the dialog pairs as the only dialog verdicts (never plain moves)', () => {
    const dialogPairs = allPairs().filter(([s, t]) => evaluateMove(s, t).kind === 'dialog');
    expect(dialogPairs).toEqual([
      ['in_human_review', 'pending'],
      ['in_human_review', 'completed'],
    ]);
  });

  it('rejects every move into or out of in_progress/to_be_audited naming them agent/system-owned', () => {
    for (const [source, target] of allPairs()) {
      const touchesAgentOwned = AGENT_OWNED.includes(source) || AGENT_OWNED.includes(target);
      const verdict = evaluateMove(source, target);
      if (!touchesAgentOwned) continue;
      const pair = `${source} -> ${target}`;
      expect(verdict.kind, pair).toBe('rejected');
      if (verdict.kind !== 'rejected') continue;
      expect(verdict.reason, pair).toBe('agent_owned');
      expect(verdict.explanation, pair).toBe(REJECTED_AGENT_OWNED_EXPLANATION);
      expect(verdict.explanation, pair).toContain('in_progress');
      expect(verdict.explanation, pair).toContain('to_be_audited');
      expect(verdict.explanation, pair).toContain('agent/system-owned');
    }
  });

  it('never allows a straight drag to completed (Section 8.2 drift guard)', () => {
    for (const source of BOARD_STATES) {
      const verdict = evaluateMove(source, 'completed');
      expect(verdict.kind, source).not.toBe('allowed');
    }
    expect(evaluateMove('draft', 'completed').kind).toBe('rejected');
    expect(evaluateMove('pending', 'completed').kind).toBe('rejected');
  });

  it('keeps every rejection explanation a stable, non-empty operator-facing string', () => {
    const explanations = new Set<string>();
    for (const [source, target] of allPairs()) {
      const verdict = evaluateMove(source, target);
      if (verdict.kind !== 'rejected') continue;
      expect(verdict.explanation.trim().length, `${source} -> ${target}`).toBeGreaterThan(10);
      explanations.add(verdict.explanation);
    }
    expect(explanations).toEqual(
      new Set([
        REJECTED_AGENT_OWNED_EXPLANATION,
        REJECTED_SAME_STATE_EXPLANATION,
        REJECTED_NOT_OWNER_VALID_EXPLANATION,
      ]),
    );
  });

  it('is keyed by canonical snake_case states only — display labels never leak in (ADR-010)', () => {
    for (const [source, target] of allPairs()) {
      const pair = `${source} -> ${target}`;
      const verdict = evaluateMove(source, target);
      expect((BOARD_STATES as readonly string[]).includes(source), pair).toBe(true);
      expect((BOARD_STATES as readonly string[]).includes(target), pair).toBe(true);
      const serialized = JSON.stringify(verdict);
      for (const label of Object.values(STATE_LABELS)) {
        expect(serialized.includes(label), `${pair} must not contain label "${label}"`).toBe(false);
      }
    }
  });

  it('is pure and deterministic — repeated evaluation returns equal verdicts', () => {
    for (const [source, target] of allPairs()) {
      const first = evaluateMove(source, target);
      const second = evaluateMove(source, target);
      expect(second).toEqual(first);
      expect(MOVE_MAP[source][target]).toEqual(first);
    }
  });
});
