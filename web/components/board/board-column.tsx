/**
 * Board column (MT-4.3-01; Section 13.2 "columns map 1:1 to canonical
 * states"). The column is presentational: it receives its already-grouped
 * tasks and renders them through the MT-4.3-06 windowed list. Header shows
 * the presentation label and the (full, unwindowed) count — the count is
 * the data-set size, not the mounted-node count.
 */
import { TaskCard } from '@/components/board/task-card';
import { VirtualList } from '@/components/board/virtual-list';
import type { Task } from '@/lib/api/generated/types.gen';
import { STATE_LABELS, type BoardState } from '@/lib/board/states';

type BoardColumnProps = {
  state: BoardState;
  tasks: readonly Task[];
  /** Latest known checkpoint percent for a task (stream-fed; null = unknown). */
  percentFor: (task: Task) => number | null;
  stalledAfterMinutes: number;
  nowMs: number;
};

export function BoardColumn({
  state,
  tasks,
  percentFor,
  stalledAfterMinutes,
  nowMs,
}: BoardColumnProps) {
  return (
    <section
      data-testid={`board-column-${state}`}
      aria-label={`${STATE_LABELS[state]} column, ${tasks.length} tasks`}
      className="flex min-w-48 flex-1 snap-start flex-col rounded-lg border border-border bg-muted/30"
    >
      <header className="flex items-center justify-between border-b border-border px-3 py-2">
        <h2 className="text-sm font-semibold text-foreground">{STATE_LABELS[state]}</h2>
        <span
          data-testid={`board-column-count-${state}`}
          className="rounded-full bg-muted px-2 text-xs font-medium text-muted-foreground"
        >
          {tasks.length}
        </span>
      </header>
      {tasks.length === 0 ? (
        <p
          data-testid={`board-column-empty-${state}`}
          className="p-3 text-xs text-muted-foreground"
        >
          No tasks
        </p>
      ) : (
        <VirtualList
          items={tasks}
          itemKey={(task) => task.id}
          label={`${STATE_LABELS[state]} tasks`}
          testId={`board-column-list-${state}`}
          className="p-1.5"
          renderItem={(task) => (
            <TaskCard
              task={task}
              percent={percentFor(task)}
              stalledAfterMinutes={stalledAfterMinutes}
              nowMs={nowMs}
            />
          )}
        />
      )}
    </section>
  );
}
