/**
 * Drag-and-drop integration (MT-4.4-02; `npm test -- -t drag-drop`).
 *
 * Proves Section 13.2's rules end-to-end on the rendered board: every
 * drop and every keyboard/touch pick routes through the MT-4.4-01 map
 * exactly once — `allowed` invokes the move seam with the documented
 * contract payload, `dialog` hands off without moving the card, and
 * `rejected` shows the map's explanation, leaves the card in place, and
 * performs **no network call** (WP-4.4 exit criterion: "disallowed moves
 * blocked client-side with explanation"). Also covers hover affordances,
 * keyboard parity through the destination picker, the deferred-seam
 * notices, and virtualization staying intact with DnD wired.
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import type { ComponentProps } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import {
  REJECTED_AGENT_OWNED_EXPLANATION,
  REJECTED_NOT_OWNER_VALID_EXPLANATION,
  REJECTED_SAME_STATE_EXPLANATION,
} from '@/lib/board/move-map';
import {
  dialogHandoffUnavailableNotice,
  moveSendUnavailableNotice,
} from '@/lib/board/move-routing';
import type { BoardState } from '@/lib/board/states';
import type { Task } from '@/lib/api/generated/types.gen';
import { installBoardApi, makeTask, renderWithQueryClient, sseConnection } from '../helpers/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

function mountBoard(tasks: Task[], props: Partial<ComponentProps<typeof Board>> = {}) {
  const { calls } = installBoardApi({ tasks, sse: () => sseConnection().response });
  const view = renderWithQueryClient(<Board pid="PID00001" {...props} />);
  return { calls, ...view };
}

function column(state: BoardState): HTMLElement {
  return screen.getByTestId(`board-column-${state}`);
}

function cardIn(state: BoardState): HTMLElement {
  return within(column(state)).getByTestId('task-card');
}

function noticeText(): string {
  return screen.getByTestId('board-move-notice').textContent ?? '';
}

/** The canonical drag gesture: start on a card, hover a column, drop. */
function dragTo(sourceState: BoardState, targetState: BoardState): void {
  fireEvent.dragStart(cardIn(sourceState));
  fireEvent.dragOver(column(targetState));
  fireEvent.drop(column(targetState));
}

describe('drag-drop integration (MT-4.4-02)', () => {
  it('routes an allowed drop to the move callback with the contract payload — no network call', async () => {
    const onMove = vi.fn();
    const onDialog = vi.fn();
    const { calls } = mountBoard([makeTask({ id: 'PID00001-T001', state: 'draft' })], {
      onMove,
      onDialog,
    });
    await screen.findByTestId('task-card');

    const callsBefore = calls.length;
    const card = screen.getByTestId('task-card');
    expect(card.getAttribute('draggable')).toBe('true');

    fireEvent.dragStart(card);
    fireEvent.dragOver(column('pending'));
    const hint = screen.getByTestId('column-drop-hint-pending');
    expect(hint.getAttribute('data-verdict')).toBe('allowed');
    expect(hint.textContent).toContain('publish');
    expect((hint.textContent ?? '').trim().length).toBeGreaterThan(0); // text, not color alone
    fireEvent.drop(column('pending'));

    expect(onMove).toHaveBeenCalledTimes(1);
    const [task, target, action] = onMove.mock.calls[0];
    expect(task.id).toBe('PID00001-T001');
    expect(task.version).toBe(1); // Section 8.2: the UI sends the version it saw
    expect(target).toBe('pending'); // canonical snake_case target (ADR-010)
    expect(action).toBe('publish');
    expect(onDialog).not.toHaveBeenCalled();
    expect(calls.length).toBe(callsBefore); // drop itself sends nothing (MT-4.4-04 owns calls)
    expect(screen.queryByTestId('column-drop-hint-pending')).toBeNull(); // session cleared
  });

  it('routes dialog verdicts to the dialog seam instead of moving the card', async () => {
    const onMove = vi.fn();
    const onDialog = vi.fn();
    const { calls } = mountBoard([makeTask({ id: 'PID00001-T005', state: 'in_human_review' })], {
      onMove,
      onDialog,
    });
    await screen.findByTestId('task-card');
    const callsBefore = calls.length;

    // in_human_review → completed opens approve-and-merge, never a plain move.
    dragTo('in_human_review', 'completed');
    expect(onDialog).toHaveBeenCalledTimes(1);
    expect(onDialog.mock.calls[0][1]).toBe('approve_merge');
    expect(onMove).not.toHaveBeenCalled();
    // Card never left its column (no cache mutation — Section 13.2).
    expect(within(column('in_human_review')).getByTestId('task-card')).toBeTruthy();
    expect(calls.length).toBe(callsBefore);

    // in_human_review → pending opens request-changes/reassign (T16).
    dragTo('in_human_review', 'pending');
    expect(onDialog).toHaveBeenCalledTimes(2);
    expect(onDialog.mock.calls[1][1]).toBe('request_changes');
    expect(onMove).not.toHaveBeenCalled();
    expect(within(column('in_human_review')).getByTestId('task-card')).toBeTruthy();
    expect(calls.length).toBe(callsBefore);
  });

  it('rejects drops into and out of agent/system-owned states with the explanation — card stays, no call', async () => {
    const onMove = vi.fn();
    const onDialog = vi.fn();
    const { calls } = mountBoard(
      [
        makeTask({ id: 'PID00001-T001', state: 'draft' }),
        makeTask({ id: 'PID00001-T003', state: 'in_progress' }),
      ],
      { onMove, onDialog },
    );
    await screen.findAllByTestId('task-card');
    const callsBefore = calls.length;

    // Into in_progress: hover shows the rejected affordance…
    fireEvent.dragStart(cardIn('draft'));
    fireEvent.dragOver(column('in_progress'));
    const hint = screen.getByTestId('column-drop-hint-in_progress');
    expect(hint.getAttribute('data-verdict')).toBe('rejected');
    expect(hint.textContent).toContain('agent/system-owned');
    fireEvent.drop(column('in_progress'));

    // …the drop shows the map's stable explanation…
    expect(noticeText()).toBe(REJECTED_AGENT_OWNED_EXPLANATION);
    // …the card is still in its own column…
    expect(within(column('draft')).getByTestId('task-card')).toBeTruthy();
    expect(onMove).not.toHaveBeenCalled();
    expect(onDialog).not.toHaveBeenCalled();
    expect(calls.length).toBe(callsBefore);

    // Out of in_progress: same rejection path.
    dragTo('in_progress', 'pending');
    expect(noticeText()).toBe(REJECTED_AGENT_OWNED_EXPLANATION);
    expect(within(column('in_progress')).getByTestId('task-card')).toBeTruthy();
    expect(onMove).not.toHaveBeenCalled();
    expect(calls.length).toBe(callsBefore);
  });

  it('never lets another pair slip through — straight-to-completed and same-column drops are rejected', async () => {
    const onMove = vi.fn();
    const onDialog = vi.fn();
    const { calls } = mountBoard([makeTask({ id: 'PID00001-T002', state: 'pending' })], {
      onMove,
      onDialog,
    });
    await screen.findByTestId('task-card');
    const callsBefore = calls.length;

    dragTo('pending', 'completed');
    expect(noticeText()).toBe(REJECTED_NOT_OWNER_VALID_EXPLANATION);
    expect(within(column('pending')).getByTestId('task-card')).toBeTruthy();
    expect(onMove).not.toHaveBeenCalled();
    expect(onDialog).not.toHaveBeenCalled();

    dragTo('pending', 'pending');
    expect(noticeText()).toBe(REJECTED_SAME_STATE_EXPLANATION);
    expect(calls.length).toBe(callsBefore);
  });

  it('offers keyboard/touch parity through the destination picker — same map, same routes', async () => {
    const onMove = vi.fn();
    const onDialog = vi.fn();
    const { calls } = mountBoard([makeTask({ id: 'PID00001-T001', state: 'draft' })], {
      onMove,
      onDialog,
    });
    await screen.findByTestId('task-card');
    const callsBefore = calls.length;

    // A native button — reachable by keyboard per Section 13.4.
    const moveButton = screen.getByRole('button', { name: 'Move task PID00001-T001' });
    fireEvent.click(moveButton);
    const dialog = await screen.findByTestId('move-destination-dialog');
    expect(dialog).toBeTruthy();

    // Every option carries the map's verdict — no path bypasses it.
    expect(screen.getByTestId('move-option-pending').getAttribute('data-verdict')).toBe('allowed');
    expect(screen.getByTestId('move-option-completed').getAttribute('data-verdict')).toBe(
      'rejected',
    );
    expect(screen.getByTestId('move-option-in_progress').getAttribute('data-verdict')).toBe(
      'rejected',
    );

    // Rejected pick: explains, keeps the card, sends nothing.
    fireEvent.click(screen.getByTestId('move-option-in_progress'));
    await waitFor(() => expect(screen.queryByTestId('move-destination-dialog')).toBeNull());
    expect(noticeText()).toBe(REJECTED_AGENT_OWNED_EXPLANATION);
    expect(within(column('draft')).getByTestId('task-card')).toBeTruthy();
    expect(onMove).not.toHaveBeenCalled();
    expect(calls.length).toBe(callsBefore);

    // Allowed pick: routes exactly like the drag path.
    fireEvent.click(screen.getByRole('button', { name: 'Move task PID00001-T001' }));
    await screen.findByTestId('move-destination-dialog');
    fireEvent.click(screen.getByTestId('move-option-pending'));
    await waitFor(() => expect(screen.queryByTestId('move-destination-dialog')).toBeNull());
    expect(onMove).toHaveBeenCalledTimes(1);
    expect(onMove.mock.calls[0][2]).toBe('publish');
    expect(onDialog).not.toHaveBeenCalled();
    expect(calls.length).toBe(callsBefore);
  });

  it('shows hover affordances only while dragging and clears them on leave or drag end', async () => {
    mountBoard([makeTask({ id: 'PID00001-T001', state: 'draft' })]);
    await screen.findByTestId('task-card');
    const card = screen.getByTestId('task-card');
    expect(screen.queryByTestId('column-drop-hint-pending')).toBeNull();

    fireEvent.dragStart(card);
    fireEvent.dragOver(column('pending'));
    expect(screen.getByTestId('column-drop-hint-pending')).toBeTruthy();

    fireEvent.dragLeave(column('pending'), { relatedTarget: null });
    expect(screen.queryByTestId('column-drop-hint-pending')).toBeNull();

    fireEvent.dragOver(column('pending'));
    expect(screen.getByTestId('column-drop-hint-pending')).toBeTruthy();
    fireEvent.dragEnd(card); // abandoned drag — no drop, no route
    expect(screen.queryByTestId('column-drop-hint-pending')).toBeNull();

    // Session is gone: a stray drag-over after dragEnd routes nothing.
    fireEvent.dragOver(column('pending'));
    expect(screen.queryByTestId('column-drop-hint-pending')).toBeNull();
    expect(noticeText()).toBe('');
  });

  it('announces an explicit seam notice when the deferred consumer is absent — never a silent no-op', async () => {
    // Production page wiring: MT-4.4-03/04 seams are deferred with the
    // endpoints, so no handlers are passed.
    const { calls } = mountBoard([
      makeTask({ id: 'PID00001-T001', state: 'draft' }),
      makeTask({ id: 'PID00001-T005', state: 'in_human_review' }),
    ]);
    await screen.findAllByTestId('task-card');
    const callsBefore = calls.length;

    dragTo('draft', 'pending');
    expect(noticeText()).toBe(moveSendUnavailableNotice('publish', 'draft', 'pending'));
    expect(within(column('draft')).getByTestId('task-card')).toBeTruthy();

    dragTo('in_human_review', 'completed');
    expect(noticeText()).toBe(dialogHandoffUnavailableNotice('approve_merge', 'in_human_review'));
    expect(within(column('in_human_review')).getByTestId('task-card')).toBeTruthy();
    expect(calls.length).toBe(callsBefore);
  });

  it('keeps the virtualized window intact with DnD wired — mounted cards stay bounded', async () => {
    const tasks = Array.from({ length: 40 }, (_, index) =>
      makeTask({ id: `PID00001-T${String(index + 1).padStart(3, '0')}`, state: 'draft' }),
    );
    mountBoard(tasks);
    await waitFor(() =>
      expect(screen.getByTestId(`board-column-count-draft`).textContent).toBe('40'),
    );

    const mounted = document.querySelectorAll('[data-testid="task-card"]');
    expect(mounted.length).toBeGreaterThan(0);
    expect(mounted.length).toBeLessThan(tasks.length); // windowing not defeated
    for (const card of mounted) {
      expect(card.getAttribute('draggable')).toBe('true');
      expect(within(card as HTMLElement).getByTestId('task-card-move')).toBeTruthy();
    }
  });
});
