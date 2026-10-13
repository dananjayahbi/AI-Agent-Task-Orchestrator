'use client';

/**
 * Task detail view (MT-4.6-01; Section 13.1 "Task detail (drawer or
 * page): Description, criteria, scope, attachments, checkpoint feed,
 * resolutions, audit reports, transitions history").
 *
 * Form: **page** — the route `/projects/{pid}/tasks/{taskId}` already
 * exists (Section 13.1's conceptual route) and a page keeps the entry
 * contract (task id parameter) trivially stable for WP-4.8's
 * cross-links, gives deep-linkable reloads, and inherits the app
 * layout's shared query cache so board → detail → board navigation
 * never loses cached board state (Section 13.3 cache discipline — the
 * QueryClient lives in the layout, not the page). Recorded in the WP
 * changelog per MT-4.6-01's risk note.
 *
 * Composition (Section 20.3: layout, data wiring and states stay
 * separate):
 *  - the task row loads through the generated client (NFR-11) via
 *    `useTaskDetailQuery` with distinct loading / error states and
 *    catalog-only error copy (Section 20.4 item 5);
 *  - the view owns the detail's single SSE sink
 *    (`useTaskDetailLiveUpdates`) so the checkpoint feed, attachment
 *    statuses and the row itself move live — one connection for the
 *    whole page;
 *  - description, criteria and scope render from the row; attachments,
 *    checkpoint feed, resolutions and transition history are their own
 *    components (MT-4.6-02/03/04), each with their own states;
 *  - `task.version` (Section 7.2 optimistic locking; Section 8.2 rule
 *    3) is surfaced on the root element and available to every child
 *    block through the row they receive;
 *  - `latest_feedback` renders when set (Section 7.2; WP-3.6 will start
 *    populating it — the field is already in the published contract).
 */
import Link from 'next/link';

import { AttachmentViewer } from '@/components/task/detail/attachment-viewer';
import { CheckpointFeed } from '@/components/task/detail/checkpoint-feed';
import {
  ResolutionsSection,
  TransitionsHistorySection,
} from '@/components/task/detail/resolutions-section';
import { PriorityChip } from '@/components/board/priority-chip';
import { ErrorState } from '@/components/errors/error-state';
import { LoadingState } from '@/components/states/loading-state';
import { STATE_LABELS } from '@/lib/board/states';
import { resolveError } from '@/lib/errors';
import { useTaskDetailLiveUpdates } from '@/lib/queries/task-detail-live';
import { useTaskDetailQuery } from '@/lib/queries/task-detail';
import { MarkdownPreview } from '@/components/task/markdown-preview';

type TaskDetailProps = {
  pid: string;
  taskId: string;
};

/** Section 13.1 blocks rendered from the task row itself. */
function TaskFacts({
  description,
  criteria,
  scope,
  testCommand,
}: {
  description: string;
  criteria: readonly string[];
  scope: readonly string[];
  testCommand: string;
}) {
  return (
    <>
      <section
        data-testid="task-detail-section-description"
        aria-label="Description"
        className="grid gap-2"
      >
        <h2 className="text-sm font-semibold text-foreground">Description</h2>
        <MarkdownPreview source={description} />
      </section>

      <section
        data-testid="task-detail-section-criteria"
        aria-label="Acceptance criteria"
        className="grid gap-2"
      >
        <h2 className="text-sm font-semibold text-foreground">Acceptance criteria</h2>
        {criteria.length === 0 ? (
          <p data-testid="task-detail-criteria-empty" className="text-xs text-muted-foreground">
            No acceptance criteria recorded.
          </p>
        ) : (
          <ul data-testid="task-detail-criteria-list" className="list-disc pl-5 text-sm">
            {criteria.map((criterion, index) => (
              <li key={index}>{criterion}</li>
            ))}
          </ul>
        )}
      </section>

      <section
        data-testid="task-detail-section-scope"
        aria-label="Target scope"
        className="grid gap-2"
      >
        <h2 className="text-sm font-semibold text-foreground">Target scope</h2>
        {scope.length === 0 ? (
          <p data-testid="task-detail-scope-empty" className="text-xs text-muted-foreground">
            No target scope recorded.
          </p>
        ) : (
          <ul
            data-testid="task-detail-scope-list"
            className="flex flex-wrap gap-1.5 font-mono text-[11px]"
          >
            {scope.map((glob) => (
              <li key={glob} className="rounded-md border border-border bg-muted/40 px-1.5 py-0.5">
                {glob}
              </li>
            ))}
          </ul>
        )}
        {testCommand !== '' && (
          <p className="text-xs text-muted-foreground">
            Test command:{' '}
            <code data-testid="task-detail-test-command" className="font-mono">
              {testCommand}
            </code>
          </p>
        )}
      </section>
    </>
  );
}

export function TaskDetail({ pid, taskId }: TaskDetailProps) {
  const taskQuery = useTaskDetailQuery(pid, taskId);
  const { status } = useTaskDetailLiveUpdates(pid, taskId);

  // A blank/missing id never fires a request (MT acceptance: missing-id
  // route handling) — render the catalog's not-found copy directly.
  if (taskId.trim() === '') {
    return (
      <ErrorState title="Task not found" message="This task does not exist or has been removed." />
    );
  }

  if (taskQuery.isPending) {
    return <LoadingState label="Loading task…" />;
  }

  if (taskQuery.isError) {
    const friendly = resolveError(taskQuery.error);
    return (
      <ErrorState
        title={friendly.title}
        message={friendly.message}
        requestId={friendly.requestId}
        onRetry={() => void taskQuery.refetch()}
      />
    );
  }

  const task = taskQuery.data;

  return (
    <article
      data-testid="task-detail"
      data-task-id={task.id}
      data-task-version={task.version}
      className="grid gap-6"
    >
      <header className="grid gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={`/projects/${pid}/board`}
            data-testid="task-detail-back"
            className="text-xs text-muted-foreground underline-offset-2 hover:underline"
          >
            ← Back to board
          </Link>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span data-testid="task-detail-id" className="font-mono text-xs text-muted-foreground">
            {task.id}
          </span>
          <PriorityChip priority={task.priority} />
          <span
            data-testid="task-detail-state"
            className="rounded-full bg-secondary px-2 py-0.5 text-[11px] font-semibold text-secondary-foreground"
          >
            {STATE_LABELS[task.state]}
          </span>
          {task.worker_agent_id !== null && (
            <span
              data-testid="task-detail-worker"
              className="text-xs text-muted-foreground"
              aria-label={`Worker ${task.worker_agent_id}`}
            >
              Worker: {task.worker_agent_id}
            </span>
          )}
        </div>
        <h1 data-testid="task-detail-title" className="text-xl font-semibold text-foreground">
          {task.title}
        </h1>
        {task.latest_feedback !== '' && (
          <div
            data-testid="task-detail-feedback"
            className="rounded-md border border-dashed border-border bg-muted/40 p-2.5"
          >
            <span className="text-xs font-semibold text-foreground">Latest review feedback</span>
            <p className="mt-1 text-sm break-words text-muted-foreground">{task.latest_feedback}</p>
          </div>
        )}
      </header>

      <TaskFacts
        description={task.description}
        criteria={task.acceptance_criteria}
        scope={task.target_scope}
        testCommand={task.test_command}
      />

      <section
        data-testid="task-detail-section-attachments"
        aria-label="Attachments"
        className="grid gap-2"
      >
        <h2 className="text-sm font-semibold text-foreground">Attachments</h2>
        <AttachmentViewer pid={pid} taskId={taskId} />
      </section>

      <section
        data-testid="task-detail-section-checkpoints"
        aria-label="Checkpoint feed"
        className="grid gap-2"
      >
        <h2 className="text-sm font-semibold text-foreground">Checkpoint feed</h2>
        <CheckpointFeed pid={pid} taskId={taskId} streamStatus={status} />
      </section>

      <ResolutionsSection pid={pid} taskId={taskId} />
      <TransitionsHistorySection />
    </article>
  );
}
