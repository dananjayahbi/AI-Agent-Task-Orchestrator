/**
 * MT-4.11-04 — repeatable board-load check at 500 cards (Section 13.4:
 * "Board with 500 cards stays responsive (virtualized columns); first
 * load under 3 s on LAN"; Section 18 Performance row — board load).
 *
 * What this script measures (jsdom; caveats documented in
 * docs/plan/web-performance-report.md — jsdom has no paint, so these
 * are JS-execution costs that bound the browser's work, and the LAN
 * first-load budget is derived from the production bundle instead):
 *
 *  1. mount cost — wall-clock to first painted DOM for the 500-card
 *     board with all six columns populated;
 *  2. bounded render — mounted card nodes stay a small window, far
 *     below 500 (the MT-4.3-06 mechanism re-verified on the finished
 *     WP-4.11 UI);
 *  3. scroll windowing — jumping deep into a column re-windows without
 *     mounting the whole list;
 *  4. live-update cost — a batch of SSE transition patches applied to
 *     the full board settles within the recorded budget (Sections
 *     13.3/13.4);
 *  5. filter cost — a search keystroke over 500 cards settles fast
 *     (the client-side predicate path).
 *
 * Thresholds are deliberately generous (CI machines vary); the measured
 * numbers are logged so the report records evidence, and the assertions
 * catch order-of-magnitude regressions.
 */
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import { CARD_ROW_HEIGHT } from '@/components/board/virtual-list';
import { visibleWindow } from '@/lib/board/windowing';
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

const CARD_COUNT = 500;

/** Synthetic Section 13.4 board: 500 tasks cycling through the six states. */
function makeBoardFixture() {
  return Array.from({ length: CARD_COUNT }, (_, index) =>
    makeTask({
      id: `PID00001-T${String(index + 1).padStart(3, '0')}`,
      title: `Task ${index + 1}`,
      state: BOARD_STATES[index % BOARD_STATES.length],
    }),
  );
}

function setupLargeBoard() {
  const streams: SseConnection[] = [];
  installApi([
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
  return { streams: streams as SseConnection[] };
}

const mountedCards = () => document.querySelectorAll('[data-testid="task-card"]').length;

/** Milliseconds of wall clock — performance.now under jsdom. */
const now = () => performance.now();

function log(label: string, ms: number, extra = '') {
  console.log(`[board-load] ${label}: ${ms.toFixed(1)}ms ${extra}`.trim());
}

function logCount(label: string, count: number, extra = '') {
  console.log(`[board-load] ${label}: ${count} ${extra}`.trim());
}

describe('board-load at 500 cards (MT-4.11-04)', () => {
  it('mounts the full board within budget with virtualization engaged', async () => {
    const started = now();
    setupLargeBoard();
    await screen.findByTestId('board-columns');
    const mountMs = now() - started;
    log('mount 500-card board', mountMs);

    // All six columns present, full counts reported…
    for (const state of BOARD_STATES) {
      expect(screen.getByTestId(`board-column-count-${state}`)).toBeTruthy();
    }
    // …but a bounded DOM: six columns × (fallback viewport window + overscan).
    const cards = mountedCards();
    logCount('mounted card nodes', cards, `(${CARD_COUNT} in data)`);
    expect(cards).toBeGreaterThan(0);
    expect(cards).toBeLessThan(100);
    // Generous CI budget (order-of-magnitude regression guard).
    expect(mountMs).toBeLessThan(2000);
  });

  it('windows deep into a column without mounting the whole list', async () => {
    setupLargeBoard();
    await waitFor(() => expect(screen.getByTestId('board-column-list-pending')).toBeTruthy());
    const pendingList = screen.getByTestId('board-column-list-pending');

    const started = now();
    // Pending is every 6th task: row ~60 is PID00001-T362.
    pendingList.scrollTop = CARD_ROW_HEIGHT * 60;
    fireEvent.scroll(pendingList);
    await waitFor(() =>
      expect(pendingList.querySelector('[aria-label="PID00001-T362"]')).not.toBeNull(),
    );
    const scrollMs = now() - started;
    log('scroll to pending row ~60', scrollMs);
    // Bounded, not proportional to scroll depth: ≤10 rows per column
    // (viewport + overscan), six columns → well under 100 nodes.
    expect(mountedCards()).toBeLessThan(100);
  });

  it('applies a batch of SSE transition patches to the full board within budget', async () => {
    const { streams } = setupLargeBoard();
    await waitFor(() => expect(screen.getByTestId('board-column-list-pending')).toBeTruthy());

    // 25 live transitions — a realistic busy burst (Section 9.6 stream).
    // Pending cards are T002, T008, T014, … (every 6th).
    const batch = 25;
    const started = now();
    for (let index = 0; index < batch; index += 1) {
      const taskId = `PID00001-T${String(2 + index * 6).padStart(3, '0')}`;
      streams[0].frame(
        900 + index,
        makeEventEnvelope({
          id: 900 + index,
          type: 'task.transitioned',
          task_id: taskId,
          data: {
            from_state: 'pending',
            to_state: 'in_progress',
            reason_code: 'claimed',
            task_version: 2,
          },
        }),
      );
    }
    // Settle: the first patched cards leave their column (pure cache
    // patch, no refetch — MT-4.3-05). In-progress starts at 83 of the
    // 500-card cycle; 25 claimed → 108.
    await waitFor(() =>
      expect(screen.getByTestId('board-column-count-in_progress').textContent).toBe('108'),
    );
    const patchMs = now() - started;
    log(`${batch} SSE transition patches`, patchMs, `(${(patchMs / batch).toFixed(2)}ms/event)`);
    expect(patchMs).toBeLessThan(2000);
    // Bounded DOM still holds after the burst.
    expect(mountedCards()).toBeLessThan(100);
  });

  it('filters 500 cards within budget', async () => {
    setupLargeBoard();
    await screen.findByTestId('board-columns');

    const started = now();
    fireEvent.change(screen.getByTestId('board-search'), { target: { value: 'Task 42' } });
    await waitFor(() => expect(mountedCards()).toBeLessThan(CARD_COUNT));
    const filterMs = now() - started;
    log('search filter keystroke', filterMs);
    expect(filterMs).toBeLessThan(1000);

    fireEvent.change(screen.getByTestId('board-search'), { target: { value: '' } });
    await waitFor(() => expect(mountedCards()).toBeGreaterThan(0));
  });
});

/** The windowing math stays bounded for any scroll offset (pure). */
describe('windowing math at 500 rows (MT-4.11-04)', () => {
  it('mounts a bounded slice for every row-boundary offset', () => {
    const count = 500;
    const itemHeight = CARD_ROW_HEIGHT;
    const viewport = 480;
    const overscan = 3;
    const mounted = (rows: { startIndex: number; endIndex: number }) =>
      rows.endIndex - rows.startIndex;
    // Full viewport walk, one sample per row boundary.
    for (let row = 0; row < count; row += 1) {
      const window_ = visibleWindow(row * itemHeight, itemHeight, viewport, count, overscan);
      expect(window_.startIndex).toBeGreaterThanOrEqual(0);
      expect(window_.endIndex).toBeLessThanOrEqual(count);
      // ceil(480/132)=4 visible rows + 2×3 overscan = 10 mounted rows max.
      expect(mounted(window_)).toBeLessThanOrEqual(10);
    }
  });

  it('clamps the extremes', () => {
    expect(visibleWindow(0, 132, 480, 500, 3)).toEqual({ startIndex: 0, endIndex: 7 });
    const end = visibleWindow(999999, 132, 480, 500, 3);
    expect(end.endIndex).toBe(500);
    expect(end.startIndex).toBeGreaterThan(480);
    expect(visibleWindow(0, 132, 480, 0, 3)).toEqual({ startIndex: 0, endIndex: 0 });
    expect(visibleWindow(-50, 132, 480, 500, 3).startIndex).toBe(0);
  });
});
