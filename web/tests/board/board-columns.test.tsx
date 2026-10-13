/**
 * MT-4.3-01 — six board columns mapped 1:1 to the canonical states
 * (Section 13.2; G-01; Section 8.1 merge-pending badge note).
 */
import { screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import { BOARD_STATES, STATE_LABELS } from '@/lib/board/states';
import {
  installApi,
  installBoardApi,
  jsonResponse,
  makeEventEnvelope,
  makePolicy,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
} from '../helpers/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('Board — six canonical columns (MT-4.3-01)', () => {
  it('renders exactly six columns, keyed and ordered by the canonical states', async () => {
    const sse = sseConnection();
    installBoardApi({
      tasks: [
        makeTask({ id: 'PID00001-T001', state: 'draft' }),
        makeTask({ id: 'PID00001-T002', state: 'pending' }),
        makeTask({ id: 'PID00001-T003', state: 'in_progress' }),
        makeTask({ id: 'PID00001-T004', state: 'to_be_audited' }),
        makeTask({ id: 'PID00001-T005', state: 'in_human_review' }),
        makeTask({ id: 'PID00001-T006', state: 'completed' }),
      ],
      sse: () => sse.response,
    });

    const { container } = renderWithQueryClient(<Board pid="PID00001" />);
    await waitFor(() => expect(screen.getByTestId('board-column-completed')).toBeTruthy());

    const columns = container.querySelectorAll('section[data-testid^="board-column-"]');
    expect([...columns].map((column) => column.getAttribute('data-testid'))).toEqual(
      BOARD_STATES.map((state) => `board-column-${state}`),
    );
    // Labels are presentation-only; the keys are the machine values.
    expect(screen.getByRole('heading', { name: STATE_LABELS.draft })).toBeTruthy();
    expect(screen.getByRole('heading', { name: STATE_LABELS.in_human_review })).toBeTruthy();
  });

  it('groups tasks by canonical state and drives data through the generated client', async () => {
    const { calls } = installBoardApi({
      tasks: [
        makeTask({ id: 'PID00001-T001', title: 'Draft task', state: 'draft' }),
        makeTask({ id: 'PID00001-T002', title: 'Pending task', state: 'pending' }),
        makeTask({ id: 'PID00001-T003', title: 'Another pending', state: 'pending' }),
      ],
      sse: () => sseConnection().response,
    });

    renderWithQueryClient(<Board pid="PID00001" />);
    await waitFor(() => expect(screen.getByText('Pending task')).toBeTruthy());

    const pendingColumn = screen.getByTestId('board-column-pending');
    expect(within(pendingColumn).getByText('Pending task')).toBeTruthy();
    expect(within(pendingColumn).getByText('Another pending')).toBeTruthy();
    expect(within(pendingColumn).queryByText('Draft task')).toBeNull();
    expect(within(screen.getByTestId('board-column-draft')).getByText('Draft task')).toBeTruthy();
    expect(within(pendingColumn).getByTestId('board-column-count-pending').textContent).toBe('2');

    // NFR-11: the only transport is the generated client's tasks list call.
    const listCalls = calls.filter((call) => call.pathname === '/api/v1/projects/PID00001/tasks');
    expect(listCalls).toHaveLength(1);
    expect(listCalls[0].search).toContain('page_size=100');
  });

  it('keeps merge-pending tasks in their state column with the Section 8.1 badge — no seventh column', async () => {
    installBoardApi({
      tasks: [
        makeTask({ id: 'PID00001-T001', state: 'to_be_audited', merge_status: 'pending' }),
        makeTask({ id: 'PID00001-T002', state: 'in_human_review', merge_status: 'merging' }),
      ],
      sse: () => sseConnection().response,
    });

    const { container } = renderWithQueryClient(<Board pid="PID00001" />);
    await waitFor(() => expect(screen.getAllByTestId('task-card-merge-badge')).toHaveLength(2));

    const audited = within(screen.getByTestId('board-column-to_be_audited'));
    expect(audited.getByTestId('task-card-merge-badge').textContent).toBe('approved, merging');
    expect(
      within(screen.getByTestId('board-column-in_human_review')).getAllByTestId(
        'task-card-merge-badge',
      ),
    ).toHaveLength(1);

    const columns = container.querySelectorAll('section[data-testid^="board-column-"]');
    expect(columns).toHaveLength(6);
    expect(container.querySelector('[data-testid="board-column-merge-pending"]')).toBeNull();
  });

  it('shows the loading state while the list is pending', async () => {
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/tasks(\?|$)/,
        respond: async () => {
          await gate;
          return jsonResponse(pageOf([]));
        },
      },
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/policy(\?|$)/,
        respond: () => jsonResponse(makePolicy()),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/events\/stream(\?|$)/,
        respond: () => sseConnection().response,
      },
    ]);

    renderWithQueryClient(<Board pid="PID00001" />);
    expect(screen.getByText('Loading board…')).toBeTruthy();
    release?.();
    await waitFor(() => expect(screen.getByText('No tasks in this project yet')).toBeTruthy());
  });

  it('maps list errors to canonical catalog copy and never shows raw server text', async () => {
    let failNext = true;
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/tasks(\?|$)/,
        respond: () => {
          if (failNext) {
            failNext = false;
            return new Response(
              JSON.stringify({
                error: {
                  code: 'SERVER_ERROR',
                  message: 'Traceback: very raw detail',
                  retryable: true,
                  details: null,
                  correlation_id: 'corr-board',
                },
              }),
              { status: 500, headers: { 'Content-Type': 'application/json' } },
            );
          }
          return jsonResponse(pageOf([makeTask()]));
        },
      },
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/policy(\?|$)/,
        respond: () => jsonResponse(makePolicy()),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/events\/stream(\?|$)/,
        respond: () => sseConnection().response,
      },
    ]);

    renderWithQueryClient(<Board pid="PID00001" />);
    await waitFor(() =>
      expect(
        screen.getByText(
          'The server had a problem handling this request. Try again — if it keeps failing, share the reference ID with support.',
        ),
      ).toBeTruthy(),
    );
    expect(screen.queryByText('Traceback: very raw detail')).toBeNull();
    expect(screen.getByText('Reference ID: corr-board')).toBeTruthy();

    // Retry recovers into the board.
    failNext = false;
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('board')).toBeTruthy());
  });

  it('shows the project-empty state (distinct from loading and error) when there are no tasks', async () => {
    installBoardApi({ tasks: [], sse: () => sseConnection().response });
    renderWithQueryClient(<Board pid="PID00001" />);

    await waitFor(() => expect(screen.getByText('No tasks in this project yet')).toBeTruthy());
    expect(screen.queryByText('Loading board…')).toBeNull();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('streams without crashing when only heartbeat comments arrive', async () => {
    const sse = sseConnection();
    installBoardApi({ tasks: [makeTask()], sse: () => sse.response });
    renderWithQueryClient(<Board pid="PID00001" />);
    await waitFor(() => expect(screen.getByTestId('board')).toBeTruthy());

    sse.heartbeat();
    sse.frame(2, makeEventEnvelope({ id: 2, type: 'system.alert', task_id: null, data: {} }));
    // Unknown-to-the-board catalog types are ignored safely (Section 20.4 item 6).
    await waitFor(() =>
      expect(screen.getByTestId('stream-status').getAttribute('data-status')).toBe('open'),
    );
    expect(screen.getByTestId('task-card')).toBeTruthy();
  });
});
