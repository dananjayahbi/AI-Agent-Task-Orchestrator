/**
 * Transition-history rows (MT-4.6-03; Section 7.2 Task Transition,
 * Principle P8 — history is append-only and read-only here).
 *
 * Data source (recorded against the WP changelog's endpoint-gap OQ):
 * Section 9.2 publishes **no** `GET /tasks/{id}/transitions`, but it does
 * publish `GET /events` (history, filters) and every state-machine
 * dispatch writes both the Transition row and its Section 9.6 event with
 * the same `{from_state, to_state, reason_code, task_version}` payload
 * plus `actor` and the server `occurred_at` (Section 8.2 rule 2). The
 * history block therefore reads the task-filtered event log through the
 * generated client (NFR-11) — a documented contract, never an invented
 * endpoint — and renders only transition-shaped envelopes.
 *
 * Ordering: the endpoint pages oldest → newest (monotonic id), so rows
 * are collected with the shared cursor helper and presented
 * reverse-chronological (newest first). `fetchAllPages` carries the
 * defensive page cap (RISK-13) — bounded even for long tasks.
 */
import { useQuery } from '@tanstack/react-query';

import { apiV1EventsRetrieve, callApi } from '@/lib/api';
import { fetchAllPages } from '@/lib/api/pagination';
import type { EventEnvelope } from '@/lib/api/generated/types.gen';
import { queryKeys } from '@/lib/queries/keys';

const PAGE_SIZE = 100; // contract clamp (pagination.md)

export type TransitionRow = {
  /** Monotonic event id — the ordering key (Section 9.6). */
  id: number;
  /** Server timestamp, verbatim from `occurred_at`. */
  occurredAt: string;
  actorType: string;
  actorRef: string;
  fromState: string;
  toState: string;
  /** Section 8.2 trigger code — displayed verbatim, never rewritten. */
  reasonCode: string;
  taskVersion: number | null;
  eventType: string;
};

type TransitionData = {
  from_state?: unknown;
  to_state?: unknown;
  reason_code?: unknown;
  task_version?: unknown;
};

/**
 * A transition-shaped envelope: the dispatcher's exact data contract
 * (`{from_state, to_state, reason_code}` strings). Checkpoints,
 * `review.requested` payloads and everything else fail the gate and are
 * never rendered as history rows.
 */
export function isTransitionEvent(event: EventEnvelope): boolean {
  const data: unknown = event.data;
  if (typeof data !== 'object' || data === null) {
    return false;
  }
  const fields = data as TransitionData;
  return (
    typeof fields.from_state === 'string' &&
    typeof fields.to_state === 'string' &&
    typeof fields.reason_code === 'string'
  );
}

export function toTransitionRow(event: EventEnvelope): TransitionRow {
  const data = event.data as TransitionData;
  return {
    id: event.id,
    occurredAt: event.occurred_at,
    actorType: event.actor.type,
    actorRef: event.actor.ref,
    fromState: data.from_state as string,
    toState: data.to_state as string,
    reasonCode: data.reason_code as string,
    taskVersion: typeof data.task_version === 'number' ? data.task_version : null,
    eventType: event.type,
  };
}

/** Every transition event for the task, newest first (Section 13.1). */
export async function fetchTaskTransitions(taskId: string): Promise<TransitionRow[]> {
  const events = await fetchAllPages((cursor) =>
    callApi(
      apiV1EventsRetrieve({
        query: { task: taskId, page_size: PAGE_SIZE, ...(cursor !== undefined ? { cursor } : {}) },
      }),
    ),
  );
  return events
    .filter(isTransitionEvent)
    .map(toTransitionRow)
    .sort((a, b) => b.id - a.id);
}

/** Fetch-on-expand history query (Section 13.3/13.4 — RISK-13). */
export function useTaskTransitionHistoryQuery(pid: string, taskId: string, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.taskTransitions(pid, taskId),
    queryFn: () => fetchTaskTransitions(taskId),
    enabled: enabled && taskId.trim() !== '',
    staleTime: 30_000,
  });
}
