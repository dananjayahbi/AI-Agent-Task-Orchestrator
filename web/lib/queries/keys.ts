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
   * (MT-4.3-05) targets the exact entry the board is rendering.
   */
  boardTasks: (pid: string, filters: BoardServerFilters) =>
    [
      'projects',
      pid,
      'tasks',
      {
        priority: filters.priority,
        states: normalizeStates(filters.states),
        includeArchived: filters.includeArchived,
      },
    ] as const,
  /** Latest checkpoint percent per task, populated from `task.checkpoint` events (MT-4.3-05). */
  boardCheckpointProgress: (pid: string) =>
    ['projects', pid, 'tasks', 'checkpoint-progress'] as const,
};
