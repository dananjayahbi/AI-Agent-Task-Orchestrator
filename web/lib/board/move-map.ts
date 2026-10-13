/**
 * Allowed-move map (MT-4.4-01; FR-WEB-02; parent plan Section 13.2).
 *
 * Pure, side-effect-free client-side source of truth for what a drag (or a
 * keyboard move) may do with a card. Canonical source state → canonical
 * target state → exactly one verdict:
 *
 *  - `allowed`  a plain Owner move (Section 8.2 T2 publish / T3 unpublish);
 *  - `dialog`   must open the confirmation layer instead of moving —
 *               T15 approve-and-merge (`approve_merge`) or T16
 *               request-changes/reassign (`request_changes`);
 *  - `rejected` blocked with a stable, operator-phrased explanation;
 *               the card stays put (never a dead end, never a silent
 *               empty toast).
 *
 * Discipline:
 *  - ADR-010: keys are canonical snake_case states only — the `STATE_LABELS`
 *    display labels never appear in this module;
 *  - the map mirrors Owner-valid moves only (Section 8.2); it must never
 *    gain "convenient" drags the state machine forbids (e.g. a straight
 *    drag to `completed` from anywhere);
 *  - advisory UX only, not authorization: the server re-validates every
 *    transition and answers `TASK_STATE_CONFLICT` (HTTP 409) on an illegal
 *    move (Section 12.1 posture; FR-WEB-02 "server transition validation");
 *  - MT-4.4-02 routes every move interaction through `evaluateMove` —
 *    components never re-derive these rules themselves.
 */
import { BOARD_STATES, type BoardState } from '@/lib/board/states';

/** Plain Owner moves (Section 8.2): which transition an allowed drop sends. */
export type MoveAction = 'publish' | 'unpublish';

/** Dialog-layer hand-offs (Section 13.2; content built by MT-4.4-03). */
export type MoveDialog = 'approve_merge' | 'request_changes';

/** Machine-readable rejection reasons — copy lives in the explanation strings. */
export type MoveReason = 'agent_owned' | 'same_state' | 'not_owner_valid';

export type MoveVerdict =
  | { readonly kind: 'allowed'; readonly action: MoveAction }
  | { readonly kind: 'dialog'; readonly dialog: MoveDialog }
  | {
      readonly kind: 'rejected';
      readonly reason: MoveReason;
      readonly explanation: string;
    };

/**
 * Stable user-facing explanations (tests assert these exact strings, so a
 * silent empty toast can never satisfy "rejected with an explanation").
 */
export const REJECTED_AGENT_OWNED_EXPLANATION =
  'in_progress and to_be_audited are agent/system-owned states — cards cannot be dragged ' +
  'into or out of them. The task stays where it is.';

export const REJECTED_SAME_STATE_EXPLANATION =
  'This task is already in this column — nothing to move.';

export const REJECTED_NOT_OWNER_VALID_EXPLANATION =
  'That move is not Owner-valid for this task: only draft ⇄ pending (publish/unpublish) ' +
  'and the human-review decisions can be dragged. The task stays where it is.';

/** Section 13.2: drops into or out of these states are always rejected. */
const AGENT_OWNED_STATES: ReadonlySet<BoardState> = new Set<BoardState>([
  'in_progress',
  'to_be_audited',
]);

/** The Section 13.2 rules as one pure function — the only rule source. */
function verdictFor(source: BoardState, target: BoardState): MoveVerdict {
  if (AGENT_OWNED_STATES.has(source) || AGENT_OWNED_STATES.has(target)) {
    return {
      kind: 'rejected',
      reason: 'agent_owned',
      explanation: REJECTED_AGENT_OWNED_EXPLANATION,
    };
  }
  if (source === target) {
    return { kind: 'rejected', reason: 'same_state', explanation: REJECTED_SAME_STATE_EXPLANATION };
  }
  if (source === 'draft' && target === 'pending') {
    return { kind: 'allowed', action: 'publish' };
  }
  if (source === 'pending' && target === 'draft') {
    return { kind: 'allowed', action: 'unpublish' };
  }
  if (source === 'in_human_review' && target === 'completed') {
    return { kind: 'dialog', dialog: 'approve_merge' };
  }
  if (source === 'in_human_review' && target === 'pending') {
    return { kind: 'dialog', dialog: 'request_changes' };
  }
  // Nothing is implicitly allowed (Section 13.2): every other pair —
  // including anything aiming straight at `completed` — is rejected.
  return {
    kind: 'rejected',
    reason: 'not_owner_valid',
    explanation: REJECTED_NOT_OWNER_VALID_EXPLANATION,
  };
}

function buildMoveMap(): Record<BoardState, Record<BoardState, MoveVerdict>> {
  const map = {} as Record<BoardState, Record<BoardState, MoveVerdict>>;
  for (const source of BOARD_STATES) {
    const row = {} as Record<BoardState, MoveVerdict>;
    for (const target of BOARD_STATES) {
      row[target] = verdictFor(source, target);
    }
    map[source] = row;
  }
  return map;
}

/**
 * Full source → target → verdict matrix over the six canonical states
 * (every pair resolves to exactly one verdict — nothing falls through).
 */
export const MOVE_MAP: Readonly<Record<BoardState, Readonly<Record<BoardState, MoveVerdict>>>> =
  buildMoveMap();

/**
 * Look up the verdict for moving a card from `source` to `target`.
 * Defensive: an unexpected runtime value resolves to the generic rejection
 * rather than `undefined`.
 */
export function evaluateMove(source: BoardState, target: BoardState): MoveVerdict {
  const verdict = MOVE_MAP[source]?.[target];
  return (
    verdict ?? {
      kind: 'rejected',
      reason: 'not_owner_valid',
      explanation: REJECTED_NOT_OWNER_VALID_EXPLANATION,
    }
  );
}
