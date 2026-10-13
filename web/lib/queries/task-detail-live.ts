/**
 * Live task-detail updates (MT-4.6-02 / MT-4.6-04; Section 13.3 "the
 * SSE stream applies event patches to the cache so the board updates
 * without refetching" — the detail view's own single sink).
 *
 * One connection for the whole detail view (the same discipline as the
 * board's `useBoardLiveUpdates` — never a second one per block). Each
 * Section 9.6 envelope is routed to the patchers that own its cache:
 *
 *  - `task.checkpoint`      → the checkpoint feed caches (pure patch,
 *                             MT-4.6-02's acceptance: no refetch);
 *  - `attachment.*`         → the task-attachments lists (WP-4.5's
 *                             `patchAttachmentCaches`, reused verbatim —
 *                             the viewer's per-file statuses move live);
 *  - other events for this  → a deduplicated targeted single-task
 *    task                    refetch (`GET /tasks/{id}`) into the
 *                             `taskDetail` cache — partially-described
 *                             payloads never get guessed at (MT-4.3-05
 *                             risk note).
 *
 * Events for other tasks in the project are ignored (the server can
 * filter per task, but the hook subscribes project-wide once — belt and
 * braces, Section 9.6).
 */
import { useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import type { EventEnvelope, Task } from '@/lib/api/generated/types.gen';
import { patchAttachmentCaches } from '@/lib/queries/attachments';
import { patchCheckpointCaches } from '@/lib/queries/checkpoints';
import { queryKeys } from '@/lib/queries/keys';
import { fetchTaskDetail } from '@/lib/queries/task-detail';
import { useEventStream, type StreamStatus } from '@/lib/stream/use-event-stream';

export function useTaskDetailLiveUpdates(
  pid: string,
  taskId: string,
): { status: StreamStatus; lastEventId: number | null } {
  const queryClient = useQueryClient();
  const inflight = useRef(false);

  const refreshRow = useCallback(async () => {
    try {
      const task = await fetchTaskDetail(taskId);
      queryClient.setQueryData<Task>(queryKeys.taskDetail(pid, taskId), task);
    } catch {
      // A failed row refresh never breaks the stream: the next event or
      // a manual reload recovers (targeted-refetch policy).
    } finally {
      inflight.current = false;
    }
  }, [pid, taskId, queryClient]);

  const onEvent = useCallback(
    (event: EventEnvelope) => {
      if (event.project_id !== pid) {
        return;
      }

      // Pure patches first — they never touch the network.
      patchCheckpointCaches(queryClient, event);
      patchAttachmentCaches(queryClient, event);

      if (event.task_id !== taskId) {
        return; // another task's event — out of this view's scope
      }

      if (event.type === 'task.checkpoint') {
        // The feed already carries the checkpoint; keep the row's
        // stalled-window input (Section 8.6) advancing alongside it.
        queryClient.setQueryData<Task>(queryKeys.taskDetail(pid, taskId), (row) => {
          if (row === undefined) return row;
          const current = row.last_checkpoint_at;
          if (current !== null && current.localeCompare(event.occurred_at) >= 0) {
            return row; // replay or out-of-order — never regress (P7)
          }
          return { ...row, last_checkpoint_at: event.occurred_at };
        });
        return;
      }

      // Everything else describes the row only partially — one
      // deduplicated `GET /tasks/{id}`, never a list refetch.
      if (!inflight.current) {
        inflight.current = true;
        void refreshRow();
      }
    },
    [pid, taskId, queryClient, refreshRow],
  );

  return useEventStream({ project: pid, onEvent });
}
