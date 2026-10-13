/**
 * Query key factory (MT-4.2-01; Section 13.3 server-state caching).
 * One place defines the cache identity so invalidation after mutations
 * (create/edit/revoke) always hits the right entries.
 */
import { normalizeStates, type BoardServerFilters } from '@/lib/board/filters';

export const queryKeys = {
  projects: ['projects'] as const,
  project: (pid: string) => ['projects', pid] as const,
  projectPolicy: (pid: string) => ['projects', pid, 'policy'] as const,
  projectManifest: (pid: string) => ['projects', pid, 'manifest'] as const,
  projectTokens: (pid: string) => ['projects', pid, 'tokens'] as const,
  /**
   * Board task list (MT-4.3-01/03): identity is the project plus the
   * server-side filter set — a filter change refetches, an SSE patch
   * (MT-4.3-05) targets the exact entry the board is rendering. The
   * `'list'` segment namespaces every filter variant under one root so a
   * mutation (MT-4.5-01 save) can invalidate the list without touching
   * the sibling progress map.
   */
  boardTasks: (pid: string, filters: BoardServerFilters) =>
    [
      'projects',
      pid,
      'tasks',
      'list',
      {
        priority: filters.priority,
        states: normalizeStates(filters.states),
        includeArchived: filters.includeArchived,
      },
    ] as const,
  /** Every cached board-list variant for the project (post-save invalidation). */
  boardTasksRoot: (pid: string) => ['projects', pid, 'tasks', 'list'] as const,
  /**
   * Dependencies-picker choices (MT-4.5-04): cursor-paged project task
   * list, loaded lazily — never merged into the board cache (different
   * key space, sibling of `list` under `tasks`).
   */
  taskChoices: (pid: string) => ['projects', pid, 'tasks', 'choices'] as const,
  /**
   * One task's attachment rows (MT-4.5-05): initial load is
   * `GET /tasks/{id}/attachments`; the SSE `attachment.*` events patch
   * this entry live (no polling).
   */
  taskAttachments: (pid: string, taskId: string) =>
    ['projects', pid, 'tasks', taskId, 'attachments'] as const,
  /** Latest checkpoint percent per task, populated from `task.checkpoint` events (MT-4.3-05). */
  boardCheckpointProgress: (pid: string) =>
    ['projects', pid, 'tasks', 'checkpoint-progress'] as const,
};
