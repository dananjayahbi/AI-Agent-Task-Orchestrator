/**
 * Optimistic moves with rollback (MT-4.4-04;
 * `npm test -- -t optimistic-rollback`).
 *
 * Section 13.2: a confirmed dialog action reflects immediately (T15 only
 * flips the merge-pending badge — Section 8.1), the request carries the
 * `version` the client saw (Section 8.2 rule 3), `VERSION_CONFLICT` and
 * `TASK_STATE_CONFLICT` roll the card back to **server truth** with
 * distinct catalog-mapped messages (Section 13.3), and the confirming
 * `review.decided` event settles idempotently whether it arrives before
 * or after the HTTP response — no double move, no oscillation, filters
 * intact (WP-4.4 acceptance).
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import type { Task } from '@/lib/api/generated/types.gen';
import type { BoardState } from '@/lib/board/states';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makePolicy,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
  type Route,
  type SseConnection,
} from '../helpers/api';
import { makeResolution } from '../helpers/task-detail';

afterEach(() => {
  vi.unstubAllGlobals();
});

const TASK_ID = 'PID00001-T005';
const TASKS_URL = /\/api\/v1\/projects\/PID00001\/tasks(\?|$)/;

function reviewSuccess(state: 'in_human_review' | 'pending', version: number) {
  return {
    decision: { id: 'dec-1' },
    task: {
      id: TASK_ID,
      state,
      version,
      review_reason: 'test_failure',
      merge_status: state === 'pending' ? 'none' : 'pending',
    },
  };
}

/**
 * Board harness with a gateable review POST and a mutable server-truth
 * row for the rollback refresh (`GET /tasks/{id}`).
 */
function setup(options: {
  serverRow: Task;
  review: () => Promise<Response> | Response;
  resolutions?: unknown[];
}) {
  let serverRow = options.serverRow;
  const conn = sseConnection();
  const routes: Route[] = [
    { method: 'GET', match: TASKS_URL, respond: () => jsonResponse(pageOf([serverRow])) },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/resolutions(\?|$)/,
      respond: () => jsonResponse(pageOf(options.resolutions ?? [])),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
      respond: () => jsonResponse(serverRow),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/projects\/PID00001\/policy(\?|$)/,
      respond: () => jsonResponse(makePolicy()),
    },
    {
      method: 'POST',
      match: /\/api\/v1\/tasks\/[^/]+\/review$/,
      respond: () => options.review(),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/events\/stream(\?|$)/,
      respond: () => conn.response,
    },
  ];
  const { calls } = installApi(routes);
  const view = renderWithQueryClient(<Board pid="PID00001" />);
  return {
    calls,
    stream: conn as SseConnection,
    setServerRow: (row: Task) => {
      serverRow = row;
    },
    ...view,
  };
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

function dragTo(sourceState: BoardState, targetState: BoardState): void {
  fireEvent.dragStart(cardIn(sourceState));
  fireEvent.dragOver(column(targetState));
  fireEvent.drop(column(targetState));
}

async function openRequestChanges(): Promise<void> {
  await screen.findByTestId('task-card');
  dragTo('in_human_review', 'pending');
  await screen.findByTestId('request-changes-dialog');
  fireEvent.change(screen.getByTestId('request-changes-note'), {
    target: { value: 'Rework needed' },
  });
  fireEvent.click(screen.getByTestId('request-changes-confirm'));
}

function decidedEvent(id: number, toState: string, version: number) {
  return {
    id,
    type: 'review.decided',
    project_id: 'PID00001',
    task_id: TASK_ID,
    occurred_at: '2026-10-01T12:00:00Z',
    actor: { type: 'owner', ref: 'owner-1' },
    data: {
      from_state: 'in_human_review',
      to_state: toState,
      reason_code: 'request_changes',
      task_version: version,
    },
  };
}

describe('optimistic-rollback (MT-4.4-04)', () => {
  it('reflects the confirmed move before the server answers, then settles idempotently', async () => {
    let release!: (response: Response) => void;
    const gate = new Promise<Response>((resolve) => {
      release = resolve;
    });
    const original = makeTask({ id: TASK_ID, state: 'in_human_review', version: 3 });
    const { stream, setServerRow } = setup({ serverRow: original, review: () => gate });

    await openRequestChanges();

    // Optimistic: the card is in Pending while the POST is in flight.
    await waitFor(() => expect(within(column('pending')).getByTestId('task-card')).toBeTruthy());
    expect(screen.queryByTestId('request-changes-dialog')).toBeTruthy(); // response pending

    // Server committed (the event arrives before the HTTP response):
    // the confirming event supersedes with server truth.
    setServerRow(makeTask({ id: TASK_ID, state: 'pending', version: 6 }));
    stream.frame(2, decidedEvent(2, 'pending', 6));
    await waitFor(() =>
      expect(within(column('pending')).getAllByTestId('task-card')).toHaveLength(1),
    );

    // HTTP response lands afterwards — same values, no oscillation.
    release(jsonResponse(reviewSuccess('pending', 6)));
    await waitFor(() => expect(screen.queryByTestId('request-changes-dialog')).toBeNull());
    await waitFor(() => expect(noticeText()).toContain('Pending'));
    expect(within(column('pending')).getAllByTestId('task-card')).toHaveLength(1);
    expect(
      screen
        .queryByTestId('board-column-in_human_review')
        ?.querySelector('[data-testid="task-card"]') ?? null,
    ).toBeNull();
  });

  it('keeps the approved task in review with the merge-pending badge outcome (Section 8.1)', async () => {
    const original = makeTask({ id: TASK_ID, state: 'in_human_review', version: 3 });
    const { calls } = setup({
      serverRow: original,
      resolutions: [makeResolution()],
      review: () => jsonResponse(reviewSuccess('in_human_review', 4)),
    });
    await screen.findByTestId('task-card');

    dragTo('in_human_review', 'completed');
    await screen.findByTestId('approve-resolution-context');
    fireEvent.click(screen.getByTestId('approve-confirm'));

    // Approve never moves columns — merge-pending is a sub-status.
    await waitFor(() => expect(noticeText()).toContain('merge pending'));
    expect(within(column('in_human_review')).getByTestId('task-card')).toBeTruthy();
    expect(calls.some((call) => call.method === 'POST' && call.pathname.endsWith('/review'))).toBe(
      true,
    );
  });

  it('VERSION_CONFLICT rolls back to server truth with its distinct mapped message', async () => {
    let release!: (response: Response) => void;
    const gate = new Promise<Response>((resolve) => {
      release = resolve;
    });
    const original = makeTask({ id: TASK_ID, state: 'in_human_review', version: 3 });
    const { calls } = setup({ serverRow: original, review: () => gate });

    await openRequestChanges();

    // Optimistic move first…
    await waitFor(() => expect(within(column('pending')).getByTestId('task-card')).toBeTruthy());
    // …then the server answers 409 — roll back to server truth.
    release(errorResponse('VERSION_CONFLICT', 409));
    // …then the rollback: the row refresh lands back in Human review.
    await waitFor(() =>
      expect(within(column('in_human_review')).getByTestId('task-card')).toBeTruthy(),
    );
    expect(
      screen.queryByTestId('board-column-pending')?.querySelector('[data-testid="task-card"]') ??
        null,
    ).toBeNull();
    expect(noticeText()).toContain('Outdated version'); // catalog copy (Section 13.3)
    expect(noticeText()).toContain('server’s current state'); // refresh explained
    // Rollback refreshed the row from the API (never restore-from-memory).
    expect(
      calls.filter((call) => call.method === 'GET' && call.pathname === `/api/v1/tasks/${TASK_ID}`)
        .length,
    ).toBeGreaterThan(0);
  });

  it('TASK_STATE_CONFLICT rolls back with its own distinct message', async () => {
    let release!: (response: Response) => void;
    const gate = new Promise<Response>((resolve) => {
      release = resolve;
    });
    const original = makeTask({ id: TASK_ID, state: 'in_human_review', version: 3 });
    setup({ serverRow: original, review: () => gate });

    await openRequestChanges();
    await waitFor(() => expect(within(column('pending')).getByTestId('task-card')).toBeTruthy());
    release(errorResponse('TASK_STATE_CONFLICT', 409));

    await waitFor(() =>
      expect(within(column('in_human_review')).getByTestId('task-card')).toBeTruthy(),
    );
    expect(noticeText()).toContain('Task changed'); // distinct from VERSION_CONFLICT
    expect(noticeText()).not.toContain('Outdated version');
  });

  it('keeps filters intact through a conflicting move', async () => {
    let release!: (response: Response) => void;
    const gate = new Promise<Response>((resolve) => {
      release = resolve;
    });
    const original = makeTask({ id: TASK_ID, state: 'in_human_review', version: 3 });
    setup({ serverRow: original, review: () => gate });
    await screen.findByTestId('task-card');

    const search = screen.getByTestId('board-search') as HTMLInputElement;
    fireEvent.change(search, { target: { value: 'login' } });
    expect(search.value).toBe('login');

    await openRequestChanges();
    await waitFor(() => expect(within(column('pending')).getByTestId('task-card')).toBeTruthy());
    release(errorResponse('VERSION_CONFLICT', 409));
    await waitFor(() =>
      expect(within(column('in_human_review')).getByTestId('task-card')).toBeTruthy(),
    );
    expect((screen.getByTestId('board-search') as HTMLInputElement).value).toBe('login');
    expect(screen.getByTestId('board-filters')).toBeTruthy();
  });
});
