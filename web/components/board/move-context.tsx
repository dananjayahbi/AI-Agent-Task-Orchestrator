'use client';
/**
 * Board move controller (MT-4.4-02; parent plan Section 13.2).
 *
 * The Board owns the drag session, the move notice, and the MT-4.4-03/04
 * seams; columns and cards consume this context so that **every** move
 * interaction — drop, keyboard/touch picker — routes through the single
 * `route` (which consults the MT-4.4-01 map). Components rendered outside
 * a Board (standalone card previews, unit tests) get `null` and simply
 * expose no move affordances — no dangling drag state, no phantom calls.
 */
import { createContext, useContext } from 'react';

import type { Task } from '@/lib/api/generated/types.gen';
import type { BoardState } from '@/lib/board/states';

/** A drag in flight: the card being dragged and the column hovered (if any). */
export type BoardDragSession = {
  task: Task;
  over: BoardState | null;
};

export type BoardMoveController = {
  /** Consult the allowed-move map and dispatch the verdict — the only move path. */
  route: (task: Task, target: BoardState) => void;
  /** Current drag session; `null` when nothing is being dragged. */
  drag: BoardDragSession | null;
  beginDrag: (task: Task) => void;
  /** Target column under the pointer, or `null` when the pointer left. */
  dragOver: (target: BoardState | null) => void;
  endDrag: () => void;
};

export const BoardMoveContext = createContext<BoardMoveController | null>(null);

export function useBoardMove(): BoardMoveController | null {
  return useContext(BoardMoveContext);
}
