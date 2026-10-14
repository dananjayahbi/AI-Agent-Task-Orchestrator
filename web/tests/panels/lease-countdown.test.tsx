/**
 * MT-4.9-02 — lease countdown displays (Sections 13.1/13.2, 8.6, 9.6;
 * Principle P7 — the server clock is authoritative).
 *
 * Pins: initial computation from server-issued `lease_expires_at` under
 * a frozen clock, the P7 re-anchor on a live envelope (server skew moves
 * the display), the checkpoint extension through the targeted refetch
 * (the event data omits the new deadline — Section 9.6), the 80% warning
 * (computed threshold AND the `task.lease_expiring` push, which also
 * re-arms the deadline from its own server field), clearing when the
 * lease ends, the expired presentation, and the no-lease → nothing rule
 * (Section 20.3).
 */
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { LeaseCountdown } from '@/components/panels/lease-countdown';
import { SessionsView } from '@/components/panels/sessions-view';
import { resetServerClock } from '@/lib/server-clock';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makeEventEnvelope,
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
  // Freeze only Date (P7 determinism): timers stay real so the SSE mock
  // and react-query behave exactly as in production.
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(NOW);
  window.localStorage.clear();
});

type RecordedCall = { pathname: string };

function setupLeaseView(options: { tasks?: unknown[]; events?: unknown[] }): {
  calls: RecordedCall[];
  streams: SseConnection[];
  rows: Map<string, unknown>;
} {
  const { tasks = [], events = [] } = options;
  const streams: SseConnection[] = [];
  const rows = new Map<string, unknown>(tasks.map((task) => [(task as { id: string }).id, task]));
  const { calls } = installApi([
    tasksServerRoute('PID00001', tasks),
    {
      method: 'GET',
      match: /\/api\/v1\/events(\?|$)/,
      respond: () => jsonResponse(pageOf(events)),
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

const leaseTask = (overrides: Partial<Record<string, unknown>> = {}) =>
  makeTask({
    id: 'PID00001-T001',
    title: 'Counted work',
    state: 'in_progress',
    worker_agent_id: 'coder-1',
    worker_session_id: 'sess-1',
    claimed_role: 'coder',
    lease_acquired_at: iso(-35), // 45-minute lease window
    lease_expires_at: iso(10),
    last_checkpoint_at: iso(-5),
    ...overrides,
  });

describe('LeaseCountdown (MT-4.9-02)', () => {
  it('renders nothing when there is no lease (Section 20.3 — no zero-value noise)', () => {
    const { container } = render(<LeaseCountdown acquiredAt={iso(-35)} expiresAt={null} />);
    expect(screen.queryByTestId('lease-countdown')).toBeNull();
    expect(container.textContent).toBe('');
  });

  it('computes the initial remaining time from server-issued expires_at, and shows "expired" past the deadline', () => {
    const { rerender } = renderWithQueryClient(
      <LeaseCountdown acquiredAt={iso(-35)} expiresAt={iso(10)} />,
    );
    const initial = screen.getByTestId('lease-countdown');
    expect(initial.textContent).toBe('10m 00s');
    expect(initial.getAttribute('data-state')).toBe('remaining');

    // Past the deadline: "expired" text, never a negative/wild value.
    rerender(<LeaseCountdown acquiredAt={iso(-50)} expiresAt={iso(-5)} />);
    const expired = screen.getByTestId('lease-countdown');
    expect(expired.textContent).toBe('expired');
    expect(expired.getAttribute('data-state')).toBe('expired');
  });

  it('re-anchors to server time from a live envelope (P7 — a skewed client clock cannot own the math)', async () => {
    const { streams } = setupLeaseView({ tasks: [leaseTask()] });
    const countdown = await screen.findByTestId('lease-countdown');
    expect(countdown.textContent).toBe('10m 00s');

    // Server stamped this envelope 60s BEFORE the local clock says "now".
    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'system.alert',
        task_id: null,
        occurred_at: iso(-1),
        actor: { type: 'system', ref: 'alert-detector' },
        data: { level: 'warn', message: 'clock sample' },
      }),
    );

    await waitFor(() => expect(screen.getByTestId('lease-countdown').textContent).toBe('11m 00s'));
    expect(screen.getByTestId('lease-countdown').getAttribute('data-state')).toBe('remaining');
  });

  it('extends the countdown on task.checkpoint through one targeted refetch (no list refetch)', async () => {
    const { calls, streams, rows } = setupLeaseView({ tasks: [leaseTask()] });
    const countdown = await screen.findByTestId('lease-countdown');
    expect(countdown.textContent).toBe('10m 00s');

    // Server extended the lease on the checkpoint; the event data does not
    // carry the new deadline (Section 9.6), so the join refetches the row.
    rows.set('PID00001-T001', leaseTask({ lease_expires_at: iso(20), last_checkpoint_at: iso(0) }));
    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'task.checkpoint',
        task_id: 'PID00001-T001',
        occurred_at: iso(0),
        actor: { type: 'agent', ref: 'sess-1' },
        data: {
          checkpoint_id: 'CHK-1',
          attempt_number: 1,
          kind: 'progress',
          percent: 50,
          session_id: 'sess-1',
          message: 'halfway',
          token_usage: null,
        },
      }),
    );

    await waitFor(() => expect(screen.getByTestId('lease-countdown').textContent).toBe('20m 00s'));
    const taskRowFetches = calls.filter((call) => /^\/api\/v1\/tasks\//.test(call.pathname));
    expect(taskRowFetches).toHaveLength(1);
    expect(
      calls.filter((call) => call.pathname === '/api/v1/projects/PID00001/tasks'),
    ).toHaveLength(1);
  });

  it('warns at the computed 80%-of-lease threshold (Section 9.6)', async () => {
    setupLeaseView({
      tasks: [leaseTask({ lease_acquired_at: iso(-36), lease_expires_at: iso(9) })],
    });
    const countdown = await screen.findByTestId('lease-countdown');
    expect(countdown.textContent).toBe('9m 00s');
    expect(countdown.getAttribute('data-state')).toBe('warning');
  });

  it('warns on the task.lease_expiring push and re-arms the deadline from its server field', async () => {
    const { streams } = setupLeaseView({
      tasks: [leaseTask({ lease_acquired_at: iso(-10), lease_expires_at: iso(40) })],
    });
    const countdown = await screen.findByTestId('lease-countdown');
    expect(countdown.getAttribute('data-state')).toBe('remaining');
    expect(countdown.textContent).toBe('40m 00s');

    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'task.lease_expiring',
        task_id: 'PID00001-T001',
        occurred_at: iso(0),
        actor: { type: 'system', ref: 'lease-notifier' },
        data: {
          task_id: 'PID00001-T001',
          lease_generation: 1,
          lease_expires_at: iso(5),
        },
      }),
    );

    const warned = await screen.findByTestId('lease-countdown');
    await waitFor(() => expect(warned.getAttribute('data-state')).toBe('warning'));
    expect(warned.textContent).toBe('5m 00s');
  });

  it('clears the countdown when the lease ends (expired/released — Section 9.6)', async () => {
    const { streams } = setupLeaseView({ tasks: [leaseTask()] });
    await screen.findByTestId('lease-countdown');

    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'task.lease_expired',
        task_id: 'PID00001-T001',
        occurred_at: iso(10),
        actor: { type: 'system', ref: 'lease-sweeper' },
        data: {
          from_state: 'in_progress',
          to_state: 'pending',
          reason_code: 'lease_expired',
          task_version: 3,
        },
      }),
    );

    await waitFor(() => expect(screen.queryByTestId('lease-countdown')).toBeNull());
    expect(screen.getByTestId('session-ended-row')).toBeTruthy();
  });
});
