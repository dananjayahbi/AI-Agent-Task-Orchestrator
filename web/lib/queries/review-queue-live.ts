/**
 * Live review-queue maintenance (MT-4.8-01; Sections 9.6, 13.3 — "the
 * SSE stream applies event patches to the cache so the [queue] updates
 * without refetching").
 *
 * The queue's stream is **cross-project** (Section 9.6 optional
 * filters — the queue itself spans projects; authorization still scopes
 * the feed per connection). Rules, mirroring the board sink's
 * patch-vs-refetch discipline:
 *
 *  - `review.requested` — an entry escalation: fetch the row once
 *    (deduplicated in flight — the payload carries only
 *    `{review_reason, task_version}`, never a row: MT-3.9-01) and insert
 *    it; if the fetch says the task already left `in_human_review`, the
 *    insert drops it instead (server truth);
 *  - transition-shaped events (every dispatch carries
 *    `{from_state, to_state, reason_code}`): `to_state` outside
 *    `in_human_review` **removes** the row (a decision resolved it);
 *    into `in_human_review` inserts a row the queue lacks;
 *  - the initial query covers everything else; a failed row fetch never
 *    breaks the stream — the next event or refetch recovers.
 */
import { useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import type { EventEnvelope, Task } from '@/lib/api/generated/types.gen';
import { queryKeys } from '@/lib/queries/keys';
import { fetchTaskRow } from '@/lib/queries/tasks';
import { isTransitionEvent, toTransitionRow } from '@/lib/queries/transitions';
import { removeQueueRow, upsertQueueRow } from '@/lib/review/queue';
import { useEventStream, type StreamStatus } from '@/lib/stream/use-event-stream';

export function useReviewQueueLiveUpdates(): {
  status: StreamStatus;
  lastEventId: number | null;
} {
  const queryClient = useQueryClient();
  const inflight = useRef<Set<string>>(new Set());

  const refreshRow = useCallback(
    async (taskId: string) => {
      if (inflight.current.has(taskId)) {
        return; // one targeted GET per task while in flight
      }
      inflight.current.add(taskId);
      try {
        const row = await fetchTaskRow(taskId);
        queryClient.setQueryData<Task[]>(queryKeys.reviewQueue, (rows) =>
          rows === undefined ? rows : upsertQueueRow(rows, row),
        );
      } catch {
        // Never breaks the stream: the next event or refetch recovers
        // (targeted-refetch policy, MT-4.3-05).
      } finally {
        inflight.current.delete(taskId);
      }
    },
    [queryClient],
  );

  const onEvent = useCallback(
    (event: EventEnvelope) => {
      if (event.task_id === null || event.task_id === undefined) {
        return;
      }
      const taskId = event.task_id;

      if (event.type === 'review.requested') {
        void refreshRow(taskId);
        return;
      }

      if (isTransitionEvent(event)) {
        const { toState } = toTransitionRow(event);
        const current = queryClient.getQueryData<Task[]>(queryKeys.reviewQueue);
        if (current === undefined) {
          return; // queue not loaded — the initial query carries the truth
        }
        if (toState === 'in_human_review') {
          if (!current.some((task) => task.id === taskId)) {
            void refreshRow(taskId); // entered review elsewhere — add the row
          }
        } else if (current.some((task) => task.id === taskId)) {
          // A decision (or any transition) resolved it — remove the row.
          queryClient.setQueryData<Task[]>(queryKeys.reviewQueue, (rows) =>
            rows === undefined ? rows : removeQueueRow(rows, taskId),
          );
        }
      }
    },
    [queryClient, refreshRow],
  );

  return useEventStream({ onEvent });
}
