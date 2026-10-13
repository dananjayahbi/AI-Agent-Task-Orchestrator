/**
 * Lease countdown helpers (MT-4.3-02; Section 8.6 lease semantics;
 * Section 13.2 "worker badge with lease countdown").
 *
 * Display-only: the countdown is derived from the server-set
 * `lease_expires_at` against a client clock — it never mutates state and
 * never talks to the network (Section 7.2 fields).
 */
import type { Task } from '@/lib/api/generated/types.gen';

/** Milliseconds until the lease expires; null when the task holds no lease. */
export function leaseRemainingMs(task: Task, nowMs: number): number | null {
  if (task.lease_expires_at === null) {
    return null;
  }
  const expiresAt = Date.parse(task.lease_expires_at);
  if (Number.isNaN(expiresAt)) {
    return null;
  }
  return expiresAt - nowMs;
}

/**
 * Compact remaining-time copy: "45m 00s" below an hour, "2h 05m" above,
 * "expired" once the deadline has passed (the sweeper will re-claim —
 * Section 8.6 "Expire"; the badge must not show negative time).
 */
export function formatLeaseRemaining(remainingMs: number): string {
  if (remainingMs <= 0) {
    return 'expired';
  }
  const totalSeconds = Math.floor(remainingMs / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) {
    return `${hours}h ${String(minutes).padStart(2, '0')}m`;
  }
  return `${minutes}m ${String(seconds).padStart(2, '0')}s`;
}
