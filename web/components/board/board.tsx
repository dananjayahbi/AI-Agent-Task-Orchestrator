'use client';

/**
 * Project Kanban board (MT-4.3-01 → MT-4.3-06; Section 13.1 "Kanban for
 * one project (six columns), filters, search, archive toggle").
 *
 * Composition notes:
 *  - layout, data wiring and states are separate concerns (Section 20.3):
 *    this component wires; columns/cards present; loading/empty/error are
 *    distinct early returns with catalog copy (MT-4.1-04);
 *  - the task list comes from the generated client through the query cache
 *    (Section 13.3; NFR-11) with server-side filters in the query key
 *    (MT-4.3-03) and a client-side search predicate over the cached set;
 *  - `useBoardLiveUpdates` (MT-4.3-05) patches that cache from the SSE
 *    stream (MT-4.3-04) so agent transitions move cards without refetch;
 *  - columns render through the MT-4.3-06 windowed list; one shared clock
 *    (`useNow`) drives every lease countdown and stalled marker.
 */
import { useMemo, useState, useCallback } from 'react';

import { BoardColumn } from '@/components/board/board-column';
import { BoardFiltersBar } from '@/components/board/board-filters';
import {
  BoardMoveContext,
  type BoardDragSession,
  type BoardMoveController,
} from '@/components/board/move-context';
import { ReviewMoveDialogs } from '@/components/review/review-move-dialogs';
import { StreamStatusIndicator } from '@/components/board/stream-status';
import { TaskFormModal } from '@/components/task/task-form-modal';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/errors/error-state';
import { EmptyState } from '@/components/states/empty-state';
import { LoadingState } from '@/components/states/loading-state';
import {
  DEFAULT_BOARD_FILTERS,
  isDefaultBoardFilters,
  matchesFilters,
  serverFiltersOf,
  type BoardFilters,
} from '@/lib/board/filters';
import {
  routeMove,
  type MoveDialogHandler,
  type MoveActionHandler,
} from '@/lib/board/move-routing';
import type { MoveDialog } from '@/lib/board/move-map';
import { BOARD_STATES, groupTasksByState } from '@/lib/board/states';
import { DEFAULT_STALLED_AFTER_MINUTES } from '@/lib/board/stalled';
import { useNow } from '@/lib/board/use-now';
import { resolveError } from '@/lib/errors';
import { layout } from '@/lib/layout/styles';
import { useBoardLiveUpdates } from '@/lib/queries/board-live';
import { useCheckpointProgressQuery } from '@/lib/queries/checkpoint-progress';
import { usePolicyQuery } from '@/lib/queries/policy';
import { useBoardTasksQuery } from '@/lib/queries/tasks';
import type { Task } from '@/lib/api/generated/types.gen';

const NO_TASKS: Task[] = [];

function defaultFilters(): BoardFilters {
  // Copy defensively — `states` is mutable state, never shared identity.
  return { ...DEFAULT_BOARD_FILTERS, states: [...DEFAULT_BOARD_FILTERS.states] };
}

type BoardProps = {
  pid: string;
  /**
   * MT-4.4-04 seam (`allowed` verdicts): sends the documented Section 9.2
   * `POST /tasks/{id}/transition`. Deferred with the endpoint — until it
   * lands, allowed drops route to an explicit notice instead (WP-4.4
   * changelog "endpoint gap").
   */
  onMove?: MoveActionHandler;
  /**
   * MT-4.4-03 seam (`dialog` verdicts): opens the approve-and-merge /
   * request-changes layer (Section 9.2 `POST /tasks/{id}/review`).
   * The board renders `ReviewMoveDialogs` itself when no handler is
   * passed (production wiring); tests may intercept the seam.
   */
  onDialog?: MoveDialogHandler;
};

export function Board({ pid, onMove, onDialog }: BoardProps) {
  const [filters, setFilters] = useState<BoardFilters>(defaultFilters);
  const [drag, setDrag] = useState<BoardDragSession | null>(null);
  const [moveNotice, setMoveNotice] = useState<{ message: string; rejected: boolean } | null>(null);
  // MT-4.4-03: the active `dialog` verdict (T15/T16 hand-off). The card
  // never moves on a dialog verdict — the layer decides via the review
  // endpoint (Section 13.2).
  const [reviewDialog, setReviewDialog] = useState<{ task: Task; dialog: MoveDialog } | null>(null);
  // MT-4.5-01 entry points: "New task" (T1 create) and each card's Edit.
  const [taskForm, setTaskForm] = useState<{ open: boolean; task: Task | null }>({
    open: false,
    task: null,
  });
  const serverFilters = useMemo(() => serverFiltersOf(filters), [filters]);

  const tasksQuery = useBoardTasksQuery(pid, serverFilters);
  const policyQuery = usePolicyQuery(pid);
  const progressQuery = useCheckpointProgressQuery(pid);
  const { status } = useBoardLiveUpdates(pid, filters);
  const nowMs = useNow(1000);

  const tasks = tasksQuery.data ?? NO_TASKS;
  const visible = useMemo(
    () => tasks.filter((task) => matchesFilters(task, filters)),
    [tasks, filters],
  );
  const grouped = useMemo(() => groupTasksByState(visible), [visible]);

  // Section 8.6 policy knob; the documented Section 7.2 default (20 min)
  // covers the load window and any policy-fetch failure.
  const stalledAfterMinutes =
    policyQuery.data?.stalled_after_minutes ?? DEFAULT_STALLED_AFTER_MINUTES;
  const progress = progressQuery.data ?? {};
  const percentFor = (task: Task): number | null => progress[task.id]?.percent ?? null;

  // MT-4.4-03 production wiring: without an injected handler the board
  // opens its own review-move dialog layer (never a plain move — the
  // verdicts are decisions served by `POST /tasks/{id}/review`).
  const openReviewDialog = useCallback((task: Task, dialog: MoveDialog) => {
    setReviewDialog({ task, dialog });
  }, []);
  const resolveDialogHandler = onDialog ?? openReviewDialog;

  // MT-4.4-02: one controller serves drag and keyboard/touch — every move
  // interaction consults the MT-4.4-01 map through this single route.
  const moveController = useMemo<BoardMoveController>(
    () => ({
      drag,
      route: (task, target) => {
        routeMove(task, target, {
          onMove,
          onDialog: resolveDialogHandler,
          announce: (message, verdict) =>
            setMoveNotice({ message, rejected: verdict.kind === 'rejected' }),
        });
      },
      beginDrag: (task) => setDrag({ task, over: null }),
      dragOver: (target) =>
        setDrag((current) =>
          current === null || current.over === target ? current : { ...current, over: target },
        ),
      endDrag: () => setDrag(null),
    }),
    [drag, onMove, resolveDialogHandler],
  );

  if (tasksQuery.isPending) {
    return <LoadingState label="Loading board…" />;
  }

  if (tasksQuery.isError) {
    const friendly = resolveError(tasksQuery.error);
    return (
      <ErrorState
        title={friendly.title}
        message={friendly.message}
        requestId={friendly.requestId}
        onRetry={() => void tasksQuery.refetch()}
      />
    );
  }

  const filteredView = visible.length === 0 && !isDefaultBoardFilters(filters);

  return (
    <BoardMoveContext.Provider value={moveController}>
      <div data-testid="board" className={layout.pageStack}>
        <div className={layout.pageHeaderRow}>
          <h1 className="text-lg font-semibold text-foreground">Board — {pid}</h1>
          <div className="flex items-center gap-2">
            <Button
              data-testid="board-new-task"
              onClick={() => setTaskForm({ open: true, task: null })}
            >
              New task
            </Button>
            <StreamStatusIndicator status={status} />
          </div>
        </div>

        {/* Section 13.4: outcomes are announced as text (never color alone). */}
        <div
          role="status"
          aria-live="polite"
          data-testid="board-move-notice"
          className={
            moveNotice === null
              ? 'text-sm text-muted-foreground'
              : moveNotice.rejected
                ? 'text-sm font-medium text-destructive'
                : 'text-sm text-muted-foreground'
          }
        >
          {moveNotice?.message ?? ''}
        </div>

        <BoardFiltersBar filters={filters} onChange={setFilters} />

        {visible.length === 0 ? (
          <EmptyState
            title={
              filteredView ? 'No tasks match the current filters' : 'No tasks in this project yet'
            }
            description={
              filteredView
                ? 'Adjust or clear the filters to see more of the board.'
                : 'Tasks appear here once they are created and published for this project.'
            }
            action={
              filteredView ? (
                <Button
                  data-testid="board-empty-clear-filters"
                  variant="outline"
                  onClick={() => setFilters(defaultFilters())}
                >
                  Clear filters
                </Button>
              ) : undefined
            }
          />
        ) : (
          <div data-testid="board-columns" className={layout.boardColumns}>
            {BOARD_STATES.map((state) => (
              <BoardColumn
                key={state}
                state={state}
                tasks={grouped[state]}
                percentFor={percentFor}
                stalledAfterMinutes={stalledAfterMinutes}
                nowMs={nowMs}
                onEdit={(task) => setTaskForm({ open: true, task })}
              />
            ))}
          </div>
        )}

        <TaskFormModal
          pid={pid}
          task={taskForm.task}
          open={taskForm.open}
          onOpenChange={(open) => setTaskForm((current) => ({ ...current, open }))}
          onSaved={(created) =>
            // Keep the current open state: closing mid-create must not
            // re-open the modal, an open one switches to edit mode.
            setTaskForm((current) => ({ open: current.open, task: created }))
          }
        />

        {/* MT-4.4-03: approve-merge / request-changes-reassign layer —
            only while a `dialog` verdict is pending (Section 13.2). */}
        {reviewDialog !== null && (
          <ReviewMoveDialogs
            task={reviewDialog.task}
            dialog={reviewDialog.dialog}
            pid={pid}
            filters={filters}
            onNotice={setMoveNotice}
            onClose={() => setReviewDialog(null)}
          />
        )}
      </div>
    </BoardMoveContext.Provider>
  );
}
