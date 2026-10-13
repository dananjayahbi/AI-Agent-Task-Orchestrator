/**
 * Live board updates (MT-4.3-05; Section 13.3 "the SSE stream applies
 * event patches to the cache so the board updates without refetching").
 *
 * Subscribes the MT-4.3-04 hook to the project's stream and turns each
 * Section 9.6 envelope into targeted cache writes:
 *
 *  - pure patches (transition/lease/checkpoint) go through the reducer in
 *    `lib/board/patch.ts` — zero network, the WP-4.3 acceptance case;
 *  - partially-described events schedule a **single-task** refetch
 *    (`GET /tasks/{id}`), deduplicated while in flight — never a
 *    board-list refetch;
 *  - the checkpoint percent map is maintained alongside the task list so
 *    MT-4.3-02's percent bar updates live.
 *
 * The active filters are read through a ref at delivery time, so a patch
 * arriving mid-filter-change lands on exactly the cache entry the board is
 * currently rendering (MT-4.3-03 composition rule).
 */
import { useCallback, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import type { EventEnvelope, Task } from '@/lib/api/generated/types.gen';
import { serverFiltersOf, type BoardFilters } from '@/lib/board/filters';
import { applyEventToBoard, applyEventToProgress, mergeRefetchedTask } from '@/lib/board/patch';
import type { CheckpointProgressMap } from '@/lib/queries/checkpoint-progress';
import { queryKeys } from '@/lib/queries/keys';
import { fetchTaskRow } from '@/lib/queries/tasks';
import { useEventStream, type StreamStatus } from '@/lib/stream/use-event-stream';

export function useBoardLiveUpdates(
  pid: string,
  filters: BoardFilters,
): { status: StreamStatus; lastEventId: number | null } {
  const queryClient = useQueryClient();
  const latest = useRef({ pid, filters });
  useEffect(() => {
    latest.current = { pid, filters };
  }, [pid, filters]);
  const inflight = useRef<Set<string>>(new Set());

  const refreshTaskRow = useCallback(
    async (taskId: string, forPid: string) => {
      try {
        const task = await fetchTaskRow(taskId);
        // Filters read at completion time — the newest cache entry wins.
        const server = serverFiltersOf(latest.current.filters);
        const key = queryKeys.boardTasks(forPid, server);
        queryClient.setQueryData<Task[]>(key, (tasks) =>
          tasks === undefined ? tasks : mergeRefetchedTask(tasks, task, server),
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
      const { pid: currentPid, filters: currentFilters } = latest.current;
      if (event.project_id !== currentPid) {
        return; // the server already filters; belt and braces (Section 9.6)
      }
      const server = serverFiltersOf(currentFilters);

      // Percent map first — maintained even before the task list loads.
      queryClient.setQueryData<CheckpointProgressMap>(
        queryKeys.boardCheckpointProgress(currentPid),
        (previous) => applyEventToProgress(previous ?? {}, event),
      );

      const key = queryKeys.boardTasks(currentPid, server);
      const current = queryClient.getQueryData<Task[]>(key);
      if (current === undefined) {
        return; // board entry not loaded — nothing to patch
      }
      const effect = applyEventToBoard(current, event, server);
      if (effect.tasks !== current) {
        queryClient.setQueryData<Task[]>(key, effect.tasks);
      }
      for (const taskId of effect.refetchTaskIds) {
        if (inflight.current.has(taskId)) {
          continue;
        }
        inflight.current.add(taskId);
        void refreshTaskRow(taskId, event.project_id);
      }
    },
    [queryClient, refreshTaskRow],
  );

  return useEventStream({ project: pid, onEvent });
}
