/**
 * MT-4.3-06 — column virtualization for 500-card boards (Section 13.4:
 * responsive board, keyboard navigation reach; Section 19 WP-4.3 final
 * slice). "Responsive" is made objective per the MT risk note: mounted
 * card nodes stay bounded far below the data-set size, scrolling windows
 * the list, and live patches keep scroll position.
 */
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import { CARD_ROW_HEIGHT } from '@/components/board/virtual-list';
import { BOARD_STATES } from '@/lib/board/states';
import {
  installApi,
  jsonResponse,
  makeEventEnvelope,
  makePolicy,
  makeTask,
  renderWithQueryClient,
  sseConnection,
  tasksServerRoute,
  type SseConnection,
} from '../helpers/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

/** Synthetic Section 13.4 board: 500 tasks cycling through the six states. */
function makeBoardFixture() {
  return Array.from({ length: 500 }, (_, index) =>
    makeTask({
      id: `PID00001-T${String(index + 1).padStart(3, '0')}`,
      title: `Task ${index + 1}`,
      state: BOARD_STATES[index % BOARD_STATES.length],
    }),
  );
}

function setupLargeBoard() {
  const streams: SseConnection[] = [];
  const { calls } = installApi([
    tasksServerRoute('PID00001', makeBoardFixture()),
    {
      method: 'GET',
      match: /\/api\/v1\/projects\/PID00001\/policy(\?|$)/,
      respond: () => jsonResponse(makePolicy()),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/events\/stream(\?|$)/,
      respond: () => {
        const connection = sseConnection();
        streams.push(connection);
        return connection.response;
      },
    },
  ]);
  renderWithQueryClient(<Board pid="PID00001" />);
  return { calls, streams };
}

const mountedCards = () => document.querySelectorAll('[data-testid="task-card"]').length;

describe('Board virtualization (MT-4.3-06)', () => {
  it('mounts a bounded window of the 500 cards while reporting full column counts', async () => {
    setupLargeBoard();
    await waitFor(() => expect(screen.getByTestId('board-column-count-draft')).toBeTruthy());

    // Full data set…
    expect(screen.getByTestId('board-column-count-draft').textContent).toBe('84');
    expect(screen.getByTestId('board-column-count-in_progress').textContent).toBe('83');
    // …but a bounded DOM: six columns × (fallback viewport window + overscan).
    expect(mountedCards()).toBeGreaterThan(0);
    expect(mountedCards()).toBeLessThan(100);
  });

  it('windows the list on scroll — off-screen cards mount, on-screen cards unmount', async () => {
    setupLargeBoard();
    await waitFor(() => expect(screen.getByTestId('board-column-list-pending')).toBeTruthy());

    const pendingList = screen.getByTestId('board-column-list-pending');

    pendingList.scrollTop = CARD_ROW_HEIGHT * 20;
    fireEvent.scroll(pendingList);

    await waitFor(
      () => expect(cardsIn(pendingList).getByLabelText('PID00001-T122')).toBeTruthy(), // pending #20
    );
    expect(cardsIn(pendingList).queryByLabelText('PID00001-T002')).toBeNull();
  });

  it('keeps off-screen cards reachable by keyboard (no dead ends, Section 13.4)', async () => {
    setupLargeBoard();
    await waitFor(() => expect(screen.getByTestId('board-column-list-pending')).toBeTruthy());
    const pendingList = screen.getByTestId('board-column-list-pending');

    fireEvent.keyDown(pendingList, { key: 'ArrowDown' });
    await waitFor(() => expect(document.activeElement?.getAttribute('data-index')).toBe('0'));
    fireEvent.keyDown(pendingList, { key: 'ArrowDown' });
    await waitFor(() => expect(document.activeElement?.getAttribute('data-index')).toBe('1'));

    fireEvent.keyDown(pendingList, { key: 'End' });
    await waitFor(() => expect(document.activeElement?.getAttribute('data-index')).toBe('83'));
    // The last pending card (task #500) is now mounted and focused.
    expect(cardsIn(pendingList).getByLabelText('PID00001-T500')).toBeTruthy();
    expect(cardsIn(pendingList).queryByLabelText('PID00001-T002')).toBeNull();

    fireEvent.keyDown(pendingList, { key: 'Home' });
    await waitFor(() => expect(cardsIn(pendingList).getByLabelText('PID00001-T002')).toBeTruthy());
  });

  it('reconciles live patches without resetting scroll position', async () => {
    const { streams } = setupLargeBoard();
    await waitFor(() => expect(screen.getByTestId('board-column-list-pending')).toBeTruthy());
    const pendingList = screen.getByTestId('board-column-list-pending');

    pendingList.scrollTop = CARD_ROW_HEIGHT * 20;
    fireEvent.scroll(pendingList);
    await waitFor(() => expect(cardsIn(pendingList).getByLabelText('PID00001-T122')).toBeTruthy());

    // An agent claims a pending card inside the window → it moves columns.
    streams[0].frame(
      900,
      makeEventEnvelope({
        id: 900,
        type: 'task.transitioned',
        task_id: 'PID00001-T122',
        data: {
          from_state: 'pending',
          to_state: 'in_progress',
          reason_code: 'claimed',
          task_version: 2,
        },
      }),
    );

    await waitFor(() => expect(cardsIn(pendingList).queryByLabelText('PID00001-T122')).toBeNull());
    // Scroll survives the patch; the window does not jump to the top.
    expect(pendingList.scrollTop).toBe(CARD_ROW_HEIGHT * 20);
    expect(cardsIn(pendingList).getByLabelText('PID00001-T128')).toBeTruthy();
    expect(cardsIn(pendingList).queryByLabelText('PID00001-T002')).toBeNull();
  });

  it('keeps the MT-4.3-01 states working with virtualization enabled', async () => {
    setupLargeBoard();
    await waitFor(() => expect(mountedCards()).toBeGreaterThan(0));

    // Filtered-empty state still replaces the (virtualized) columns…
    fireEvent.change(screen.getByTestId('board-search'), { target: { value: 'no-such-task' } });
    await waitFor(() =>
      expect(screen.getByText('No tasks match the current filters')).toBeTruthy(),
    );
    expect(mountedCards()).toBe(0);

    // …and clearing restores the virtualized board.
    fireEvent.click(screen.getByTestId('board-empty-clear-filters'));
    await waitFor(() => expect(mountedCards()).toBeGreaterThan(0));
  });
});

function cardsIn(element: HTMLElement) {
  return {
    getByLabelText: (label: string) =>
      element.querySelector(`[aria-label="${label}"]`) as HTMLElement | null,
    queryByLabelText: (label: string) =>
      element.querySelector(`[aria-label="${label}"]`) as HTMLElement | null,
  };
}
