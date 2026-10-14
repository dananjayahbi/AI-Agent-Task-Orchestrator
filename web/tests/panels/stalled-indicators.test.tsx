/**
 * MT-4.9-03 — stalled-task indicators (Sections 8.6, 13.1; policy
 * `stalled_after_minutes`).
 *
 * Section 8.6 is UI-only: no checkpoint within the policy threshold while
 * the lease is still valid. These tests pin: before/after threshold under
 * a frozen clock, the policy value honored when it differs from the
 * documented default (no hard-coded 20), live clearing on a progress
 * `task.checkpoint` (targeted refetch), clearing when the lease ends, and
 * the Section 9.9 `system.alert` intake refreshing the indicator from
 * server state.
 */
import { screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SessionsView } from '@/components/panels/sessions-view';
import { resetServerClock } from '@/lib/server-clock';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makeEventEnvelope,
  makePolicy,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
  tasksServerRoute,
  type SseConnection,
} from '../helpers/api';

const NOW = new Date('2026-10-01T12:00:00Z');
const iso = (minutes: number): string => new Date(NOW.getTime() + minutes * 60_000).toISOString();

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  resetServerClock();
});

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] }); // frozen Date; real timers for SSE
  vi.setSystemTime(NOW);
  window.localStorage.clear();
});

type RecordedCall = { pathname: string };

function setupStalledView(options: { tasks?: unknown[]; policy?: Record<string, unknown> }): {
  calls: RecordedCall[];
  streams: SseConnection[];
  rows: Map<string, unknown>;
} {
  const { tasks = [], policy = makePolicy({ stalled_after_minutes: 20 }) } = options;
  const streams: SseConnection[] = [];
  const rows = new Map<string, unknown>(tasks.map((task) => [(task as { id: string }).id, task]));
  const { calls } = installApi([
    tasksServerRoute('PID00001', tasks),
    {
      method: 'GET',
      match: /\/api\/v1\/projects\/PID00001\/policy(\?|$)/,
      respond: () => jsonResponse(policy),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/events(\?|$)/,
      respond: () => jsonResponse(pageOf([])),
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
  renderWithQueryClient(<SessionsView pid="PID00001" />);
  return { calls, streams, rows };
}

const stalledTask = (overrides: Partial<Record<string, unknown>> = {}) =>
  makeTask({
    id: 'PID00001-T001',
    title: 'Stall watch',
    state: 'in_progress',
    worker_agent_id: 'coder-1',
    worker_session_id: 'sess-1',
    claimed_role: 'coder',
    created_at: iso(-120),
    lease_acquired_at: iso(-50),
    lease_expires_at: iso(20), // lease still valid — stall ≠ expiry
    last_checkpoint_at: iso(-25), // beyond the default 20-minute threshold
    ...overrides,
  });

const taskRowFetches = (calls: RecordedCall[]) =>
  calls.filter((call) => /^\/api\/v1\/tasks\//.test(call.pathname));

describe('Stalled indicator (MT-4.9-03)', () => {
  it('does not show before the threshold passes (Section 8.6 — lease valid, recent checkpoint)', async () => {
    setupStalledView({
      tasks: [stalledTask({ last_checkpoint_at: iso(-5) })],
    });
    await screen.findByTestId('session-lease');
    expect(screen.queryByTestId('stalled-indicator')).toBeNull();
  });

  it('appears after stalled_after_minutes with no checkpoint while the lease is valid', async () => {
    setupStalledView({ tasks: [stalledTask()] });
    const marker = await screen.findByTestId('stalled-indicator');
    // Accessible text label (Section 13.4) + threshold disclosed in the title.
    expect(marker.textContent).toBe('Stalled');
    expect(marker.getAttribute('title')).toContain('stalled_after_minutes (20 min)');
    const lease = screen.getByTestId('session-lease');
    expect(within(lease).getByTestId('lease-countdown').getAttribute('data-state')).toBe(
      'remaining',
    );
  });

  it('honors a policy threshold that differs from the documented default', async () => {
    setupStalledView({
      tasks: [stalledTask()], // -25m checkpoint: stalls at 20, not at 60
      policy: makePolicy({ stalled_after_minutes: 60 }),
    });
    await screen.findByTestId('session-lease');
    expect(screen.queryByTestId('stalled-indicator')).toBeNull();
  });

  it('clears live on a fresh progress task.checkpoint (targeted refetch, no list refetch)', async () => {
    const { calls, streams, rows } = setupStalledView({ tasks: [stalledTask()] });
    await screen.findByTestId('stalled-indicator');

    rows.set(
      'PID00001-T001',
      stalledTask({ last_checkpoint_at: iso(0), lease_expires_at: iso(30) }),
    );
    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'task.checkpoint',
        task_id: 'PID00001-T001',
        occurred_at: iso(0),
        actor: { type: 'agent', ref: 'sess-1' },
        data: {
          checkpoint_id: 'CHK-2',
          attempt_number: 1,
          kind: 'progress',
          percent: 60,
          session_id: 'sess-1',
          message: 'moving',
          token_usage: null,
        },
      }),
    );

    await waitFor(() => expect(screen.queryByTestId('stalled-indicator')).toBeNull());
    expect(taskRowFetches(calls)).toHaveLength(1);
    expect(
      calls.filter((call) => call.pathname === '/api/v1/projects/PID00001/tasks'),
    ).toHaveLength(1);
  });

  it('stops showing stall when the lease ends (Section 8.6 — lease must still be valid)', async () => {
    const { streams } = setupStalledView({ tasks: [stalledTask()] });
    await screen.findByTestId('stalled-indicator');

    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'task.released',
        task_id: 'PID00001-T001',
        occurred_at: iso(-24),
        actor: { type: 'agent', ref: 'sess-1' },
        data: {
          from_state: 'in_progress',
          to_state: 'pending',
          reason_code: 'voluntary_release',
          task_version: 4,
        },
      }),
    );

    await waitFor(() => expect(screen.queryByTestId('stalled-indicator')).toBeNull());
    expect(screen.getByTestId('session-ended-row')).toBeTruthy();
  });

  it('refreshes from server state on the Section 9.9 system.alert intake', async () => {
    const { calls, streams, rows } = setupStalledView({ tasks: [stalledTask()] });
    await screen.findByTestId('stalled-indicator');

    // Server saw progress the stream missed — the alert's refetch recovers it.
    rows.set('PID00001-T001', stalledTask({ last_checkpoint_at: iso(0) }));
    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'system.alert',
        task_id: 'PID00001-T001',
        occurred_at: iso(0),
        actor: { type: 'system', ref: 'stalled-detector' },
        data: { level: 'warn', kind: 'stalled', task_id: 'PID00001-T001' },
      }),
    );

    await waitFor(() => expect(taskRowFetches(calls)).toHaveLength(1));
    await waitFor(() => expect(screen.queryByTestId('stalled-indicator')).toBeNull());
    expect(screen.getByTestId('session-lease')).toBeTruthy();
  });
});
