/**
 * Optimistic review-move patches (MT-4.4-04; Section 13.2 "Optimistic UI
 * with rollback on `VERSION_CONFLICT` or `TASK_STATE_CONFLICT`").
 *
 * Pure reducers over the cached board list — the caller owns cache writes
 * and rollback (a rollback refetches server truth: refresh beats
 * restore-from-memory, MT-4.4-04 risk note). Rules:
 *
 *  - an optimistic row never bumps `version` — it is intent, not server
 *    truth; the confirming response/event carries the server's new
 *    version and settles the row (Section 7.2/8.2 version discipline);
 *  - `approve` (T15) does not move the card: merge-pending is a
 *    sub-status (Section 8.1), so only `merge_status` flips to `pending`
 *    — the column stays `in_human_review` with an "approved, merging"
 *    badge, never a completed column;
 *  - `request_changes` / `reassign` (T16) preview the return to
 *    `pending` and clear the lease fields (Section 8.3 invariant 1 — no
 *    coder lease outside `in_progress`);
 *  - settlement applies exactly the post-transition identity the review
 *    response carries (`VerdictTaskState`: state, version, review_reason,
 *    merge_status) — the SSE `review.decided` refetch (WP-4.3 cache
 *    patching) then confirms the same row idempotently.
 */
import type { DecisionEnum, Task, VerdictTaskState } from '@/lib/api/generated/types.gen';
import { isBoardState } from '@/lib/board/states';

/** Section 8.3 invariant 1: no lease fields outside `in_progress`. */
function withoutLease(task: Task): Task {
  return {
    ...task,
    worker_agent_id: null,
    worker_session_id: null,
    claimed_role: null,
    lease_acquired_at: null,
    lease_expires_at: null,
  };
}

function patchRow(tasks: Task[], taskId: string, patch: (task: Task) => Task): Task[] {
  const index = tasks.findIndex((task) => task.id === taskId);
  if (index === -1) {
    return tasks;
  }
  const next = [...tasks];
  next[index] = patch(tasks[index]);
  return next;
}

/**
 * The pre-response preview of one confirmed decision — applied when the
 * operator confirms, before the server answers (Section 13.2).
 */
export function optimisticDecisionPatch(
  tasks: Task[],
  taskId: string,
  decision: DecisionEnum,
  note: string,
): Task[] {
  if (decision === 'approve') {
    return patchRow(tasks, taskId, (task) => ({ ...task, merge_status: 'pending' }));
  }
  return patchRow(tasks, taskId, (task) =>
    withoutLease({
      ...task,
      state: 'pending',
      ...(decision === 'request_changes' && note.trim() !== ''
        ? { latest_feedback: note.trim() }
        : {}),
    }),
  );
}

/**
 * Settle from the server's post-transition identity (Section 9.2
 * `ReviewDecisionResponse.task`). Idempotent: applying it twice — HTTP
 * response and SSE-driven refetch racing — writes the same values, so
 * there is no double move or oscillation (MT-4.4-04 acceptance).
 */
export function settleDecisionPatch(
  tasks: Task[],
  taskId: string,
  outcome: Pick<VerdictTaskState, 'state' | 'version' | 'review_reason' | 'merge_status'>,
): Task[] {
  return patchRow(tasks, taskId, (task) => {
    // The response's state is contractually canonical (ADR-010); guard
    // anyway rather than widen Task's state union with an unknown value.
    const state = isBoardState(outcome.state) ? outcome.state : task.state;
    return {
      ...(state === 'in_progress' ? task : withoutLease(task)),
      state,
      version: outcome.version,
      review_reason: outcome.review_reason,
      merge_status: outcome.merge_status,
    };
  });
}
