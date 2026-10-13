/**
 * Stalled-task derivation (MT-4.3-02; parent plan Section 8.6).
 *
 * The plan defines "stalled" precisely and UI-only: **a task is stalled if
 * no progress checkpoint arrived within `stalled_after_minutes`, even
 * though the lease is still valid.** Nothing else — not queue age, not
 * lease expiry (an expired lease is the sweeper's T5 business, not a
 * stalled marker).
 *
 * When a task has never produced a checkpoint, the window is measured from
 * the claim (`lease_acquired_at`, falling back to `created_at`) — the
 * first checkpoint of an attempt cannot arrive "within" a window that
 * never started.
 */
import type { Task } from '@/lib/api/generated/types.gen';

/** Section 7.2 documented default for `stalled_after_minutes`. */
export const DEFAULT_STALLED_AFTER_MINUTES = 20;

export function isTaskStalled(task: Task, stalledAfterMinutes: number, nowMs: number): boolean {
  // A coder lease exists only in in_progress (Section 8.3 invariant 1) —
  // everywhere else the question does not arise.
  if (task.state !== 'in_progress') {
    return false;
  }
  if (task.lease_expires_at === null) {
    return false;
  }
  if (Date.parse(task.lease_expires_at) <= nowMs) {
    return false; // lease no longer valid — T5 territory, not "stalled"
  }

  const windowMs = stalledAfterMinutes * 60_000;
  const referenceIso = task.last_checkpoint_at ?? task.lease_acquired_at ?? task.created_at;
  const reference = Date.parse(referenceIso);
  if (Number.isNaN(reference)) {
    return false;
  }
  return nowMs - reference >= windowMs;
}
