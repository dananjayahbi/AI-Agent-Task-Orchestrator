'use client';
/**
 * Move destination picker (MT-4.4-02; parent plan Section 13.4 "keyboard
 * navigation for the board and dialogs").
 *
 * The non-drag channel for moves: a per-card dialog listing the six
 * canonical columns, each showing the MT-4.4-01 verdict for this card's
 * current state. Selection calls the same board `route` a drop would, so
 * keyboard and touch users get identical map consultation and callbacks —
 * drag is an enhancement, not the only path. This is *not* the MT-4.4-03
 * confirmation layer (approve-merge / request-changes), which stays
 * deferred; a dialog verdict picked here routes straight to that seam.
 *
 * Radix's Dialog (MT-4.1 UI kit) provides focus trapping, Escape, focus
 * return and the modal semantics — no hand-rolled keyboard handling.
 */
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { Task } from '@/lib/api/generated/types.gen';
import { evaluateMove } from '@/lib/board/move-map';
import { moveOptionHintFor } from '@/lib/board/move-routing';
import { BOARD_STATES, STATE_LABELS, type BoardState } from '@/lib/board/states';
import { cn } from 'cn';

type MoveDestinationDialogProps = {
  task: Task;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Routed through the board controller — identical to the drag path. */
  onPick: (target: BoardState) => void;
};

export function MoveDestinationDialog({
  task,
  open,
  onOpenChange,
  onPick,
}: MoveDestinationDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="move-destination-dialog">
        <DialogHeader>
          <DialogTitle>Move {task.id}</DialogTitle>
          <DialogDescription>
            Choose a destination column. Each option shows whether this move is valid for the
            task&apos;s current state — disallowed moves explain why and leave the card where it is.
          </DialogDescription>
        </DialogHeader>
        <ul aria-label="Move destinations" className="flex flex-col gap-2">
          {BOARD_STATES.map((target) => {
            const verdict = evaluateMove(task.state, target);
            const rejected = verdict.kind === 'rejected';
            return (
              <li key={target}>
                <button
                  type="button"
                  data-testid={`move-option-${target}`}
                  data-verdict={verdict.kind}
                  onClick={() => onPick(target)}
                  className={cn(
                    'w-full rounded-md border border-border px-3 py-2 text-left',
                    'hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring',
                    rejected && 'border-dashed',
                  )}
                >
                  <span className="block text-sm font-medium text-foreground">
                    {STATE_LABELS[target]}
                  </span>
                  <span
                    className={cn(
                      'block text-xs',
                      rejected ? 'text-destructive' : 'text-muted-foreground',
                    )}
                  >
                    {rejected ? verdict.explanation : moveOptionHintFor(verdict)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </DialogContent>
    </Dialog>
  );
}
