/**
 * Cross-project review queue (MT-4.8-01; Section 13.1 — "All
 * `in_human_review` tasks across projects, sorted by age and priority").
 *
 * Data-source wiring (MT risk note — Section 9.2 has no cross-project
 * task query, and N-project fan-out violates the responsiveness target):
 *
 *  1. one `GET /dashboard/summary` call tells us which projects have
 *     `state_counts.in_human_review > 0` — the documented prefilter;
 *  2. only those projects get a `GET /projects/{pid}/tasks
 *     ?state=in_human_review` fan-out (cursor to the end, page_size 100
 *     clamp) — projects with zero review rows cost no task request, and
 *     the fan-out is bounded by the prefilter instead of N;
 *  3. rows are sorted age-first per `lib/review/queue.ts` (recorded
 *     choice).
 *
 * A review task created between the summary read and the task lists is
 * picked up by the live `review.requested` subscription
 * (`review-queue-live.ts`) or the next refetch — never missed silently.
 */
import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { callApi, listTasks, retrieveDashboardSummary } from '@/lib/api';
import { fetchAllPages } from '@/lib/api/pagination';
import type { Task } from '@/lib/api/generated/types.gen';
import { sortQueueRows } from '@/lib/review/queue';
import { queryKeys } from '@/lib/queries/keys';

/** One project's `in_human_review` rows, cursor to the end (Section 9.2). */
function fetchProjectReviewTasks(pid: string): Promise<Task[]> {
  return fetchAllPages((cursor) =>
    callApi(
      listTasks({
        path: { pid },
        query: {
          state: ['in_human_review'],
          page_size: 100, // contract clamp (pagination.md)
          ...(cursor !== undefined ? { cursor } : {}),
        },
      }),
    ),
  );
}

export async function fetchReviewQueue(): Promise<Task[]> {
  const summary = await callApi(retrieveDashboardSummary({}));
  const withReview = summary.projects
    .filter((card) => card.state_counts.in_human_review > 0)
    .map((card) => card.project_id);
  const batches = await Promise.all(withReview.map(fetchProjectReviewTasks));
  return sortQueueRows(batches.flat());
}

/** The queue rows (Section 13.3 — server state through the query cache). */
export function useReviewQueueQuery() {
  return useQuery({
    queryKey: queryKeys.reviewQueue,
    queryFn: fetchReviewQueue,
    staleTime: 30_000,
    // Live patches write this entry; keep it on screen across refetches.
    placeholderData: keepPreviousData,
  });
}
