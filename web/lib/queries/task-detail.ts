/**
 * Task detail query (MT-4.6-01; Section 13.1 task-detail route; Section
 * 13.3 server state through the query library; NFR-11 — generated client
 * only).
 *
 * One `GET /tasks/{id}` behind its own cache key (`taskDetail`, sibling
 * of the per-task block entries) so the detail row never fights the
 * board list cache, and a targeted single-task refetch from the detail
 * SSE sink (MT-4.6-02's live hook) lands exactly here.
 */
import { useQuery } from '@tanstack/react-query';

import { callApi, retrieveTask } from '@/lib/api';
import type { Task } from '@/lib/api/generated/types.gen';
import { queryKeys } from '@/lib/queries/keys';

/** One task row (`GET /tasks/{id}`, Section 9.2). */
export function fetchTaskDetail(taskId: string): Promise<Task> {
  return callApi(retrieveTask({ path: { id: taskId } }));
}

/**
 * The detail view's task row. `taskId` is the stable entry contract
 * (MT risk note: WP-4.8 review links reuse it); a blank id yields a
 * disabled placeholder so a malformed route never fires a request.
 */
export function useTaskDetailQuery(pid: string, taskId: string) {
  return useQuery({
    queryKey: queryKeys.taskDetail(pid, taskId),
    queryFn: () => fetchTaskDetail(taskId),
    enabled: taskId.trim() !== '',
    staleTime: 30_000,
  });
}
