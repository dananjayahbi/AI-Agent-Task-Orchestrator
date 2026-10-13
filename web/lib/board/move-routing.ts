/**
 * Move routing (MT-4.4-02; parent plan Section 13.2, FR-WEB-02).
 *
 * One pure funnel for every move interaction — drag-and-drop drops and the
 * keyboard/touch destination picker alike. `routeMove` consults the
 * MT-4.4-01 map (`evaluateMove`) and hands the verdict to exactly one of:
 *
 *  - `onMove`   — `allowed`: the MT-4.4-04 seam. Its eventual consumer
 *                 sends the documented Section 9.2 contract
 *                 `POST /api/v1/tasks/{id}/transition` carrying the
 *                 canonical target state and the `version` the client saw
 *                 (Section 8.2 version discipline). Until that consumer
 *                 exists the route falls back to an explicit notice —
 *                 never a silent no-op and never a cache mutation.
 *  - `onDialog` — `dialog`: the MT-4.4-03 seam, whose consumer opens the
 *                 approve-and-merge / request-changes layer instead of
 *                 moving the card (Section 9.2 `POST /tasks/{id}/review`).
 *  - `announce` — `rejected`: the map's operator-facing explanation; the
 *                 card stays put and **no network call happens**.
 *
 * Nothing here fetches, mutates the query cache, or re-derives rules — the
 * map stays the single source of truth (MT-4.4-01) and the server still
 * re-validates every transition (Section 13.2 posture).
 */
import type { Task } from '@/lib/api/generated/types.gen';
import {
  evaluateMove,
  type MoveAction,
  type MoveDialog,
  type MoveVerdict,
} from '@/lib/board/move-map';
import { STATE_LABELS, type BoardState } from '@/lib/board/states';

/**
 * MT-4.4-04 seam: consumes `allowed` verdicts. The eventual consumer sends
 * `POST /api/v1/tasks/{id}/transition` with `{ to_state: target,
 * version: task.version }` (Section 9.2; Section 8.2 "the UI sends the
 * version it saw").
 */
export type MoveActionHandler = (task: Task, target: BoardState, action: MoveAction) => void;

/**
 * MT-4.4-03 seam: consumes `dialog` verdicts — the approve-and-merge
 * (T15) and request-changes/reassign (T16) confirmations served by
 * `POST /tasks/{id}/review` (Section 9.2).
 */
export type MoveDialogHandler = (task: Task, dialog: MoveDialog) => void;

/** Renders the outcome perceivably (Section 13.4 — text, never color alone). */
export type MoveAnnouncer = (message: string, verdict: MoveVerdict) => void;

export type MoveRouteHandlers = {
  onMove?: MoveActionHandler;
  onDialog?: MoveDialogHandler;
  announce: MoveAnnouncer;
};

/**
 * Fallback notices while the MT-4.4-04 consumer is deferred (the schema
 * has no `POST /tasks/{id}/transition` path yet — see the WP changelog's
 * endpoint-gap note). Stable strings the tests assert.
 */
export function moveSendUnavailableNotice(
  action: MoveAction,
  source: BoardState,
  target: BoardState,
): string {
  return (
    `Validated ${action}: ${STATE_LABELS[source]} → ${STATE_LABELS[target]}. ` +
    'Sending transitions is not available on this board yet, so no move was sent — ' +
    `the task stays in ${STATE_LABELS[source]}.`
  );
}

/** Fallback notice while the MT-4.4-03 dialog layer is deferred. */
export function dialogHandoffUnavailableNotice(dialog: MoveDialog, source: BoardState): string {
  const action =
    dialog === 'approve_merge'
      ? 'Approve-and-merge confirmation'
      : 'Request-changes/reassign confirmation';
  return (
    `${action} is not available on this board yet, so no change was sent — ` +
    `the task stays in ${STATE_LABELS[source]}.`
  );
}

/**
 * Short per-column drag-hover affordance (Section 13.2: "drag hover shows
 * allowed/rejected affordances per the map"). The full explanation lands
 * in the board notice on drop; this hint always carries text, not color
 * alone (Section 13.4).
 */
export function dragHintFor(verdict: MoveVerdict): string {
  if (verdict.kind === 'allowed') {
    return verdict.action === 'publish' ? 'Drop here to publish' : 'Drop here to unpublish';
  }
  if (verdict.kind === 'dialog') {
    return verdict.dialog === 'approve_merge'
      ? 'Drop here to approve and merge (opens confirmation)'
      : 'Drop here to request changes or reassign (opens dialog)';
  }
  return rejectionHint(verdict);
}

/**
 * Verdict line for the keyboard/touch destination picker — same map, same
 * words the drop path would say, phrased for a list option instead of a
 * hover target.
 */
export function moveOptionHintFor(verdict: MoveVerdict): string {
  if (verdict.kind === 'allowed') {
    return verdict.action === 'publish' ? 'Valid move: publish' : 'Valid move: unpublish';
  }
  if (verdict.kind === 'dialog') {
    return verdict.dialog === 'approve_merge'
      ? 'Opens the approve-and-merge confirmation'
      : 'Opens the request-changes/reassign dialog';
  }
  return rejectionHint(verdict);
}

function rejectionHint(verdict: Extract<MoveVerdict, { kind: 'rejected' }>): string {
  if (verdict.reason === 'agent_owned') return 'Not allowed — agent/system-owned states';
  if (verdict.reason === 'same_state') return 'Not allowed — already in this column';
  return 'Not allowed — not an Owner-valid move';
}

/**
 * The single move path (drag or keyboard): consult the MT-4.4-01 map,
 * dispatch exactly one handler for the verdict, and return it. No side
 * effect happens outside the handlers — a rejected drop performs no
 * network call and leaves the card where it is (Section 13.2).
 */
export function routeMove(
  task: Task,
  target: BoardState,
  handlers: MoveRouteHandlers,
): MoveVerdict {
  const verdict = evaluateMove(task.state, target);
  if (verdict.kind === 'allowed') {
    if (handlers.onMove !== undefined) {
      handlers.onMove(task, target, verdict.action);
    } else {
      handlers.announce(moveSendUnavailableNotice(verdict.action, task.state, target), verdict);
    }
  } else if (verdict.kind === 'dialog') {
    if (handlers.onDialog !== undefined) {
      handlers.onDialog(task, verdict.dialog);
    } else {
      handlers.announce(dialogHandoffUnavailableNotice(verdict.dialog, task.state), verdict);
    }
  } else {
    handlers.announce(verdict.explanation, verdict);
  }
  return verdict;
}
