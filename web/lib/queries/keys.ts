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
  /**
   * Task detail row (MT-4.6-01; Section 13.1 task-detail route): one
   * `GET /tasks/{id}` result. Sibling of the per-task blocks below so a
   * single-task refetch (targeted-refetch policy) never collides with
   * the board list or the block caches.
   */
  taskDetail: (pid: string, taskId: string) =>
    ['projects', pid, 'tasks', taskId, 'detail'] as const,
  /**
   * Checkpoint feed history (MT-4.6-02): initial load is
   * `GET /tasks/{id}/checkpoints` (cursor-gated older pages); live rows
   * arrive via `task.checkpoint` events patched into this entry.
   */
  taskCheckpoints: (pid: string, taskId: string) =>
    ['projects', pid, 'tasks', taskId, 'checkpoints'] as const,
  /**
   * Resolutions list (MT-4.6-03 partial): fetch-on-expand per Section
   * 13.3/13.4 — the entry is created only when the section first opens.
   */
  taskResolutions: (pid: string, taskId: string) =>
    ['projects', pid, 'tasks', taskId, 'resolutions'] as const,
  /**
   * Audit-report rows for a task (MT-4.6-03 partial): fetched alongside
   * the resolutions (WP-1.8) so each resolution's audit trail can be
   * linked. Also fetch-on-expand.
   */
  taskAuditReports: (pid: string, taskId: string) =>
    ['projects', pid, 'tasks', taskId, 'audit-reports'] as const,
  /**
   * Attachment content pages (MT-4.6-04; Section 9.5): one cache entry
   * per attachment × format × page — never preloaded, fetched when the
   * viewer addresses the page (RISK-13: one page per request).
   */
  attachmentContent: (attachmentId: string, format: string, page: number | null) =>
    ['attachments', attachmentId, 'content', format, page] as const,
  /** Latest checkpoint percent per task, populated from `task.checkpoint` events (MT-4.3-05). */
  boardCheckpointProgress: (pid: string) =>
    ['projects', pid, 'tasks', 'checkpoint-progress'] as const,
};
