/**
 * Canonical board states (MT-4.3-01; parent plan G-01 / Section 8.1).
 *
 * The six canonical machine values live in the generated API types
 * (`StateEnum`). This module owns only their **board order** (the Section
 * 8.1 diagram order) and their **display labels** — labels are
 * presentation-only and never used for grouping (G-01 discipline).
 *
 * Drift guard: `satisfies readonly StateEnum[]` rejects any value the
 * schema does not know, and the `BoardStatesCoverage` assertion below
 * fails the build when the schema grows a seventh state — a schema change
 * must be a compile error here, never a silent mis-grouping (MT-4.3-01
 * risk note).
 */
import type { StateEnum, Task } from '@/lib/api/generated/types.gen';

/** The six canonical states in Section 8.1 diagram order. */
export const BOARD_STATES = [
  'draft',
  'pending',
  'in_progress',
  'to_be_audited',
  'in_human_review',
  'completed',
] as const satisfies readonly StateEnum[];

export type BoardState = (typeof BOARD_STATES)[number];

/**
 * Compile-time coverage: every `StateEnum` member from the contract must be
 * listed in `BOARD_STATES` (and vice versa via `satisfies`). If this line
 * stops type-checking, the schema and the board disagree — fix before merge.
 */
type BoardStatesCoverage =
  Exclude<StateEnum, BoardState> extends never
    ? BoardState extends StateEnum
      ? true
      : never
    : never;
const _coverage: BoardStatesCoverage = true;
void _coverage;

/** Human labels — presentation only (G-01: machine values drive logic). */
export const STATE_LABELS: Record<BoardState, string> = {
  draft: 'Draft',
  pending: 'Pending',
  in_progress: 'In progress',
  to_be_audited: 'To be audited',
  in_human_review: 'Human review',
  completed: 'Completed',
};

export function isBoardState(value: unknown): value is BoardState {
  return typeof value === 'string' && (BOARD_STATES as readonly string[]).includes(value);
}

/** All six states — the "no state filter" selection. */
export const ALL_BOARD_STATES: readonly BoardState[] = BOARD_STATES;

/**
 * Group tasks into one bucket per canonical state, keyed by the machine
 * value, in Section 8.1 order. A task whose state is not one of the six
 * cannot exist (contract enum); defensively it is dropped rather than
 * rendered under a wrong label.
 */
export function groupTasksByState(tasks: readonly Task[]): Record<BoardState, Task[]> {
  const grouped = Object.fromEntries(BOARD_STATES.map((state) => [state, [] as Task[]])) as Record<
    BoardState,
    Task[]
  >;
  for (const task of tasks) {
    if (isBoardState(task.state)) {
      grouped[task.state].push(task);
    }
  }
  return grouped;
}
