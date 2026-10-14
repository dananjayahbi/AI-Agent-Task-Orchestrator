/**
 * MT-4.9-01 — Agents panel session list (Section 13.1 "Live sessions,
 * current leases"; Section 9.6 envelope; Section 9.2 Session fields).
 *
 * The Owner-facing contract has no `GET /agent-sessions`, so the panel
 * derives rows from canonical lease state + `GET /events` history and
 * keeps them fresh **over the stream** (AC 2: updates arrive as events,
 * never as a poll). These tests pin: fixture derivation, active/ended
 * separation, the claim join through one targeted single-task refetch,
 * pure release patching (replay-safe), the session lifecycle events, the
 * separated states, and the panel's project selection.
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AgentsPanel } from '@/components/panels/agents-panel';
import { SessionsView } from '@/components/panels/sessions-view';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makeEventEnvelope,
  makeProject,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
  tasksServerRoute,
  type SseConnection,
} from '../helpers/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

beforeEach(() => {
  window.localStorage.clear();
});

const EVENTS_PATH = '/api/v1/events';

type RecordedCall = { method: string; pathname: string; search: string };

type SessionsFixture = {
  calls: RecordedCall[];
  streams: SseConnection[];
  rows: Map<string, unknown>;
};

function setup(options: {
  tasks?: unknown[];
  events?: unknown[];
  tasksError?: boolean;
}): SessionsFixture {
  const { tasks = [], events = [], tasksError = false } = options;
  const streams: SseConnection[] = [];
  const rows = new Map<string, unknown>(tasks.map((task) => [(task as { id: string }).id, task]));
  const { calls } = installApi([
    tasksError
      ? {
          method: 'GET',
          match: /\/api\/v1\/projects\/PID00001\/tasks(\?|$)/,
          respond: () => errorResponse('SERVER_ERROR', 500),
        }
      : tasksServerRoute('PID00001', tasks),
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

const listCalls = (calls: RecordedCall[]) =>
  calls.filter((call) => call.pathname === '/api/v1/projects/PID00001/tasks');
const taskRowCalls = (calls: RecordedCall[]) =>
  calls.filter((call) => /^\/api\/v1\/tasks\//.test(call.pathname));
const eventsCalls = (calls: RecordedCall[]) =>
  calls.filter((call) => call.pathname === EVENTS_PATH);

const heldTask = makeTask({
  id: 'PID00001-T001',
  title: 'Implement login form',
  state: 'in_progress',
  worker_agent_id: 'coder-1',
  worker_session_id: 'sess-1',
  claimed_role: 'coder',
  lease_acquired_at: '2026-10-01T09:00:00Z',
  lease_expires_at: '2026-10-01T09:45:00Z',
  last_checkpoint_at: '2026-10-01T09:20:00Z',
});

describe('Agents panel sessions (MT-4.9-01)', () => {
  it('renders an active session from canonical lease state with its task/lease join and Section 9.2 fields', async () => {
    const { calls } = setup({ tasks: [heldTask] });

    const row = await screen.findByTestId('session-row');
    expect(row.getAttribute('data-session-id')).toBe('sess-1');
    expect(within(row).getByText('coder-1')).toBeTruthy();
    expect(within(row).getByText('PID00001-T001')).toBeTruthy();
    expect(within(row).getByText('Implement login form')).toBeTruthy();
    expect(within(row).getByText('coder')).toBeTruthy();

    // Section 9.2 fields with the documented contract gap: client_name /
    // capability / transport have no Owner-facing read source yet → "–".
    expect(within(row).getByText('Client')).toBeTruthy();
    expect(within(row).getByText('Capability')).toBeTruthy();
    expect(within(row).getByText('Transport')).toBeTruthy();
    expect(within(row).getAllByText('–').length).toBe(3);
    expect(within(row).getByText(/Started/)).toBeTruthy();
    expect(within(row).getByText(new Date('2026-10-01T09:20:00Z').toLocaleString())).toBeTruthy();

    // Both contract sources were read once each: lease tasks + history.
    expect(listCalls(calls)).toHaveLength(1);
    expect(eventsCalls(calls)).toHaveLength(1);
  });

  it('separates a recently ended session (history claim → release) into the ended section', async () => {
    setup({
      events: [
        makeEventEnvelope({
          id: 1,
          type: 'task.claimed',
          task_id: 'PID00001-T001',
          occurred_at: '2026-10-01T09:00:00Z',
          actor: { type: 'agent', ref: 'sess-9' },
          data: {
            from_state: 'pending',
            to_state: 'in_progress',
            reason_code: 'claim',
            task_version: 2,
          },
        }),
        makeEventEnvelope({
          id: 2,
          type: 'task.released',
          task_id: 'PID00001-T001',
          occurred_at: '2026-10-01T10:00:00Z',
          actor: { type: 'agent', ref: 'sess-9' },
          data: {
            from_state: 'in_progress',
            to_state: 'pending',
            reason_code: 'voluntary_release',
            task_version: 3,
          },
        }),
      ],
    });

    const endedRow = await screen.findByTestId('session-ended-row');
    expect(endedRow.getAttribute('data-session-id')).toBe('sess-9');
    expect(screen.queryByTestId('session-row')).toBeNull();
    // Badge + "Ended" field label both render on an ended row.
    expect(within(endedRow).getAllByText('Ended')).toHaveLength(2);
    expect(
      within(endedRow).getByText(new Date('2026-10-01T10:00:00Z').toLocaleString()),
    ).toBeTruthy();
    // Lease-derived end: no join lingers on an ended row.
    expect(within(endedRow).queryByTestId('session-lease')).toBeNull();
  });

  it('applies agent.session_started and agent.session_ended live over the stream', async () => {
    const { streams } = setup({ tasks: [], events: [] });
    await waitFor(() => expect(screen.getByText('No active sessions')).toBeTruthy());

    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'agent.session_started',
        task_id: null,
        occurred_at: '2026-10-01T11:00:00Z',
        actor: { type: 'agent', ref: 'sess-2' },
        data: {
          session_id: 'sess-2',
          agent_label: 'auditor-1',
          client_name: 'bridge-cli',
          capability: 'audit',
          transport: 'sse',
          started_at: '2026-10-01T11:00:00Z',
        },
      }),
    );

    const active = await screen.findByTestId('session-row');
    expect(active.getAttribute('data-session-id')).toBe('sess-2');
    expect(within(active).getByText('auditor-1')).toBeTruthy();
    expect(within(active).getByText('bridge-cli')).toBeTruthy();

    streams[0].frame(
      3,
      makeEventEnvelope({
        id: 3,
        type: 'agent.session_ended',
        task_id: null,
        occurred_at: '2026-10-01T11:30:00Z',
        actor: { type: 'agent', ref: 'sess-2' },
        data: { session_id: 'sess-2', ended_at: '2026-10-01T11:30:00Z' },
      }),
    );

    const ended = await screen.findByTestId('session-ended-row');
    expect(ended.getAttribute('data-session-id')).toBe('sess-2');
    await waitFor(() => expect(screen.getByText('No active sessions')).toBeTruthy());
  });

  it('attaches a claim through one single-task refetch — never a list refetch (risk note)', async () => {
    const claimed = makeTask({
      id: 'PID00001-T002',
      title: 'Wire the login API',
      state: 'in_progress',
      worker_agent_id: 'coder-2',
      worker_session_id: 'sess-3',
      claimed_role: 'coder',
      lease_acquired_at: '2026-10-01T11:00:00Z',
      lease_expires_at: '2026-10-01T11:45:00Z',
      last_checkpoint_at: null,
    });
    const { calls, streams, rows } = setup({ tasks: [] });
    rows.set('PID00001-T002', claimed);
    await waitFor(() => expect(screen.getByText('No active sessions')).toBeTruthy());

    streams[0].frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'task.claimed',
        task_id: 'PID00001-T002',
        occurred_at: '2026-10-01T11:00:00Z',
        actor: { type: 'agent', ref: 'sess-3' },
        data: {
          from_state: 'pending',
          to_state: 'in_progress',
          reason_code: 'claim',
          task_version: 2,
        },
      }),
    );

    const row = await screen.findByTestId('session-row');
    expect(row.getAttribute('data-session-id')).toBe('sess-3');
    const lease = within(row).getByTestId('session-lease');
    expect(within(lease).getByText('PID00001-T002')).toBeTruthy();

    // The claim data carries no worker columns (Section 9.6): exactly one
    // targeted GET /tasks/{id}; the session list is never refetched.
    await waitFor(() => expect(taskRowCalls(calls)).toHaveLength(1));
    expect(listCalls(calls)).toHaveLength(1);
  });

  it('detaches a released lease with a pure patch and stays correct under a replayed frame', async () => {
    const { calls, streams } = setup({ tasks: [heldTask] });
    await waitFor(() => expect(screen.getByTestId('session-row')).toBeTruthy());

    const release = makeEventEnvelope({
      id: 2,
      type: 'task.released',
      task_id: 'PID00001-T001',
      occurred_at: '2026-10-01T10:00:00Z',
      actor: { type: 'agent', ref: 'sess-1' },
      data: {
        from_state: 'in_progress',
        to_state: 'pending',
        reason_code: 'voluntary_release',
        task_version: 3,
      },
    });
    streams[0].frame(2, release);
    // Reconnect replay: the same envelope again (Section 9.6 resume).
    streams[0].frame(2, release);

    const endedRow = await screen.findByTestId('session-ended-row');
    expect(endedRow.getAttribute('data-session-id')).toBe('sess-1');
    await waitFor(() => expect(screen.queryByTestId('session-row')).toBeNull());
    expect(screen.getAllByTestId('session-ended-row')).toHaveLength(1);

    // Pure patch: no refetch of any kind, and the panel still never polls.
    expect(taskRowCalls(calls)).toHaveLength(0);
    expect(listCalls(calls)).toHaveLength(1);
    expect(eventsCalls(calls)).toHaveLength(1);
  });

  it('shows the separated empty states when the project has no sessions', async () => {
    setup({ tasks: [], events: [] });

    expect(await screen.findByText('No active sessions')).toBeTruthy();
    expect(screen.getByText('No recently ended sessions.')).toBeTruthy();
  });

  it('renders catalog copy (never raw server text) when a session source fails', async () => {
    setup({ tasksError: true });

    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('Something went wrong');
    expect(alert.textContent).toContain('Reference ID: corr-test');
  });

  it('selects the project context: first project by default, switching remounts the sessions view', async () => {
    const streams: SseConnection[] = [];
    const betaTask = makeTask({
      id: 'PID00002-T001',
      project_id: 'PID00002',
      title: 'Beta work',
      state: 'in_progress',
      worker_agent_id: 'coder-beta',
      worker_session_id: 'sess-beta',
      claimed_role: 'coder',
      lease_acquired_at: '2026-10-01T12:00:00Z',
      lease_expires_at: '2026-10-01T12:45:00Z',
      last_checkpoint_at: null,
    });
    const { calls } = installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects(\?|$)/,
        respond: () =>
          jsonResponse(
            pageOf([
              makeProject({ id: 'PID00001', name: 'Alpha' }),
              makeProject({ id: 'PID00002', name: 'Beta' }),
            ]),
          ),
      },
      tasksServerRoute('PID00001', []),
      tasksServerRoute('PID00002', [betaTask]),
      {
        method: 'GET',
        match: /\/api\/v1\/events(\?|$)/,
        respond: () => jsonResponse(pageOf([])),
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
    renderWithQueryClient(<AgentsPanel />);

    const select = (await screen.findByTestId('agents-project-select')) as HTMLSelectElement;
    await waitFor(() => expect(select.value).toBe('PID00001'));
    await waitFor(() =>
      expect(
        calls.some(
          (call) =>
            call.pathname === '/api/v1/projects/PID00001/tasks' &&
            call.search.includes('state=in_progress'),
        ),
      ).toBe(true),
    );
    expect(window.localStorage.getItem('orchestrator.web.current-project')).toBe('PID00001');
    expect(await screen.findByText('No active sessions')).toBeTruthy();

    fireEvent.change(select, { target: { value: 'PID00002' } });

    const betaRow = await screen.findByTestId('session-row');
    expect(betaRow.getAttribute('data-session-id')).toBe('sess-beta');
    expect(within(betaRow).getByText('coder-beta')).toBeTruthy();
    expect(window.localStorage.getItem('orchestrator.web.current-project')).toBe('PID00002');
    await waitFor(() =>
      expect(calls.some((call) => call.pathname === '/api/v1/projects/PID00002/tasks')).toBe(true),
    );
    // The project switch opened a second stream for the new context.
    await waitFor(() => expect(streams.length).toBeGreaterThanOrEqual(2));
  });
});
