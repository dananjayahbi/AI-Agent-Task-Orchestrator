/**
 * Event → board-cache reducer (MT-4.3-05; Section 13.3 "the SSE stream
 * applies event patches to the cache so the board updates without
 * refetching"; Section 9.6 envelope; Section 7.2 `version`).
 *
 * Patch-vs-invalidate table (MT-4.3-05 risk note: "document which events
 * are patch vs. invalidate"). The backend's event payloads are deliberately
 * minimal (WP-1.9): transitions carry `{from_state, to_state, reason_code,
 * task_version}` only — never a full row. So:
 *
 *  | event                       | handling                                     |
 *  |-----------------------------|----------------------------------------------|
 *  | task.transitioned           | pure in-place patch: state + version (no     |
 *  |                             | network — the WP-4.3 acceptance case)        |
 *  | task.lease_expired          | pure patch: state + version + lease/worker   |
 *  |                             | cleared (Section 8.3 invariant 1)            |
 *  | task.lease_expiring         | pure patch: lease_expires_at refresh         |
 *  | task.checkpoint             | pure patch: last_checkpoint_at (+ percent    |
 *  |                             | map, handled by applyEventToProgress)        |
 *  | task.claimed / task.released| pure patch of state+version, plus a          |
 *  |                             | **targeted single-task refetch** for the     |
 *  |                             | worker/lease fields the payload omits        |
 *  | task.created / task.updated | **targeted single-task refetch** (payload has |
 *  |                             | no row data / changed field values)          |
 *  | audit.passed, merge.*       | **targeted single-task refetch** (merge       |
 *  |                             | badge fields; payload undefined until WP-3.x) |
 *  | everything else             | ignored (out of board scope)                 |
 *
 * A refetch is always `GET /tasks/{id}` — never a board-list refetch — so
 * live updates stay targeted (Section 13.3) and the no-refetch acceptance
 * (Section 19 WP-4.3) holds for transitions.
 *
 * Version discipline (Section 7.2 optimistic concurrency): a pure patch
 * whose `task_version` is older than the cached one is ignored outright —
 * newer local data never regresses. Patches are idempotent, so a reconnect
 * replay (MT-4.3-04 resume) applies missed events exactly right the second
 * time — no duplicate cards, no gaps.
 *
 * Filter discipline (MT-4.3-03): every patch result is re-evaluated
 * against the active server-side filters — a task that no longer matches
 * disappears; a refetched row that matches is inserted/updated in place.
 */
import type { EventEnvelope, Task } from '@/lib/api/generated/types.gen';
import type { BoardServerFilters } from '@/lib/board/filters';
import { matchesServerFilters } from '@/lib/board/filters';
import { isBoardState } from '@/lib/board/states';
import type { CheckpointProgressMap } from '@/lib/queries/checkpoint-progress';

/** Event types handled as pure patches (no network). */
const PURE_PATCH_EVENTS = new Set([
  'task.transitioned',
  'task.lease_expired',
  'task.lease_expiring',
  'task.checkpoint',
]);

/** Event types that schedule a targeted single-task refetch. */
const REFETCH_EVENTS = new Set([
  'task.created',
  'task.updated',
  'task.claimed',
  'task.released',
  'audit.passed',
  'merge.started',
  'merge.succeeded',
  'merge.failed',
]);

export type BoardEventEffect = {
  /** The (possibly unchanged — same reference) task list. */
  tasks: Task[];
  /** Task rows the event payload cannot fully describe — refetch these. */
  refetchTaskIds: string[];
};

type EventDataFields = {
  task_version?: unknown;
  to_state?: unknown;
  reason_code?: unknown;
  lease_expires_at?: unknown;
  percent?: unknown;
};

function readData(event: EventEnvelope): EventDataFields {
  return typeof event.data === 'object' && event.data !== null
    ? (event.data as EventDataFields)
    : {};
}

function readTaskVersion(data: EventDataFields): number | null {
  return typeof data.task_version === 'number' && Number.isFinite(data.task_version)
    ? data.task_version
    : null;
}

/** Section 7.2: an event older than the cache must never regress it. */
function isStaleAgainst(eventVersion: number | null, cached: Task): boolean {
  return eventVersion !== null && eventVersion < cached.version;
}

function replaceTask(tasks: Task[], index: number, task: Task, matches: boolean): Task[] {
  if (!matches) {
    // No longer belongs under the active server filters — remove it.
    return tasks.filter((candidate) => candidate.id !== task.id);
  }
  const next = [...tasks];
  next[index] = task;
  return next;
}

/**
 * Apply one Section 9.6 event to the cached board task list. Pure: returns
 * the (possibly new) list plus the ids that need a targeted refetch; the
 * caller owns cache writes (this module is render/test-independent).
 */
export function applyEventToBoard(
  tasks: Task[],
  event: EventEnvelope,
  filters: BoardServerFilters,
): BoardEventEffect {
  if (event.task_id === null || event.task_id === undefined) {
    return { tasks, refetchTaskIds: [] };
  }
  const taskId = event.task_id;
  const data = readData(event);
  const eventVersion = readTaskVersion(data);
  const index = tasks.findIndex((task) => task.id === taskId);

  if (PURE_PATCH_EVENTS.has(event.type)) {
    if (index === -1) {
      // Nothing cached to move; creation gaps arrive via task.created.
      return { tasks, refetchTaskIds: [] };
    }
    const cached = tasks[index];
    if (isStaleAgainst(eventVersion, cached)) {
      return { tasks, refetchTaskIds: [] };
    }

    if (event.type === 'task.checkpoint') {
      // Percent lives in the progress map (applyEventToProgress); here only
      // the stalled window input advances (Section 8.6).
      const patched: Task = {
        ...cached,
        last_checkpoint_at:
          cached.last_checkpoint_at !== null &&
          event.occurred_at.localeCompare(cached.last_checkpoint_at) > 0
            ? event.occurred_at
            : (cached.last_checkpoint_at ?? event.occurred_at),
      };
      return { tasks: replaceTask(tasks, index, patched, true), refetchTaskIds: [] };
    }

    if (event.type === 'task.lease_expiring') {
      const expiresAt = typeof data.lease_expires_at === 'string' ? data.lease_expires_at : null;
      const patched: Task = {
        ...cached,
        ...(expiresAt !== null ? { lease_expires_at: expiresAt } : {}),
      };
      return { tasks: replaceTask(tasks, index, patched, true), refetchTaskIds: [] };
    }

    // task.transitioned / task.lease_expired: move columns from to_state.
    const toState = data.to_state;
    if (!isBoardState(toState)) {
      // Malformed payload: prefer a targeted refetch over guessing
      // (MT-4.3-05 risk note).
      return { tasks, refetchTaskIds: [taskId] };
    }
    const leavingLease = event.type === 'task.lease_expired' || toState !== 'in_progress';
    const patched: Task = {
      ...cached,
      state: toState,
      version: eventVersion ?? cached.version,
      ...(leavingLease
        ? {
            // Section 8.3 invariant 1: no coder lease outside in_progress.
            worker_agent_id: null,
            worker_session_id: null,
            claimed_role: null,
            lease_acquired_at: null,
            lease_expires_at: null,
          }
        : {}),
    };
    return {
      tasks: replaceTask(tasks, index, patched, matchesServerFilters(patched, filters)),
      refetchTaskIds: [],
    };
  }

  if (REFETCH_EVENTS.has(event.type)) {
    // Payload carries no row data (or undefined merge semantics) — refresh
    // the one row; the merge step is filter-aware (insert or remove).
    return { tasks, refetchTaskIds: [taskId] };
  }

  // Out of board scope (project.*, attachment.*, audit.* other, review.*,
  // agent.*, system.alert): ignore without breaking the stream
  // (Section 20.4 item 6).
  return { tasks, refetchTaskIds: [] };
}

/**
 * Apply one event to the per-task checkpoint percent map (MT-4.3-02's
 * percent bar source). Idempotent: the same checkpoint re-applied yields
 * the same entry; an older `occurred_at` never overwrites a newer one.
 */
export function applyEventToProgress(
  progress: CheckpointProgressMap,
  event: EventEnvelope,
): CheckpointProgressMap {
  if (event.type !== 'task.checkpoint' || event.task_id === null || event.task_id === undefined) {
    return progress;
  }
  const data = readData(event);
  const percent =
    typeof data.percent === 'number' && Number.isFinite(data.percent) ? data.percent : null;
  const existing = progress[event.task_id];
  if (existing !== undefined && existing.at.localeCompare(event.occurred_at) >= 0) {
    return progress; // replay or out-of-order — keep the newer entry
  }
  return {
    ...progress,
    [event.task_id]: { percent, at: event.occurred_at },
  };
}

/**
 * Merge a freshly refetched task row into the cached list, honoring the
 * active server filters (MT-4.3-03/05: a row that does not match what the
 * server was asked for must not sit in the cache).
 */
export function mergeRefetchedTask(tasks: Task[], task: Task, filters: BoardServerFilters): Task[] {
  const index = tasks.findIndex((candidate) => candidate.id === task.id);
  const matches = matchesServerFilters(task, filters);
  if (index === -1) {
    return matches ? [...tasks, task] : tasks;
  }
  return replaceTask(tasks, index, task, matches);
}
