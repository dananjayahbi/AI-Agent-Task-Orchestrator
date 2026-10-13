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
import { useMemo, useState } from 'react';

import { BoardColumn } from '@/components/board/board-column';
import { BoardFiltersBar } from '@/components/board/board-filters';
import { StreamStatusIndicator } from '@/components/board/stream-status';
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
import { BOARD_STATES, groupTasksByState } from '@/lib/board/states';
import { DEFAULT_STALLED_AFTER_MINUTES } from '@/lib/board/stalled';
import { useNow } from '@/lib/board/use-now';
import { resolveError } from '@/lib/errors';
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

export function Board({ pid }: { pid: string }) {
  const [filters, setFilters] = useState<BoardFilters>(defaultFilters);
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
    <div data-testid="board" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold text-foreground">Board — {pid}</h1>
        <StreamStatusIndicator status={status} />
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
        <div data-testid="board-columns" className="flex snap-x gap-3 overflow-x-auto pb-2">
          {BOARD_STATES.map((state) => (
            <BoardColumn
              key={state}
              state={state}
              tasks={grouped[state]}
              percentFor={percentFor}
              stalledAfterMinutes={stalledAfterMinutes}
              nowMs={nowMs}
            />
          ))}
        </div>
      )}
    </div>
  );
}
