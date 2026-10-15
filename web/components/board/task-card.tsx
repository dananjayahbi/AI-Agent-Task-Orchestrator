'use client';

/**
 * Task card (MT-4.3-02; parent plan Section 13.2 verbatim list): "cards
 * show id, title, priority chip, worker badge with lease countdown,
 * percent bar, attachment count, and a stalled/escalation marker."
 *
 * MT-4.4-02 adds the move affordances: inside a Board the card is
 * draggable (the drop decides via the allowed-move map — this component
 * never evaluates rules itself) and exposes a keyboard/touch "Move"
 * button opening the destination picker. Outside a Board (`move === null`)
 * it renders exactly as before — no draggable, no button.
 *
 * WP-4.6 (MT-4.6-01) makes the title a link into the task detail page
 * (`/projects/{pid}/tasks/{taskId}`) — a real anchor, so keyboard
 * navigation and deep links work (Section 13.4); the detail page links
 * back to the board, and the shared app-layout query cache keeps the
 * board's state across the round trip (Section 13.3).
 *
 * Data discipline (Section 13.3 / MT-4.3-02 out of scope): the card
 * renders exactly what its props carry — the board cache (task row +
 * stream-fed checkpoint percent). No network call ever originates here.
 *
 * Explicit unknowns (risk notes):
 *  - percent: `null` renders an indeterminate bar labelled "Progress
 *    unknown" — a missing report is never drawn as 0 %;
 *  - attachment count: the tasks list contract has no attachment count
 *    (OQ-4.3-01), so the card shows "–" until the field exists in the
 *    contract (or WP-4.6's detail view).
 */
import Link from 'next/link';
import { useState } from 'react';

import { MoveDestinationDialog } from '@/components/board/move-destination-dialog';
import { PriorityChip } from '@/components/board/priority-chip';
import { MergeStatusBadge } from '@/components/review/merge-status-badge';
import { useBoardMove } from '@/components/board/move-context';
import type { Task } from '@/lib/api/generated/types.gen';
import { formatLeaseRemaining, leaseRemainingMs } from '@/lib/board/lease';
import { DEFAULT_STALLED_AFTER_MINUTES, isTaskStalled } from '@/lib/board/stalled';

type TaskCardProps = {
  task: Task;
  /** Latest checkpoint percent 0-100; null/undefined = never reported. */
  percent?: number | null;
  /** Section 8.6 policy knob (`stalled_after_minutes`, default 20). */
  stalledAfterMinutes?: number;
  /** Shared clock reading (useNow) — one ticker drives every card. */
  nowMs: number;
  /** Known attachment count; unknown until the contract exposes it (OQ-4.3-01). */
  attachmentCount?: number | null;
  /** MT-4.5-01 entry point: opens the task modal in edit mode. */
  onEdit?: ((task: Task) => void) | undefined;
};

/**
 * MT-4.8-04: the card shows the shared merge badge for every active
 * sub-status — pending / merging (Section 8.1) plus the T18 failure
 * branch (conflict / failed, back in human review). `merged` stays off
 * the card: the Completed column already states the outcome; the
 * detail page carries the merged marker. (Replaces the old
 * `isMergePending` pending/merging-only check — same Section 8.1
 * "sub-status badge, never a column" rule, wider status set.)
 */
function showMergeBadge(task: Task): boolean {
  return task.merge_status !== 'none' && task.merge_status !== 'merged';
}

export function TaskCard({
  task,
  percent = null,
  stalledAfterMinutes = DEFAULT_STALLED_AFTER_MINUTES,
  nowMs,
  attachmentCount = null,
  onEdit,
}: TaskCardProps) {
  const move = useBoardMove();
  const [moveOpen, setMoveOpen] = useState(false);
  const remainingMs = leaseRemainingMs(task, nowMs);
  const stalled = isTaskStalled(task, stalledAfterMinutes, nowMs);
  const escalated = task.state === 'in_human_review';
  const mergeBadge = showMergeBadge(task);
  const knownPercent = typeof percent === 'number' && Number.isFinite(percent);

  return (
    <article
      data-testid="task-card"
      aria-label={task.id}
      draggable={move !== null}
      onDragStart={
        move === null
          ? undefined
          : (event) => {
              move.beginDrag(task);
              const transfer = event.dataTransfer as DataTransfer | undefined;
              if (transfer !== undefined) {
                // Firefox refuses to start a drag without setData.
                transfer.effectAllowed = 'move';
                transfer.setData('text/plain', task.id);
              }
            }
      }
      onDragEnd={move === null ? undefined : () => move.endDrag()}
      className="flex h-full flex-col gap-1.5 overflow-hidden rounded-lg border border-border bg-card p-2.5 text-card-foreground"
    >
      <div className="flex items-start justify-between gap-2">
        <span data-testid="task-card-id" className="font-mono text-[11px] text-muted-foreground">
          {task.id}
        </span>
        <div className="flex items-center gap-1">
          <PriorityChip priority={task.priority} />
          {onEdit !== undefined && (
            <button
              type="button"
              data-testid="task-card-edit"
              aria-label={`Edit task ${task.id}`}
              title={`Edit ${task.id}`}
              onClick={() => onEdit(task)}
              className="rounded-md border border-border px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
            >
              Edit
            </button>
          )}
          {move !== null && (
            <button
              type="button"
              data-testid="task-card-move"
              aria-label={`Move task ${task.id}`}
              title={`Move ${task.id} to another column`}
              onClick={() => setMoveOpen(true)}
              className="rounded-md border border-border px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
            >
              Move
            </button>
          )}
        </div>
      </div>

      {move !== null && (
        <MoveDestinationDialog
          task={task}
          open={moveOpen}
          onOpenChange={setMoveOpen}
          onPick={(target) => {
            // Same route as a drop — the map decides, never this component.
            move.route(task, target);
            setMoveOpen(false);
          }}
        />
      )}

      <h3 data-testid="task-card-title" className="line-clamp-2 text-sm font-medium">
        <Link
          href={`/projects/${task.project_id}/tasks/${task.id}`}
          className="hover:underline focus-visible:underline"
        >
          {task.title}
        </Link>
      </h3>

      {task.worker_agent_id !== null && remainingMs !== null && (
        <div
          data-testid="task-card-worker"
          className="truncate rounded-md bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground"
          aria-label={`Worker ${task.worker_agent_id}, lease ${formatLeaseRemaining(remainingMs)} remaining`}
        >
          <span className="font-medium">{task.worker_agent_id}</span>
          {' · lease '}
          <span data-testid="task-card-lease">{formatLeaseRemaining(remainingMs)}</span>
        </div>
      )}

      <div className="mt-auto flex flex-col gap-1">
        <div
          data-testid="task-card-progress"
          data-percent={knownPercent ? Math.round(percent) : 'unknown'}
          role="progressbar"
          aria-label={knownPercent ? `Progress ${Math.round(percent)} percent` : 'Progress unknown'}
          aria-valuenow={knownPercent ? Math.round(percent) : undefined}
          aria-valuemin={0}
          aria-valuemax={100}
          className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
        >
          <div
            className={
              knownPercent ? 'h-full rounded-full bg-primary' : 'h-full bg-muted-foreground/30'
            }
            style={{ width: knownPercent ? `${Math.min(100, Math.max(0, percent))}%` : '100%' }}
          />
        </div>
        <div className="flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
          <span data-testid="task-card-progress-label">
            {knownPercent ? `${Math.round(percent)}%` : 'Progress unknown'}
          </span>
          <span
            data-testid="task-card-attachments"
            title="Attachment count is not part of the tasks list contract yet (OQ-4.3-01)"
          >
            {attachmentCount === null ? '–' : attachmentCount} attachments
          </span>
        </div>
      </div>

      {(stalled || escalated || mergeBadge) && (
        <div className="flex flex-wrap gap-1">
          {stalled && (
            <span
              data-testid="task-card-stalled"
              aria-label="Stalled: no progress checkpoint within the policy window"
              className="rounded-full bg-destructive px-2 py-0.5 text-[11px] font-semibold text-destructive-foreground"
            >
              Stalled
            </span>
          )}
          {escalated && (
            <span
              data-testid="task-card-escalation"
              title={task.review_reason ?? 'Escalated for human review'}
              aria-label={`Needs review${task.review_reason ? `: ${task.review_reason}` : ''}`}
              className="rounded-full bg-secondary px-2 py-0.5 text-[11px] font-semibold text-secondary-foreground"
            >
              Needs review
            </span>
          )}
          {mergeBadge && (
            <MergeStatusBadge status={task.merge_status} testId="task-card-merge-badge" />
          )}
        </div>
      )}
    </article>
  );
}
