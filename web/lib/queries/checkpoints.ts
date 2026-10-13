/**
 * Checkpoint feed queries (MT-4.6-02; Section 9.2 `GET
 * /tasks/{id}/checkpoints`; Section 13.2 "reverse-chronological live
 * list"; Section 13.3 cache discipline).
 *
 * Cache shape is one envelope per task: `{ rows, nextCursor }`. Rows are
 * kept in the server's own order — `(-timestamp, -id)` (MT-1.8-04's
 * keyset sort) — so the initial page, cursor-paged older pages and
 * live-arrived rows all sort through one comparator instead of trusting
 * arrival order. Live rows arrive as `task.checkpoint` Section 9.6
 * events patched in by `patchCheckpointCaches` (no refetch-per-event);
 * replayed events after a reconnect dedupe on the checkpoint id
 * (Section 9.6 no-gaps/no-duplicates contract).
 */
import { useQuery, type QueryClient } from '@tanstack/react-query';

import { callApi, listCheckpoints } from '@/lib/api';
import type { Checkpoint, EventEnvelope } from '@/lib/api/generated/types.gen';
import { queryKeys } from '@/lib/queries/keys';

/** One feed page plus the cursor for older entries (Section 9.2). */
export type CheckpointFeedCache = {
  rows: Checkpoint[];
  nextCursor: string | null;
};

/** The Section 9.2 default page — pagination gates the initial load (RISK-13). */
const PAGE_SIZE = 25;

/** Server sort mirrored: newest first, UUID tiebreak (MT-1.8-04). */
export function compareCheckpointsNewestFirst(a: Checkpoint, b: Checkpoint): number {
  const byTime = b.timestamp.localeCompare(a.timestamp);
  if (byTime !== 0) return byTime;
  return b.id.localeCompare(a.id);
}

function fetchCheckpointsPage(taskId: string, cursor: string | undefined) {
  return callApi(
    listCheckpoints({
      path: { id: taskId },
      query: { page_size: PAGE_SIZE, ...(cursor === undefined ? {} : { cursor }) },
    }),
  );
}

/** First page of the feed (newest 25; older entries load on demand). */
async function fetchCheckpointFeed(taskId: string): Promise<CheckpointFeedCache> {
  const page = await fetchCheckpointsPage(taskId, undefined);
  return {
    rows: [...page.results].sort(compareCheckpointsNewestFirst),
    nextCursor: page.next_cursor,
  };
}

export function useTaskCheckpointsQuery(pid: string, taskId: string) {
  return useQuery({
    queryKey: queryKeys.taskCheckpoints(pid, taskId),
    queryFn: () => fetchCheckpointFeed(taskId),
    enabled: taskId.trim() !== '',
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

/**
 * Append the next (older) cursor page. The feed entry is the writer —
 * this never refetches the first page, so live rows already patched in
 * are preserved (Section 13.4: bounded initial load).
 */
export async function loadOlderCheckpoints(
  client: QueryClient,
  pid: string,
  taskId: string,
): Promise<void> {
  const key = queryKeys.taskCheckpoints(pid, taskId);
  const cached = client.getQueryData<CheckpointFeedCache>(key);
  if (cached === undefined || cached.nextCursor === null) return;
  const page = await fetchCheckpointsPage(taskId, cached.nextCursor);
  client.setQueryData<CheckpointFeedCache>(key, (current) => {
    if (current === undefined) return current;
    const known = new Set(current.rows.map((row) => row.id));
    const added = page.results.filter((row) => !known.has(row.id));
    return {
      rows: [...current.rows, ...added].sort(compareCheckpointsNewestFirst),
      nextCursor: page.next_cursor,
    };
  });
}

type CheckpointEventData = {
  checkpoint_id?: unknown;
  attempt_number?: unknown;
  kind?: unknown;
  percent?: unknown;
  session_id?: unknown;
  message?: unknown;
  token_usage?: unknown;
};

/**
 * Pure reducer: one `task.checkpoint` envelope → the feed cache. The
 * event carries the stored row's fields (WP-1.8's in-transaction
 * emission, MT-1.8-03) with the envelope's `occurred_at` as the server
 * timestamp, so no refetch is needed. Replays dedupe on checkpoint id;
 * unknown/malformed events leave the cache untouched (the next history
 * load reconciles).
 */
export function applyCheckpointEvent(
  cache: CheckpointFeedCache,
  event: EventEnvelope,
): CheckpointFeedCache {
  if (event.type !== 'task.checkpoint' || event.task_id === null || event.task_id === undefined) {
    return cache;
  }
  const data = (
    typeof event.data === 'object' && event.data !== null ? event.data : {}
  ) as CheckpointEventData;
  if (typeof data.checkpoint_id !== 'string' || data.checkpoint_id === '') {
    return cache;
  }
  if (cache.rows.some((row) => row.id === data.checkpoint_id)) {
    return cache; // reconnect replay — no duplicate rows (Section 9.6)
  }
  const row: Checkpoint = {
    id: data.checkpoint_id,
    task_id: event.task_id,
    attempt_number: typeof data.attempt_number === 'number' ? data.attempt_number : 0,
    session_id: typeof data.session_id === 'string' ? data.session_id : '',
    timestamp: event.occurred_at,
    message: typeof data.message === 'string' ? data.message : '',
    percent:
      typeof data.percent === 'number' && Number.isFinite(data.percent) ? data.percent : null,
    token_usage: data.token_usage ?? null,
    kind: typeof data.kind === 'string' ? data.kind : 'progress',
  };
  return {
    rows: [...cache.rows, row].sort(compareCheckpointsNewestFirst),
    nextCursor: cache.nextCursor,
  };
}

/**
 * Patch every cached feed this event belongs to (the detail view's
 * single SSE sink calls this — never a second connection, never a
 * refetch-per-event). Key shape:
 * `['projects', pid, 'tasks', taskId, 'checkpoints']`.
 */
export function patchCheckpointCaches(client: QueryClient, event: EventEnvelope): void {
  if (event.type !== 'task.checkpoint') return;
  client.setQueriesData<CheckpointFeedCache>(
    {
      predicate: (query) => {
        const key = query.queryKey;
        return (
          key.length === 5 &&
          key[0] === 'projects' &&
          key[1] === event.project_id &&
          key[2] === 'tasks' &&
          key[3] === event.task_id &&
          key[4] === 'checkpoints'
        );
      },
    },
    (cache) => (cache === undefined ? cache : applyCheckpointEvent(cache, event)),
  );
}
