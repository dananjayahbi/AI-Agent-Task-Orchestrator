/**
 * Agent session rows for the Agents panel (MT-4.9-01; Section 13.1
 * "Live sessions, current leases").
 *
 * Data source (recorded against the WP changelog's endpoint-gap OQ — the
 * MT risk note's first option): Section 9.2 publishes **no** owner-facing
 * `GET /agent-sessions` (the Sessions row is bridge `POST`-only), so the
 * panel derives session rows from two contract sources:
 *
 *  1. **Canonical task rows** — every `in_progress` / `to_be_audited`
 *     task carrying `worker_session_id` *is* a live lease holder
 *     (Section 8.3 invariant 1), so its worker/lease columns are the
 *     authoritative active-session record (`agent_label`, `started_at`
 *     ← `lease_acquired_at`, `last_seen_at` ← `last_checkpoint_at`,
 *     plus the task/lease join).
 *  2. **`GET /events` history** — claim/release/lease-expiry envelopes
 *     reconstruct recently-ended sessions (`ended_at` from the closing
 *     event's `occurred_at`), because the backend never emits
 *     `agent.session_*` today (only the catalog defines them).
 *
 * Live rows arrive over SSE without a refetch (AC: "not a poll"): session
 * envelopes and lease closers patch the cache purely; partially-described
 * claim events schedule the single-task refetch pattern (`GET /tasks/{id}`
 * — the event data carries no worker fields).
 *
 * Recorded readings (changelog): a session's `client_name`, `capability`
 * and `transport` exist only on the server AgentSession row — with no read
 * endpoint they render as "–" rather than being invented. Liveness beyond
 * leases comes from `agent.session_started|ended`; when only lease signals
 * exist, losing the last lease ends the row at that event's timestamp.
 * History is bounded by the shared cursor helper's page cap (RISK-13) and
 * the panel renders at most 50 ended rows, newest first.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useRef } from 'react';

import { apiV1EventsRetrieve, callApi } from '@/lib/api';
import type { EventEnvelope, Task } from '@/lib/api/generated/types.gen';
import { fetchAllPages } from '@/lib/api/pagination';
import { type StallSubject } from '@/lib/board/stalled';
import { queryKeys } from '@/lib/queries/keys';
import { fetchBoardTasks, fetchTaskRow } from '@/lib/queries/tasks';
import { noteServerTime } from '@/lib/server-clock';
import { useEventStream, type StreamStatus } from '@/lib/stream/use-event-stream';

const PAGE_SIZE = 100; // contract clamp (pagination.md)

/** Lease-holding states — the only states Section 8.3 lets hold a worker. */
const LEASE_STATES: ReadonlyArray<Task['state']> = ['in_progress', 'to_be_audited'];

/** One task's lease attached to a session row (MT-4.9-01 "task/lease join"). */
export type AgentSessionTaskJoin = {
  taskId: string;
  taskTitle: string;
  claimedRole: 'coder' | 'auditor';
  taskState: Task['state'];
  leaseAcquiredAt: string | null;
  leaseExpiresAt: string | null;
  lastCheckpointAt: string | null;
  /** Section 7.2 `created_at` — the stall window's last-resort origin. */
  createdAt: string;
  /** Live `task.lease_expiring` seen for this lease (Section 9.6 80% push). */
  leaseExpiring: boolean;
};

/** Section 9.2 AgentSession fields rendered by the panel (camel-cased). */
export type AgentSessionRow = {
  sessionId: string;
  /** `worker_agent_id`; null renders "–" (no read endpoint for sessions). */
  agentLabel: string | null;
  clientName: string | null;
  capability: string | null;
  transport: string | null;
  /** First known signal: earliest lease acquisition / session event. */
  startedAt: string | null;
  /** Latest checkpoint (or claim) observed for the session. */
  lastSeenAt: string | null;
  /** Null = active; set by an explicit session end or lease-derived close. */
  endedAt: string | null;
  /** Current leases (usually one; policy may allow concurrency > 1). */
  joins: AgentSessionTaskJoin[];
  /**
   * True once an `agent.session_started|ended` envelope was observed —
   * then liveness is explicit and only `session_ended` ends the row.
   * Lease-derived rows (no session event) end when their last lease does.
   */
  sessionEventSeen: boolean;
};

function asRecord(data: unknown): Record<string, unknown> {
  return typeof data === 'object' && data !== null ? (data as Record<string, unknown>) : {};
}

function str(value: unknown): string | null {
  return typeof value === 'string' && value !== '' ? value : null;
}

/** ISO-8601 UTC strings compare chronologically as strings. */
function earliest(a: string | null, b: string | null): string | null {
  if (a === null) return b;
  if (b === null) return a;
  return a <= b ? a : b;
}

function latest(...values: Array<string | null>): string | null {
  let out: string | null = null;
  for (const value of values) {
    if (value !== null && (out === null || value > out)) {
      out = value;
    }
  }
  return out;
}

function emptySession(sessionId: string): AgentSessionRow {
  return {
    sessionId,
    agentLabel: null,
    clientName: null,
    capability: null,
    transport: null,
    startedAt: null,
    lastSeenAt: null,
    endedAt: null,
    joins: [],
    sessionEventSeen: false,
  };
}

function replaceAt(
  rows: AgentSessionRow[],
  index: number,
  row: AgentSessionRow,
): AgentSessionRow[] {
  const next = rows.slice();
  if (index < 0) {
    next.push(row);
  } else {
    next[index] = row;
  }
  return next;
}

/** Session id of a session envelope: data first, agent actor.ref fallback. */
function sessionRefOf(event: EventEnvelope): string | null {
  const fromData = str(asRecord(event.data).session_id);
  if (fromData !== null) {
    return fromData;
  }
  return event.actor.type === 'agent' ? str(event.actor.ref) : null;
}

function joinFromTask(task: Task): AgentSessionTaskJoin {
  return {
    taskId: task.id,
    taskTitle: task.title,
    claimedRole: task.claimed_role === 'auditor' ? 'auditor' : 'coder',
    taskState: task.state,
    leaseAcquiredAt: task.lease_acquired_at,
    leaseExpiresAt: task.lease_expires_at,
    lastCheckpointAt: task.last_checkpoint_at,
    createdAt: task.created_at,
    leaseExpiring: false, // a refetched row re-reads server state (flag resets)
  };
}

function sortJoins(joins: AgentSessionTaskJoin[]): AgentSessionTaskJoin[] {
  return [...joins].sort((a, b) =>
    (b.leaseAcquiredAt ?? '').localeCompare(a.leaseAcquiredAt ?? ''),
  );
}

/**
 * The join's Section 7.2 columns in the shape `isTaskStalled` reads
 * (MT-4.9-03): one shared Section 8.6 derivation for board cards and the
 * Agents lease view — `last_checkpoint_at` semantics follow what WP-1.8
 * stores (recorded in the WP changelog).
 */
export function stallSubjectOf(join: AgentSessionTaskJoin): StallSubject {
  return {
    state: join.taskState,
    lease_expires_at: join.leaseExpiresAt,
    last_checkpoint_at: join.lastCheckpointAt,
    lease_acquired_at: join.leaseAcquiredAt,
    created_at: join.createdAt,
  };
}

function isLeaseHolder(task: Task): task is Task & { worker_session_id: string } {
  return (
    LEASE_STATES.includes(task.state) &&
    task.worker_session_id !== null &&
    task.worker_session_id.trim() !== ''
  );
}

/** Active sessions straight from the canonical task rows (source 1). */
export function sessionsFromTasks(tasks: Task[]): AgentSessionRow[] {
  const rows = new Map<string, AgentSessionRow>();
  for (const task of tasks) {
    if (!isLeaseHolder(task)) {
      continue;
    }
    const row = rows.get(task.worker_session_id) ?? emptySession(task.worker_session_id);
    row.agentLabel = task.worker_agent_id ?? row.agentLabel;
    row.startedAt = earliest(row.startedAt, task.lease_acquired_at);
    row.joins.push(joinFromTask(task));
    rows.set(task.worker_session_id, row);
  }
  for (const row of rows.values()) {
    row.joins = sortJoins(row.joins);
    row.lastSeenAt = latest(...row.joins.map((j) => j.lastCheckpointAt ?? j.leaseAcquiredAt));
  }
  return [...rows.values()];
}

/**
 * Recently-ended (and pre-lease) sessions from the append-only history
 * (source 2). Events arrive oldest → newest, so one chronological pass
 * tracks: task → session (from claim actors), open leases per session and
 * each session's last activity. Re-claims revive a row; closers
 * (`task.released`, `task.lease_expired`, and the transitions whose side
 * effects clear leases — submit/verdicts) end a lease-derived row at the
 * event's `occurred_at`.
 */
function scanSessionHistory(events: EventEnvelope[]): {
  rows: Map<string, AgentSessionRow>;
  lastActivity: Map<string, string>;
} {
  const rows = new Map<string, AgentSessionRow>();
  const open = new Map<string, Set<string>>();
  const sessionByTask = new Map<string, string>();
  const lastActivity = new Map<string, string>();

  const ensure = (sessionId: string): AgentSessionRow => {
    let row = rows.get(sessionId);
    if (row === undefined) {
      row = emptySession(sessionId);
      rows.set(sessionId, row);
    }
    return row;
  };
  const openSet = (sessionId: string): Set<string> => {
    let set = open.get(sessionId);
    if (set === undefined) {
      set = new Set();
      open.set(sessionId, set);
    }
    return set;
  };
  const close = (sessionId: string, taskId: string | null, at: string): void => {
    lastActivity.set(sessionId, at);
    const held = openSet(sessionId);
    if (taskId !== null) {
      held.delete(taskId);
    }
    const row = rows.get(sessionId);
    if (row !== undefined && held.size === 0 && !row.sessionEventSeen) {
      row.endedAt = at;
    }
  };

  for (const event of events) {
    const data = asRecord(event.data);
    switch (event.type) {
      case 'agent.session_started': {
        const sessionId = sessionRefOf(event);
        if (sessionId === null) {
          break;
        }
        const row = ensure(sessionId);
        row.sessionEventSeen = true;
        row.endedAt = null;
        row.startedAt = row.startedAt ?? str(data.started_at) ?? event.occurred_at;
        row.agentLabel = str(data.agent_label) ?? row.agentLabel;
        row.clientName = str(data.client_name) ?? row.clientName;
        row.capability = str(data.capability) ?? row.capability;
        row.transport = str(data.transport) ?? row.transport;
        lastActivity.set(sessionId, event.occurred_at);
        break;
      }
      case 'agent.session_ended': {
        const sessionId = sessionRefOf(event);
        if (sessionId === null) {
          break;
        }
        const row = ensure(sessionId);
        row.sessionEventSeen = true;
        row.endedAt = str(data.ended_at) ?? event.occurred_at;
        row.joins = [];
        open.delete(sessionId);
        lastActivity.set(sessionId, event.occurred_at);
        break;
      }
      case 'task.claimed':
      case 'audit.claimed': {
        if (event.task_id === null || event.actor.type !== 'agent') {
          break;
        }
        const sessionId = str(event.actor.ref);
        if (sessionId === null) {
          break;
        }
        const row = ensure(sessionId);
        row.endedAt = null; // a (re)claim revives the session
        row.startedAt = row.startedAt ?? event.occurred_at;
        sessionByTask.set(event.task_id, sessionId);
        openSet(sessionId).add(event.task_id);
        lastActivity.set(sessionId, event.occurred_at);
        break;
      }
      case 'task.released':
      case 'task.lease_expired': {
        if (event.task_id === null) {
          break;
        }
        const byActor =
          event.type === 'task.released' && event.actor.type === 'agent'
            ? str(event.actor.ref)
            : null;
        const sessionId = byActor ?? sessionByTask.get(event.task_id);
        if (sessionId !== undefined && sessionId !== null) {
          close(sessionId, event.task_id, event.occurred_at);
        }
        break;
      }
      case 'task.transitioned':
      case 'audit.passed':
      case 'audit.escalated': {
        // Submit and verdict side effects clear leases without a release
        // event (transitions_submission / audit review) — close the task.
        if (event.task_id === null) {
          break;
        }
        const sessionId = sessionByTask.get(event.task_id);
        if (sessionId !== undefined) {
          close(sessionId, event.task_id, event.occurred_at);
        }
        break;
      }
      default:
        break;
    }
  }
  return { rows, lastActivity };
}

/**
 * Combine both sources: canonical task rows win for live leases (they are
 * the current truth), history contributes ended sessions and earlier
 * start signals. A lease-derived history row with no current lease and no
 * session events is closed at its last observed activity.
 */
export function deriveAgentSessions(tasks: Task[], events: EventEnvelope[]): AgentSessionRow[] {
  const active = sessionsFromTasks(tasks);
  const activeById = new Map(active.map((row) => [row.sessionId, row]));
  const scan = scanSessionHistory(events);
  const merged = new Map<string, AgentSessionRow>();

  for (const row of scan.rows.values()) {
    const current = activeById.get(row.sessionId);
    if (current !== undefined) {
      merged.set(row.sessionId, {
        ...current,
        agentLabel: current.agentLabel ?? row.agentLabel,
        clientName: current.clientName ?? row.clientName,
        capability: current.capability ?? row.capability,
        transport: current.transport ?? row.transport,
        startedAt: earliest(current.startedAt, row.startedAt),
        lastSeenAt: latest(current.lastSeenAt, row.lastSeenAt),
        sessionEventSeen: current.sessionEventSeen || row.sessionEventSeen,
      });
      continue;
    }
    if (row.endedAt === null && !row.sessionEventSeen) {
      merged.set(row.sessionId, {
        ...row,
        endedAt: scan.lastActivity.get(row.sessionId) ?? row.startedAt,
      });
      continue;
    }
    merged.set(row.sessionId, row);
  }
  for (const row of active) {
    if (!merged.has(row.sessionId)) {
      merged.set(row.sessionId, row);
    }
  }

  const keyOf = (row: AgentSessionRow): string =>
    row.endedAt === null ? (row.startedAt ?? '') : (row.endedAt ?? '');
  return [...merged.values()].sort((a, b) => {
    const aEnded = a.endedAt !== null;
    const bEnded = b.endedAt !== null;
    if (aEnded !== bEnded) {
      return aEnded ? 1 : -1; // active first, then ended
    }
    return keyOf(b).localeCompare(keyOf(a)); // newest signal first
  });
}

/**
 * Pure SSE patch for the events the contract fully describes: a session
 * envelope carries its own lifecycle, a release/expiry's envelope id pins
 * the lease removal to `occurred_at`. Claim events are NOT handled here —
 * their data omits the worker/lease columns, so the live hook refetches
 * the task row instead (MT-4.9-01 risk note).
 */
export function applySessionEvent(
  rows: AgentSessionRow[],
  event: EventEnvelope,
): AgentSessionRow[] {
  const data = asRecord(event.data);
  switch (event.type) {
    case 'agent.session_started': {
      const sessionId = sessionRefOf(event);
      if (sessionId === null) {
        return rows;
      }
      const index = rows.findIndex((row) => row.sessionId === sessionId);
      const row = index < 0 ? emptySession(sessionId) : { ...rows[index] };
      row.sessionEventSeen = true;
      row.endedAt = null;
      row.startedAt = row.startedAt ?? str(data.started_at) ?? event.occurred_at;
      row.agentLabel = str(data.agent_label) ?? row.agentLabel;
      row.clientName = str(data.client_name) ?? row.clientName;
      row.capability = str(data.capability) ?? row.capability;
      row.transport = str(data.transport) ?? row.transport;
      return replaceAt(rows, index, row);
    }
    case 'agent.session_ended': {
      const sessionId = sessionRefOf(event);
      if (sessionId === null) {
        return rows;
      }
      const index = rows.findIndex((row) => row.sessionId === sessionId);
      const row = index < 0 ? emptySession(sessionId) : { ...rows[index] };
      row.sessionEventSeen = true;
      row.endedAt = str(data.ended_at) ?? event.occurred_at;
      row.joins = [];
      return replaceAt(rows, index, row);
    }
    case 'task.released':
    case 'task.lease_expired': {
      if (event.task_id === null) {
        return rows;
      }
      const index = rows.findIndex((row) =>
        row.joins.some((join) => join.taskId === event.task_id),
      );
      if (index < 0) {
        return rows;
      }
      const row = { ...rows[index] };
      row.joins = row.joins.filter((join) => join.taskId !== event.task_id);
      if (row.joins.length === 0 && !row.sessionEventSeen) {
        row.endedAt = event.occurred_at; // lease-derived liveness: last lease gone
      }
      return replaceAt(rows, index, row);
    }
    default:
      return rows;
  }
}

/**
 * Pure patch for `task.lease_expiring` (Section 9.6, sent at 80% of the
 * lease): re-arms the join's deadline from the envelope's own
 * `lease_expires_at` (server-issued — P7) and flags the 80% warning. The
 * flag clears on the next targeted refetch (claim/checkpoint), when the
 * computed elapsed/total threshold takes over again.
 */
export function applyLeaseExpiring(
  rows: AgentSessionRow[],
  event: EventEnvelope,
): AgentSessionRow[] {
  if (event.task_id === null) {
    return rows;
  }
  const index = rows.findIndex((row) => row.joins.some((join) => join.taskId === event.task_id));
  if (index < 0) {
    return rows;
  }
  const expires = str(asRecord(event.data).lease_expires_at);
  const row = { ...rows[index] };
  row.joins = row.joins.map((join) =>
    join.taskId === event.task_id
      ? {
          ...join,
          leaseExpiring: true,
          leaseExpiresAt: expires ?? join.leaseExpiresAt,
        }
      : join,
  );
  return replaceAt(rows, index, row);
}

/**
 * Fold a refetched task row (the targeted-refetch seam) into the session
 * list: a holder gains/refreshes its join and revives; a cleared lease
 * detaches and, for lease-derived rows, ends at the task's server
 * `updated_at`.
 */
export function applyTaskRow(rows: AgentSessionRow[], task: Task): AgentSessionRow[] {
  let next = rows.map((row) => {
    if (
      !row.joins.some((join) => join.taskId === task.id) ||
      row.sessionId === task.worker_session_id
    ) {
      return row;
    }
    const joins = row.joins.filter((join) => join.taskId !== task.id);
    const updated = { ...row, joins };
    if (joins.length === 0 && !row.sessionEventSeen && updated.endedAt === null) {
      updated.endedAt = task.updated_at;
    }
    return updated;
  });

  if (isLeaseHolder(task)) {
    const index = next.findIndex((row) => row.sessionId === task.worker_session_id);
    const row = index < 0 ? emptySession(task.worker_session_id) : { ...next[index] };
    row.agentLabel = task.worker_agent_id ?? row.agentLabel;
    row.endedAt = null;
    row.startedAt = earliest(row.startedAt, task.lease_acquired_at);
    row.joins = sortJoins([
      ...row.joins.filter((join) => join.taskId !== task.id),
      joinFromTask(task),
    ]);
    row.lastSeenAt = latest(
      row.lastSeenAt,
      ...row.joins.map((join) => join.lastCheckpointAt ?? join.leaseAcquiredAt),
    );
    next = replaceAt(next, index, row);
  }
  return next;
}

/** Both contract sources in parallel: lease tasks + project event history. */
export async function fetchAgentSessions(pid: string): Promise<AgentSessionRow[]> {
  const [tasks, events] = await Promise.all([
    fetchBoardTasks(pid, {
      priority: null,
      states: ['in_progress', 'to_be_audited'],
      includeArchived: false,
    }),
    fetchAllPages((cursor) =>
      callApi(
        apiV1EventsRetrieve({
          query: {
            project: pid,
            page_size: PAGE_SIZE,
            ...(cursor !== undefined ? { cursor } : {}),
          },
        }),
      ),
    ),
  ]);
  return deriveAgentSessions(tasks, events);
}

/** Section 13.3 server-state seam for one project's session rows. */
export function useAgentSessionsQuery(pid: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.agentSessions(pid),
    queryFn: () => fetchAgentSessions(pid),
    enabled: enabled && pid.trim() !== '',
    staleTime: 30_000,
  });
}

/**
 * Stream seam for the panel (AC: row updates arrive over the stream, not
 * a poll). Pure patches apply in cache; claim/transition events schedule
 * the single-task refetch pattern, deduplicated while in flight.
 */
export function useAgentSessionsLive(pid: string): {
  status: StreamStatus;
  lastEventId: number | null;
} {
  const queryClient = useQueryClient();
  const inflight = useRef<Set<string>>(new Set());

  const refreshTaskRow = useCallback(
    async (taskId: string, forPid: string) => {
      try {
        const task = await fetchTaskRow(taskId);
        const key = queryKeys.agentSessions(forPid);
        queryClient.setQueryData<AgentSessionRow[]>(key, (rows) =>
          rows === undefined ? rows : applyTaskRow(rows, task),
        );
      } catch {
        // A failed single-row refresh never breaks the stream: the next
        // event or a manual refetch recovers (targeted-refetch policy).
      } finally {
        inflight.current.delete(taskId);
      }
    },
    [queryClient],
  );

  const onEvent = useCallback(
    (event: EventEnvelope) => {
      if (event.project_id !== pid) {
        return; // the server already filters; belt and braces (Section 9.6)
      }
      // P7 anchor: every envelope re-aligns the display clock (MT-4.9-02).
      noteServerTime(event.occurred_at);
      const key = queryKeys.agentSessions(pid);
      const current = queryClient.getQueryData<AgentSessionRow[]>(key);
      if (current === undefined) {
        return; // entry not loaded — the initial fetch already saw this state
      }

      if (event.type === 'task.lease_expiring') {
        queryClient.setQueryData<AgentSessionRow[]>(key, (rows) =>
          rows === undefined ? rows : applyLeaseExpiring(rows, event),
        );
        return;
      }

      // Section 9.9 detector intake (MT-4.9-03): the alert refreshes the
      // flagged task from the server (covering stream misses) — display
      // stays client-computed per Section 8.6 (UI-only), and no
      // alert-shaped state is invented for a payload the detector does
      // not publish yet.
      if (event.type === 'system.alert') {
        const alertTaskId = event.task_id ?? str(asRecord(event.data).task_id);
        if (alertTaskId !== null && !inflight.current.has(alertTaskId)) {
          inflight.current.add(alertTaskId);
          void refreshTaskRow(alertTaskId, pid);
        }
        return;
      }

      if (
        event.type === 'agent.session_started' ||
        event.type === 'agent.session_ended' ||
        event.type === 'task.released' ||
        event.type === 'task.lease_expired'
      ) {
        queryClient.setQueryData<AgentSessionRow[]>(key, (rows) =>
          rows === undefined ? rows : applySessionEvent(rows, event),
        );
        return;
      }

      // A checkpoint moves lease_expires_at but its data omits it (Section
      // 9.6) — the MT-4.9-02 extension path: one targeted task refetch.
      const joined =
        event.task_id !== null &&
        current.some((row) => row.joins.some((join) => join.taskId === event.task_id));
      const needsRefetch =
        event.type === 'task.claimed' ||
        event.type === 'audit.claimed' ||
        ((event.type === 'task.checkpoint' ||
          event.type === 'task.transitioned' ||
          event.type === 'audit.passed' ||
          event.type === 'audit.escalated') &&
          joined);
      if (needsRefetch && event.task_id !== null && !inflight.current.has(event.task_id)) {
        inflight.current.add(event.task_id);
        void refreshTaskRow(event.task_id, pid);
      }
    },
    [pid, queryClient, refreshTaskRow],
  );

  return useEventStream({ project: pid, onEvent });
}
