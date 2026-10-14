'use client';

/**
 * Cross-project review queue (MT-4.8-01; Section 13.1 — route reserved
 * for "All `in_human_review` tasks across projects, sorted by age and
 * priority").
 *
 * One list for every project: rows carry project, task id, title, the
 * priority chip, the canonical Section 8.4 review reason (friendly label
 * **and** verbatim code — Section 20.5), age since escalation (recorded
 * basis in `lib/review/queue.ts`) and an entry action into the task
 * detail (WP-4.6 contract; the richer review panel lands with
 * MT-4.8-02). Sorting is age-first with the canonical priority order as
 * tiebreak — recomputed on render so live inserts land in order.
 *
 * Live maintenance (Sections 9.6, 13.3): `review.requested` adds rows,
 * transitions out of `in_human_review` remove them — through the
 * WP-4.3-pattern stream hook (`review-queue-live.ts`), whose status is
 * visible here (graceful offline: rows stay readable, Section 13.3).
 * Loading / empty / error states are distinct (Section 20.3) with
 * catalog-only copy (Section 20.4 item 5).
 */
import Link from 'next/link';

import { PriorityChip } from '@/components/board/priority-chip';
import { StreamStatusIndicator } from '@/components/board/stream-status';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/errors/error-state';
import { EmptyState } from '@/components/states/empty-state';
import { LoadingState } from '@/components/states/loading-state';
import { useNow } from '@/lib/board/use-now';
import { resolveError } from '@/lib/errors';
import { useReviewQueueQuery } from '@/lib/queries/review-queue';
import { useReviewQueueLiveUpdates } from '@/lib/queries/review-queue-live';
import { formatQueueAge, queueAgeMs, sortQueueRows } from '@/lib/review/queue';
import { reviewReasonLabel } from '@/lib/review/review-reasons';
import type { Task } from '@/lib/api/generated/types.gen';

function ReviewQueueRow({ task, nowMs }: { task: Task; nowMs: number }) {
  const age = queueAgeMs(task, nowMs);
  const detailHref = `/projects/${task.project_id}/tasks/${task.id}`;
  return (
    <li
      data-testid="review-queue-row"
      data-task-id={task.id}
      className="grid gap-2 rounded-md border border-border bg-card p-3 text-card-foreground"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex flex-wrap items-center gap-2">
          <span
            data-testid="review-queue-project"
            className="rounded-full bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground"
          >
            {task.project_id}
          </span>
          <span className="font-mono text-[11px] text-muted-foreground">{task.id}</span>
          <PriorityChip priority={task.priority} />
        </span>
        <span data-testid="review-queue-age" className="text-[11px] text-muted-foreground">
          {age === null ? 'Age unknown' : `waiting ${formatQueueAge(age)}`}
        </span>
      </div>
      <Link
        href={detailHref}
        data-testid={`review-queue-open-${task.id}`}
        className="text-sm font-semibold text-foreground hover:underline"
      >
        {task.title}
      </Link>
      <p data-testid="review-queue-reason" className="text-xs text-muted-foreground">
        {reviewReasonLabel(task.review_reason)}
        {task.review_reason !== null && <span className="font-mono"> ({task.review_reason})</span>}
      </p>
      <div>
        <Button asChild size="sm" variant="outline">
          <Link href={detailHref}>Open task</Link>
        </Button>
      </div>
    </li>
  );
}

export function ReviewQueue() {
  const queueQuery = useReviewQueueQuery();
  const { status } = useReviewQueueLiveUpdates();
  const nowMs = useNow(30_000);

  return (
    <div data-testid="review-queue" className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold text-foreground">Review queue</h1>
        <StreamStatusIndicator status={status} />
      </div>

      {queueQuery.isPending ? (
        <LoadingState label="Loading tasks awaiting review…" />
      ) : queueQuery.isError ? (
        <ErrorState
          title={resolveError(queueQuery.error).title}
          message={resolveError(queueQuery.error).message}
          requestId={resolveError(queueQuery.error).requestId}
          onRetry={() => void queueQuery.refetch()}
        />
      ) : queueQuery.data.length === 0 ? (
        <EmptyState
          title="Nothing to review"
          description="Tasks appear here as soon as any project escalates one for human review."
        />
      ) : (
        <ul className="grid gap-3" data-testid="review-queue-list">
          {sortQueueRows(queueQuery.data).map((task) => (
            <ReviewQueueRow key={task.id} task={task} nowMs={nowMs} />
          ))}
        </ul>
      )}
    </div>
  );
}
