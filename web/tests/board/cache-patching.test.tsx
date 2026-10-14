/**
 * MT-4.3-05 — query-cache patching from stream events (Section 13.3;
 * Section 9.6 envelope; Section 7.2 version; Section 19 WP-4.3 acceptance:
 * an agent transition appears without refresh and without refetch).
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import {
  errorResponse,
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

const LIST_PATH = '/api/v1/projects/PID00001/tasks';

type BoardFixture = {
  calls: Array<{ method: string; pathname: string; search: string }>;
  streams: SseConnection[];
  rows: Map<string, unknown>;
};

function setupBoard(tasks: unknown[]): BoardFixture {
  const streams: SseConnection[] = [];
  const rows = new Map<string, unknown>(tasks.map((task) => [(task as { id: string }).id, task]));
  const { calls } = installApi([
    tasksServerRoute('PID00001', tasks),
    {
      method: 'GET',
      match: /\/api\/v1\/projects\/PID00001\/policy(\?|$)/,
      respond: () => jsonResponse(makePolicy()),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
      respond: ({ pathname }) => {
        const id = pathname.split('/').pop() ?? '';
        const row = rows.get(id);
        if (row === undefined) {
          return errorResponse('TASK_NOT_FOUND', 404);
        }
        return jsonResponse(row);
      },
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
  return { calls, streams, rows };
}

const listCalls = (calls: BoardFixture['calls']) =>
  calls.filter((call) => call.pathname === LIST_PATH);
const taskRowCalls = (calls: BoardFixture['calls']) =>
  calls.filter((call) => /^\/api\/v1\/tasks\//.test(call.pathname));

const settle = () => new Promise((resolve) => setTimeout(resolve, 10));

describe('Board cache patching (MT-4.3-05)', () => {
  it('moves a card on task.transitioned within seconds — with zero refetches (Section 19 acceptance)', async () => {
    const { calls, streams } = setupBoard([makeTask({ id: 'PID00001-T001', state: 'pending' })]);
    await waitFor(() =>
      expect(
        within(screen.getByTestId('board-column-pending')).getByTestId('task-card'),
      ).toBeTruthy(),
    );

    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'task.transitioned',
        task_id: 'PID00001-T001',
        data: {
          from_state: 'pending',
          to_state: 'in_progress',
          reason_code: 'claimed',
          task_version: 2,
        },
      }),
    );

    await waitFor(() => {
      expect(
        within(screen.getByTestId('board-column-in_progress')).getByTestId('task-card'),
      ).toBeTruthy();
      expect(screen.getByTestId('board-column-empty-pending')).toBeTruthy();
    });
    // The acceptance: no list refetch, no single-task fetch — pure cache patch.
    expect(listCalls(calls)).toHaveLength(1);
    expect(taskRowCalls(calls)).toHaveLength(0);
  });

  it('ignores stale events: an older task_version never regresses cached state', async () => {
    const { calls, streams } = setupBoard([
      makeTask({ id: 'PID00001-T001', state: 'pending', version: 5 }),
    ]);
    await waitFor(() => expect(screen.getByTestId('task-card')).toBeTruthy());

    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'task.transitioned',
        task_id: 'PID00001-T001',
        data: {
          from_state: 'draft',
          to_state: 'completed',
          reason_code: 'merged',
          task_version: 3,
        },
      }),
    );
    await settle();

    expect(
      within(screen.getByTestId('board-column-pending')).getByTestId('task-card'),
    ).toBeTruthy();
    expect(screen.queryByTestId('board-column-count-completed')).toBeTruthy();
    expect(
      within(screen.getByTestId('board-column-completed')).queryAllByTestId('task-card'),
    ).toHaveLength(0);
    expect(taskRowCalls(calls)).toHaveLength(0);
  });

  it('applies reconnect replays idempotently — no duplicate cards, no gaps', async () => {
    const { streams } = setupBoard([makeTask({ id: 'PID00001-T001', state: 'pending' })]);
    await waitFor(() => expect(screen.getByTestId('task-card')).toBeTruthy());

    const replay = makeEventEnvelope({
      id: 2,
      type: 'task.transitioned',
      task_id: 'PID00001-T001',
      data: {
        from_state: 'pending',
        to_state: 'in_progress',
        reason_code: 'claimed',
        task_version: 2,
      },
    });
    streams[0].frame(2, replay);
    streams[0].frame(2, replay); // server replay after resume re-delivers nothing, but be safe
    await waitFor(() =>
      expect(
        within(screen.getByTestId('board-column-in_progress')).getAllByTestId('task-card'),
      ).toHaveLength(1),
    );
  });

  it('removes a patched task that leaves the active filters (MT-4.3-03 composition)', async () => {
    const { calls, streams } = setupBoard([
      makeTask({ id: 'PID00001-T001', state: 'pending' }),
      makeTask({ id: 'PID00001-T002', state: 'draft' }),
    ]);
    await waitFor(() => expect(screen.getAllByTestId('task-card')).toHaveLength(2));

    // Restrict the board to the pending state only.
    for (const state of ['draft', 'in_progress', 'to_be_audited', 'in_human_review', 'completed']) {
      fireEvent.click(screen.getByTestId(`board-state-filter-${state}`));
    }
    await waitFor(() => expect(screen.getAllByTestId('task-card')).toHaveLength(1));
    const listCallsAfterFilter = listCalls(calls).length;

    streams[0].frame(
      3,
      makeEventEnvelope({
        id: 3,
        type: 'task.transitioned',
        task_id: 'PID00001-T001',
        data: {
          from_state: 'pending',
          to_state: 'in_progress',
          reason_code: 'claimed',
          task_version: 2,
        },
      }),
    );

    // The task moved out of the state filter → gone, without any refetch.
    await waitFor(() => expect(screen.queryAllByTestId('task-card')).toHaveLength(0));
    expect(screen.getByText('No tasks match the current filters')).toBeTruthy();
    expect(listCalls(calls)).toHaveLength(listCallsAfterFilter);
  });

  it('inserts task.created via a targeted single-task refetch when it matches the filters', async () => {
    const { calls, streams, rows } = setupBoard([
      makeTask({ id: 'PID00001-T001', state: 'pending' }),
    ]);
    await waitFor(() => expect(screen.getByTestId('task-card')).toBeTruthy());

    rows.set(
      'PID00001-T002',
      makeTask({ id: 'PID00001-T002', title: 'Fresh draft', state: 'draft', version: 1 }),
    );
    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'task.created',
        task_id: 'PID00001-T002',
        data: { task_version: 1 },
      }),
    );

    await waitFor(() =>
      expect(
        within(screen.getByTestId('board-column-draft')).getByText('Fresh draft'),
      ).toBeTruthy(),
    );
    expect(taskRowCalls(calls).map((call) => call.pathname)).toEqual([
      '/api/v1/tasks/PID00001-T002',
    ]);
    expect(listCalls(calls)).toHaveLength(1); // never a board refetch
  });

  it('does not insert a created task that fails the active server filters', async () => {
    const { calls, streams, rows } = setupBoard([
      makeTask({ id: 'PID00001-T001', state: 'pending', priority: 'high' }),
    ]);
    await waitFor(() => expect(screen.getByTestId('task-card')).toBeTruthy());
    fireEvent.change(screen.getByTestId('board-priority-filter'), { target: { value: 'high' } });
    await waitFor(() => expect(listCalls(calls)).toHaveLength(2));

    rows.set(
      'PID00001-T002',
      makeTask({
        id: 'PID00001-T002',
        title: 'Low priority draft',
        state: 'draft',
        priority: 'low',
      }),
    );
    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'task.created',
        task_id: 'PID00001-T002',
        data: { task_version: 1 },
      }),
    );
    await settle();

    expect(screen.queryByText('Low priority draft')).toBeNull();
    expect(taskRowCalls(calls)).toHaveLength(1); // refetched once, then filtered out
    expect(listCalls(calls)).toHaveLength(2);
  });

  it('updates the percent bar from task.checkpoint without any fetch', async () => {
    const { calls, streams } = setupBoard([
      makeTask({
        id: 'PID00001-T001',
        state: 'in_progress',
        worker_agent_id: 'coder-1',
        lease_expires_at: '2030-01-01T00:00:00Z',
      }),
    ]);
    await waitFor(() => expect(screen.getByTestId('task-card')).toBeTruthy());
    expect(screen.getByTestId('task-card-progress-label').textContent).toBe('Progress unknown');

    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'task.checkpoint',
        task_id: 'PID00001-T001',
        occurred_at: '2026-10-01T10:05:00Z',
        data: { percent: 55, kind: 'progress' },
      }),
    );

    await waitFor(() =>
      expect(screen.getByTestId('task-card-progress-label').textContent).toBe('55%'),
    );
    expect(taskRowCalls(calls)).toHaveLength(0);
    expect(listCalls(calls)).toHaveLength(1);
  });

  it('moves the card on task.claimed immediately, then refetches the one row for worker fields', async () => {
    const { calls, streams, rows } = setupBoard([
      makeTask({ id: 'PID00001-T001', state: 'pending', version: 1 }),
    ]);
    await waitFor(() => expect(screen.getByTestId('task-card')).toBeTruthy());

    rows.set(
      'PID00001-T001',
      makeTask({
        id: 'PID00001-T001',
        state: 'in_progress',
        version: 2,
        worker_agent_id: 'coder-9',
        lease_acquired_at: '2026-10-01T12:00:00Z',
        lease_expires_at: '2030-01-01T00:00:00Z',
      }),
    );
    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'task.claimed',
        task_id: 'PID00001-T001',
        data: {
          from_state: 'pending',
          to_state: 'in_progress',
          reason_code: 'claimed',
          task_version: 2,
        },
      }),
    );

    await waitFor(() => {
      expect(screen.getByText('coder-9')).toBeTruthy();
      expect(screen.getByTestId('board-column-empty-pending')).toBeTruthy();
    });
    expect(taskRowCalls(calls).map((call) => call.pathname)).toEqual([
      '/api/v1/tasks/PID00001-T001',
    ]);
    expect(listCalls(calls)).toHaveLength(1);
  });

  it('clears the lease and returns the card on task.lease_expired (Section 8.3 invariant)', async () => {
    const { calls, streams } = setupBoard([
      makeTask({
        id: 'PID00001-T001',
        state: 'in_progress',
        version: 3,
        worker_agent_id: 'coder-1',
        lease_expires_at: '2030-01-01T00:00:00Z',
      }),
    ]);
    await waitFor(() => expect(screen.getByText('coder-1')).toBeTruthy());

    streams[0].frame(
      4,
      makeEventEnvelope({
        id: 4,
        type: 'task.lease_expired',
        task_id: 'PID00001-T001',
        data: {
          from_state: 'in_progress',
          to_state: 'pending',
          reason_code: 'lease_expired',
          task_version: 4,
        },
      }),
    );

    await waitFor(() =>
      expect(
        within(screen.getByTestId('board-column-pending')).getByTestId('task-card'),
      ).toBeTruthy(),
    );
    expect(screen.queryByText('coder-1')).toBeNull();
    expect(taskRowCalls(calls)).toHaveLength(0); // pure patch — no guessing fetch
    expect(listCalls(calls)).toHaveLength(1);
  });

  it('ignores out-of-scope catalog events without breaking the stream', async () => {
    const { calls, streams } = setupBoard([makeTask({ id: 'PID00001-T001', state: 'pending' })]);
    await waitFor(() => expect(screen.getByTestId('task-card')).toBeTruthy());

    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'audit.escalated',
        task_id: 'PID00001-T001',
        data: { review_reason: 'auditor_flagged' },
      }),
    );
    streams[0].heartbeat();
    streams[0].frame(
      3,
      makeEventEnvelope({ id: 3, type: 'system.alert', task_id: null, data: {} }),
    );
    await settle();

    expect(
      within(screen.getByTestId('board-column-pending')).getByTestId('task-card'),
    ).toBeTruthy();
    expect(taskRowCalls(calls)).toHaveLength(0);
    expect(listCalls(calls)).toHaveLength(1);
  });
});
