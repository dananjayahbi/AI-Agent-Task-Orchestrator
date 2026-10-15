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
   * Transition history rows (MT-4.6-03): derived from the task-filtered
   * `GET /events` history (Section 9.2 Events row — the published
   * append-only source; no `GET /tasks/{id}/transitions` endpoint
   * exists). Fetch-on-expand like the sibling blocks.
   */
  taskTransitions: (pid: string, taskId: string) =>
    ['projects', pid, 'tasks', taskId, 'transitions'] as const,
  /**
   * Attachment content pages (MT-4.6-04; Section 9.5): one cache entry
   * per attachment × format × page — never preloaded, fetched when the
   * viewer addresses the page (RISK-13: one page per request).
   */
  attachmentContent: (attachmentId: string, format: string, page: number | null) =>
    ['attachments', attachmentId, 'content', format, page] as const,
  /**
   * Cross-project review queue (MT-4.8-01; Section 13.1): all
   * `in_human_review` tasks across projects — one entry, independent of
   * any single project's board lists; live rows arrive via
   * `review.requested` / transition events patched in (Sections 9.6,
   * 13.3).
   */
  reviewQueue: ['review', 'queue'] as const,
  /** Latest checkpoint percent per task, populated from `task.checkpoint` events (MT-4.3-05). */
  boardCheckpointProgress: (pid: string) =>
    ['projects', pid, 'tasks', 'checkpoint-progress'] as const,
  /**
   * Stored patch body for one resolution (MT-4.7-02; Section 9.2
   * `GET /resolutions/{id}/patch`). Artifacts are immutable (Section
   * 7.2 sha256), so the entry is long-lived; keyed by resolution id —
   * sibling of the task blocks above, independent of the pid.
   */
  resolutionPatch: (resolutionId: string) => ['resolutions', resolutionId, 'patch'] as const,
  /**
   * Agents panel sessions (MT-4.9-01; Section 13.1): task-derived
   * session rows for one project — the Owner-facing read surface (no
   * `GET /agent-sessions` exists; Section 9.2 Sessions row is bridge
   * POST-only). Live rows arrive via `agent.session_*` and task lease
   * events patched in through the WP-4.3 hook.
   */
  agentSessions: (pid: string) => ['projects', pid, 'agent-sessions'] as const,
  /**
   * Audit-log history pages (MT-4.10-01; Section 13.1, Principle P8):
   * one entry per filter set — cursor pages accumulate under it; a
   * filter change is a new key so pagination resets (MT-4.10-02).
   */
  auditEvents: (filters: { project: string | null; task: string | null }) =>
    ['events', 'history', filters] as const,
  /**
   * Operations snapshot (MT-6.4-03; Section 17 Dashboards row): one
   * cross-project entry, polled (never SSE-patched) — see lib/queries/ops.
   */
  opsOverview: ['ops', 'overview'] as const,
};
