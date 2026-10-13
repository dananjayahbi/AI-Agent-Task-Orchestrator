/**
 * MT-4.6-01 — task detail layout: all seven Section 13.1 blocks, distinct
 * loading/error states, catalog-only error copy (Section 20.4 item 5),
 * missing-id handling, `version` for optimistic locking (Section 8.2 rule 3),
 * and the board → detail → board round trip that preserves cached board
 * state (Section 13.3 cache discipline).
 */
import { screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import { TaskDetail } from '@/components/task/detail/task-detail';
import { defaultServerFilters } from '@/lib/board/filters';
import { queryKeys } from '@/lib/queries/keys';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makePolicy,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
  tasksServerRoute,
  type Route,
} from '../helpers/api';
import { makeAttachment, makeCheckpoint } from '../helpers/task-detail';

afterEach(() => {
  vi.unstubAllGlobals();
});

const PID = 'PID00001';
const TASK_ID = 'PID00001-T001';

/** Standard detail-view routes; `taskRoute` can be overridden per test. */
function detailRoutes(
  options: { taskRoute?: Route; attachments?: unknown[]; checkpoints?: unknown[] } = {},
): Route[] {
  return [
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/checkpoints(\?|$)/,
      respond: () => jsonResponse(pageOf(options.checkpoints ?? [])),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/attachments(\?|$)/,
      respond: () => jsonResponse(pageOf(options.attachments ?? [])),
    },
    options.taskRoute ?? {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
      respond: () => jsonResponse(makeTask()),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/events\/stream(\?|$)/,
      respond: () => sseConnection().response,
    },
  ];
}

describe('TaskDetail (MT-4.6-01)', () => {
  it('renders all seven Section 13.1 blocks from fixture data with version surfaced', async () => {
    installApi(
      detailRoutes({
        taskRoute: {
          method: 'GET',
          match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
          respond: () =>
            jsonResponse(
              makeTask({
                version: 7,
                title: 'Implement login form',
                description: 'Build the login form with **client validation**.',
                acceptance_criteria: ['Validates email format', 'Shows server errors inline'],
                target_scope: ['web/**', 'backend/apps/accounts/**'],
                test_command: 'npm test',
                priority: 'high',
                state: 'in_progress',
                worker_agent_id: 'claude-code-session-9',
                latest_feedback: 'Narrow the scope to web only.',
              }),
            ),
        },
        checkpoints: [makeCheckpoint()],
        attachments: [makeAttachment()],
      }),
    );

    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);

    await waitFor(() => expect(screen.getByTestId('task-detail')).toBeTruthy());
    // Header facts (Section 7.2).
    expect(screen.getByTestId('task-detail-id').textContent).toBe(TASK_ID);
    expect(screen.getByTestId('task-detail-title').textContent).toBe('Implement login form');
    expect(screen.getByTestId('priority-chip-high')).toBeTruthy();
    expect(screen.getByTestId('task-detail-state').textContent).toBe('In progress');
    expect(screen.getByTestId('task-detail-worker').textContent).toContain('claude-code-session-9');
    // Optimistic-locking input surfaced for child views (Section 8.2 rule 3).
    expect(screen.getByTestId('task-detail').getAttribute('data-task-version')).toBe('7');
    // Back link to the board.
    expect(screen.getByTestId('task-detail-back').getAttribute('href')).toBe(
      `/projects/${PID}/board`,
    );
    // latest_feedback visible when present (WP-3.6 field, Section 7.2).
    expect(screen.getByTestId('task-detail-feedback').textContent).toContain(
      'Narrow the scope to web only.',
    );
    // Row-driven blocks.
    expect(screen.getByTestId('task-detail-section-description')).toBeTruthy();
    expect(screen.getByTestId('task-detail-criteria-list').textContent).toContain(
      'Validates email format',
    );
    expect(screen.getByTestId('task-detail-scope-list').textContent).toContain('web/**');
    expect(screen.getByTestId('task-detail-test-command').textContent).toBe('npm test');
    // Block regions owned by MT-4.6-02/03/04 (each block loads its own data).
    expect(screen.getByTestId('task-detail-section-attachments')).toBeTruthy();
    await waitFor(() => expect(screen.getByTestId('attachment-row')).toBeTruthy());
    expect(screen.getByTestId('task-detail-section-checkpoints')).toBeTruthy();
    await waitFor(() => expect(screen.getByTestId('checkpoint-row')).toBeTruthy());
    expect(screen.getByTestId('task-detail-section-resolutions')).toBeTruthy();
    expect(screen.getByTestId('task-detail-section-transitions')).toBeTruthy();
  });

  it('shows the empty-state variants for criteria and scope when the task has none', async () => {
    installApi(detailRoutes());
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getByTestId('task-detail')).toBeTruthy());
    expect(screen.getByTestId('task-detail-criteria-empty')).toBeTruthy();
    expect(screen.getByTestId('task-detail-scope-empty')).toBeTruthy();
  });

  it('renders a distinct loading state while the task row is pending', async () => {
    installApi(
      detailRoutes({
        taskRoute: {
          method: 'GET',
          match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
          // Never resolves — the loading state must be visible meanwhile.
          respond: () => new Promise<Response>(() => {}),
        },
      }),
    );
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
    expect(screen.getByText('Loading task…')).toBeTruthy();
  });

  it('maps TASK_NOT_FOUND to the catalog copy with the reference id — never raw server text', async () => {
    installApi(
      detailRoutes({
        taskRoute: {
          method: 'GET',
          match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
          respond: () => errorResponse('TASK_NOT_FOUND', 404, 'secret backend text'),
        },
      }),
    );
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toContain('Task not found');
    expect(alert.textContent).toContain('This task does not exist or has been removed.');
    expect(alert.textContent).toContain('Reference ID: corr-test');
    expect(alert.textContent).not.toContain('secret backend text');
    expect(screen.getByText('Try again')).toBeTruthy();
  });

  it('maps SERVER_ERROR to the generic catalog entry', async () => {
    installApi(
      detailRoutes({
        taskRoute: {
          method: 'GET',
          match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
          respond: () => errorResponse('SERVER_ERROR', 500),
        },
      }),
    );
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.getByRole('alert').textContent).toContain('Something went wrong');
  });

  it('renders not-found for a blank task id without firing a request', async () => {
    const { calls } = installApi(detailRoutes());
    renderWithQueryClient(<TaskDetail pid={PID} taskId="" />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.getByRole('alert').textContent).toContain('Task not found');
    expect(calls.filter((call) => call.pathname.startsWith('/api/v1/tasks/'))).toHaveLength(0);
  });

  it('links the board card into the detail route and keeps board cache across the round trip', async () => {
    const task = makeTask({ id: TASK_ID, title: 'Implement login form' });
    installApi([
      tasksServerRoute(PID, [task]),
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/policy(\?|$)/,
        respond: () => jsonResponse(makePolicy()),
      },
      ...detailRoutes(),
    ]);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    // Board renders the card; its title is a real anchor into the detail route.
    const boardView = render(
      <QueryClientProvider client={queryClient}>
        <Board pid={PID} />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('task-card')).toBeTruthy());
    const titleLink = screen.getByTestId('task-card-title').querySelector('a');
    expect(titleLink).toBeTruthy();
    expect(titleLink?.getAttribute('href')).toBe(`/projects/${PID}/tasks/${TASK_ID}`);
    boardView.unmount();

    // Detail view shares the same query client (app layout does this in prod).
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />, { queryClient });
    await waitFor(() => expect(screen.getByTestId('task-detail')).toBeTruthy());

    // Section 13.3: the board list cache entry survives the detour.
    expect(
      queryClient.getQueryData(queryKeys.boardTasks(PID, defaultServerFilters())),
    ).toBeDefined();
  });
});
