/**
 * Review-decision helpers (MT-4.4-03; Section 8.2 T15/T16, Section 9.2
 * `POST /tasks/{id}/review`, Section 11.5 — every decision recorded).
 *
 * Pure, side-effect-free builders shared by the approve-merge and
 * request-changes/reassign dialogs and their tests:
 *
 *  - request bodies bind the `version` the dialog saw (Section 8.2 rule 3:
 *    a stale value answers VERSION_CONFLICT, 409) and, for `approve`, the
 *    `resolution_id` of the resolution the operator was shown
 *    (Section 14.2 approve safety / MT-3.6-04);
 *  - the request-changes note is validated client-side before submit
 *    (T16's guard exists server-side too — this is courtesy, never the
 *    gate);
 *  - success copy states the real resulting state (Section 8.1): approve
 *    is merge-pending ("approved, merging"), never a completed column.
 */
import type { DecisionEnum, ReviewDecisionRequest } from '@/lib/api/generated/types.gen';

export type ReviewDialog = 'approve_merge' | 'request_changes';

/** T16's note rule, enforced client-side before the request is sent. */
export function noteValidationError(note: string): string | null {
  return note.trim() === ''
    ? 'A note is required — it becomes the feedback the next coder sees.'
    : null;
}

/** `approve` (T15): bind the resolution the reviewer actually saw. */
export function approveBody(version: number, resolutionId: string): ReviewDecisionRequest {
  return { decision: 'approve', version, resolution_id: resolutionId };
}

/** `request_changes` (T16): note mandatory; server re-validates (T16 guard). */
export function requestChangesBody(version: number, note: string): ReviewDecisionRequest {
  return { decision: 'request_changes', version, note: note.trim() };
}

/** `reassign` (T16): returns to `pending`, clears the worker. */
export function reassignBody(version: number, note: string): ReviewDecisionRequest {
  const trimmed = note.trim();
  return trimmed === ''
    ? { decision: 'reassign', version }
    : { decision: 'reassign', version, note: trimmed };
}

export function reviewBody(
  decision: DecisionEnum,
  version: number,
  options: { note?: string; resolutionId?: string } = {},
): ReviewDecisionRequest {
  switch (decision) {
    case 'approve':
      return approveBody(version, options.resolutionId ?? '');
    case 'request_changes':
      return requestChangesBody(version, options.note ?? '');
    case 'reassign':
      return reassignBody(version, options.note ?? '');
  }
}

/**
 * Success copy per decision — states the true resulting state
 * (Section 8.1 risk note: presenting approve as "moved to Completed"
 * would lie; the card lands in merge-pending with a badge).
 */
export function decisionSuccessNotice(decision: DecisionEnum, taskId: string): string {
  switch (decision) {
    case 'approve':
      return (
        `${taskId} approved — merge pending. The task stays in Human review with an ` +
        '"approved, merging" badge until the merge completes.'
      );
    case 'request_changes':
      return `${taskId} sent back to Pending — your note is saved as the latest feedback.`;
    case 'reassign':
      return `${taskId} returned to Pending and the worker was cleared.`;
  }
}
