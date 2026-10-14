/**
 * Review-queue model (MT-4.8-01; Section 13.1 "All `in_human_review`
 * tasks across projects, sorted by age and priority").
 *
 * Recorded ordering choice (MT risk note — the plan gives two keys
 * without precedence): **age first, as written** — longest-waiting row on
 * top (oldest `updated_at` first); the Section 8.4 priority chip breaks
 * ties in FR-TSK-05 canonical order (urgent → low), then task id for a
 * deterministic total order (NFR-09 spirit).
 *
 * Recorded age basis (MT risk note — "since escalation vs since
 * creation" is not spelled out): while a task sits in `in_human_review`
 * nothing else writes its row, so the escalation transition's bump of
 * `updated_at` **is** the escalation timestamp — age = now −
 * `updated_at`. No transitions endpoint exists to read a dedicated
 * escalation timestamp (Section 9.2 / schema — see the WP changelog).
 */
import type { PriorityEnum, Task } from '@/lib/api/generated/types.gen';

const PRIORITY_RANK: Record<PriorityEnum, number> = {
  urgent: 0,
  high: 1,
  medium: 2,
  low: 3,
};

/** Only tasks the queue shows — defensive, whatever the fetcher sent. */
export function isInHumanReview(task: Task): boolean {
  return task.state === 'in_human_review';
}

/** Age since the escalation (see module doc); `null` on unparseable time. */
export function queueAgeMs(task: Task, nowMs: number): number | null {
  const updated = Date.parse(task.updated_at);
  if (Number.isNaN(updated)) {
    return null;
  }
  return Math.max(0, nowMs - updated);
}

/** Age-first sort (module doc): oldest waiting first, priority, id. */
export function sortQueueRows(tasks: readonly Task[]): Task[] {
  return [...tasks].sort((a, b) => {
    const age = a.updated_at.localeCompare(b.updated_at); // ISO strings sort chronologically
    if (age !== 0) {
      return age;
    }
    const priority = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
    if (priority !== 0) {
      return priority;
    }
    return a.id.localeCompare(b.id);
  });
}

/** Insert or replace a live row (server truth wins on identity). */
export function upsertQueueRow(rows: readonly Task[], row: Task): Task[] {
  const without = rows.filter((task) => task.id !== row.id);
  return isInHumanReview(row) ? [...without, row] : without;
}

/** Drop a row that left `in_human_review` (Section 9.6 removals). */
export function removeQueueRow(rows: readonly Task[], taskId: string): Task[] {
  return rows.filter((task) => task.id !== taskId);
}

/** Compact age copy for the row ("3 d 4 h"); values under a minute read "just now". */
export function formatQueueAge(ms: number): string {
  if (ms < 60_000) {
    return 'just now';
  }
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours} h ${minutes % 60} m`;
  }
  const days = Math.floor(hours / 24);
  return `${days} d ${hours % 24} h`;
}
