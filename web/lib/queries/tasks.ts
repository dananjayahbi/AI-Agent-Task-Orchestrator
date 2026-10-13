/**
 * Board task queries (MT-4.3-01 / MT-4.3-03; Section 13.3 — server state
 * through the query library; NFR-11 — every request through the generated
 * client only).
 *
 * The board loads the project's task set by following the contract's
 * cursor to the last page (`page_size` = the documented clamp, 100). The
 * filter half of the identity lives in the query key (see
 * `queryKeys.boardTasks`), so toggling any server-side filter produces a
 * normal refetch through the cache — the seam SSE patching (MT-4.3-05)
 * writes into.
 */
import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { callApi } from '@/lib/api';
import { listTasks, retrieveTask } from '@/lib/api/generated/sdk.gen';
import type { Task, TaskListEnvelope } from '@/lib/api/generated/types.gen';
import { listTasksQuery, type BoardServerFilters } from '@/lib/board/filters';
import { fetchAllPages } from '@/lib/api/pagination';
import { queryKeys } from '@/lib/queries/keys';

/** One page of `GET /projects/{pid}/tasks` (Section 9.2; cursor contract). */
function fetchTasksPage(
  pid: string,
  filters: BoardServerFilters,
  cursor: string | undefined,
): Promise<TaskListEnvelope> {
  return callApi(
    listTasks({
      path: { pid },
      query: { ...listTasksQuery(filters), cursor },
    }),
  );
}

/** Every task of the project matching the filters, cursor to the end. */
export function fetchBoardTasks(pid: string, filters: BoardServerFilters): Promise<Task[]> {
  return fetchAllPages((cursor) => fetchTasksPage(pid, filters, cursor));
}

/** The board's task list (columns data source). */
export function useBoardTasksQuery(pid: string, filters: BoardServerFilters) {
  return useQuery({
    queryKey: queryKeys.boardTasks(pid, filters),
    queryFn: () => fetchBoardTasks(pid, filters),
    staleTime: 30_000,
    // Filter changes refetch under a new key; keep the previous result on
    // screen so the toolbar never unmounts mid-interaction (Section 20.3
    // states stay separated — only the *first* load shows LoadingState).
    placeholderData: keepPreviousData,
  });
}

/**
 * One task row (`GET /tasks/{id}`) — used by live patching (MT-4.3-05)
 * when an event payload is too partial to patch safely (MT-4.3-05 risk
 * note: prefer a targeted single-task refetch over guessing).
 */
export function fetchTaskRow(taskId: string): Promise<Task> {
  return callApi(retrieveTask({ path: { id: taskId } }));
}
