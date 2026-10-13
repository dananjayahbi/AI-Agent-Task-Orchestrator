/**
 * Board column (MT-4.3-01; Section 13.2 "columns map 1:1 to canonical
 * states"). The column is presentational: it receives its already-grouped
 * tasks and renders them through the MT-4.3-06 windowed list. Header shows
 * the presentation label and the (full, unwindowed) count — the count is
 * the data-set size, not the mounted-node count.
 *
 * MT-4.4-02 makes each column a drop target: every drag-over consults the
 * MT-4.4-01 map for an affordance (text, not color alone) and every drop
 * routes through the board controller — a rejected drop shows the map's
 * explanation, leaves the card in place, and performs no network call.
 */
import { TaskCard } from '@/components/board/task-card';
import { VirtualList } from '@/components/board/virtual-list';
import { useBoardMove } from '@/components/board/move-context';
import type { Task } from '@/lib/api/generated/types.gen';
import { evaluateMove } from '@/lib/board/move-map';
import { dragHintFor } from '@/lib/board/move-routing';
import { STATE_LABELS, type BoardState } from '@/lib/board/states';
import { cn } from 'cn';

type BoardColumnProps = {
  state: BoardState;
  tasks: readonly Task[];
  /** Latest known checkpoint percent for a task (stream-fed; null = unknown). */
  percentFor: (task: Task) => number | null;
  stalledAfterMinutes: number;
  nowMs: number;
  /** MT-4.5-01: opens the task modal in edit mode. */
  onEdit?: ((task: Task) => void) | undefined;
};

export function BoardColumn({
  state,
  tasks,
  percentFor,
  stalledAfterMinutes,
  nowMs,
  onEdit,
}: BoardColumnProps) {
  const move = useBoardMove();
  const dragging = move?.drag ?? null;
  const hovered = dragging !== null && dragging.over === state;
  const verdict = hovered ? evaluateMove(dragging.task.state, state) : null;

  return (
    <section
      data-testid={`board-column-${state}`}
      data-drop-target={state}
      data-drop-verdict={verdict?.kind}
      aria-label={`${STATE_LABELS[state]} column, ${tasks.length} tasks`}
      className={cn(
        'flex min-w-48 flex-1 snap-start flex-col rounded-lg border border-border bg-muted/30',
        verdict !== null &&
          (verdict.kind === 'rejected'
            ? 'outline-2 outline-dashed outline-destructive/70'
            : 'outline-2 outline-ring'),
      )}
      onDragOver={(event) => {
        if (move === null || move.drag === null) return;
        // Allow the drop for every verdict — the map decides the outcome
        // so a rejected drop can explain itself instead of dead-ending.
        event.preventDefault();
        move.dragOver(state);
      }}
      onDragLeave={(event) => {
        if (move === null || move.drag === null) return;
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          move.dragOver(null);
        }
      }}
      onDrop={(event) => {
        if (move === null || move.drag === null) return;
        event.preventDefault();
        const task = move.drag.task;
        move.endDrag();
        move.route(task, state);
      }}
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
      {verdict !== null && (
        <p
          data-testid={`column-drop-hint-${state}`}
          data-verdict={verdict.kind}
          className={cn(
            'border-b border-border px-3 py-1 text-xs font-medium',
            verdict.kind === 'rejected' ? 'text-destructive' : 'text-foreground',
          )}
        >
          {dragHintFor(verdict)}
        </p>
      )}
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
              onEdit={onEdit}
            />
          )}
        />
      )}
    </section>
  );
}
