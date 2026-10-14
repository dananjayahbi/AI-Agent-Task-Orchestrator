/**
 * Cross-project review queue (MT-4.8-01; `npm test -- -t "review queue"`).
 *
 * Section 13.1: rows from **all** projects (with the dashboard-count
 * prefilter — projects with zero review rows are never requested),
 * sorted age-first with the canonical priority order as tiebreak
 * (recorded in `lib/review/queue.ts`), each row carrying project, task
 * id, title, priority chip, the verbatim Section 8.4 reason with a
 * friendly label, age since escalation and a navigation action into the
 * task detail (WP-4.6 contract). Live: `review.requested` adds a row
 * (targeted `GET /tasks/{id}`), transitions out of `in_human_review`
 * remove rows (Sections 9.6, 13.3). Loading / empty / error states are
 * distinct (Section 20.3, catalog-only copy).
 */
import { waitFor, within, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ReviewQueue } from '@/components/review/review-queue';
import type { Task } from '@/lib/api/generated/types.gen';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makeEventEnvelope,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
} from '../helpers/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

function dashboardSummary(counts: Record<string, number>) {
  return {
    projects: Object.entries(counts).map(([pid, reviewCount]) => ({
      project_id: pid,
      name: `Project ${pid}`,
      state_counts: {
        draft: 0,
        pending: 0,
        in_progress: 0,
        to_be_audited: 0,
        in_human_review: reviewCount,
        completed: 0,
      },
      velocity: 0,
      active_agents: 0,
    })),
  };
}

function setup(options: {
  counts: Record<string, number>;
  tasksByPid: Record<string, unknown[]>;
  singleTasks?: Record<string, unknown>;
  fail?: boolean;
}) {
  const conn = sseConnection();
  const { calls } = installApi([
    {
      method: 'GET',
      match: /\/api\/v1\/dashboard\/summary(\?|$)/,
      respond: () =>
        options.fail === true
          ? errorResponse('SERVER_ERROR', 500)
          : jsonResponse(dashboardSummary(options.counts)),
    },
    ...Object.entries(options.tasksByPid).map(([pid, tasks]) => ({
      method: 'GET',
      match: new RegExp(`/api/v1/projects/${pid}/tasks(\\?|$)`),
      respond: ({ search }: { search: string }) => {
        expect(search).toContain('state=in_human_review'); // contract filter
        return jsonResponse(pageOf(tasks));
      },
    })),
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
      respond: ({ pathname }: { pathname: string }) => {
        const taskId = pathname.split('/').pop() ?? '';
        const row = options.singleTasks?.[taskId];
        return row === undefined ? errorResponse('TASK_NOT_FOUND', 404) : jsonResponse(row);
      },
    },
    {
      method: 'GET',
      match: /\/api\/v1\/events\/stream(\?|$)/,
      respond: () => conn.response,
    },
  ]);
  const view = renderWithQueryClient(<ReviewQueue />);
  return { calls, stream: conn, ...view };
}

function rowIds(): string[] {
  return screen
    .getAllByTestId('review-queue-row')
    .map((row) => row.getAttribute('data-task-id') ?? '');
}

const REVIEW_ROW = (overrides: Partial<Task> = {}): Task =>
  makeTask({ state: 'in_human_review', review_reason: 'test_failure', ...overrides });

describe('review queue (MT-4.8-01)', () => {
  it('lists in_human_review tasks across projects, sorted age-first with priority tiebreak', async () => {
    const { calls } = setup({
      counts: { PID00001: 2, PID00002: 1, PID00003: 0 },
      tasksByPid: {
        PID00001: [
          REVIEW_ROW({
            id: 'PID00001-T001',
            title: 'Older low task',
            priority: 'low',
            updated_at: '2026-10-01T09:00:00Z',
          }),
          REVIEW_ROW({
            id: 'PID00001-T002',
            title: 'Newer medium task',
            priority: 'medium',
            updated_at: '2026-10-01T10:00:00Z',
          }),
        ],
        PID00002: [
          REVIEW_ROW({
            id: 'PID00002-T004',
            project_id: 'PID00002',
            title: 'Urgent peer',
            priority: 'urgent',
            review_reason: 'sensitive_config_changed',
            updated_at: '2026-10-01T10:00:00Z', // same instant as T002 → priority breaks it
          }),
        ],
      },
    });

    await waitFor(() => expect(rowIds()).toHaveLength(3));
    // Age first (oldest waiting on top), priority tiebreak, deterministic.
    expect(rowIds()).toEqual(['PID00001-T001', 'PID00002-T004', 'PID00001-T002']);

    const first = screen.getAllByTestId('review-queue-row')[0];
    expect(within(first).getByTestId('review-queue-project').textContent).toBe('PID00001');
    expect(first.textContent).toContain('Older low task');
    expect(within(first).getByTestId('priority-chip-low')).toBeTruthy();
    // Friendly label + the canonical code verbatim (Section 8.4 / 20.5).
    expect(within(first).getByTestId('review-queue-reason').textContent).toContain('Tests failed');
    expect(within(first).getByTestId('review-queue-reason').textContent).toContain('test_failure');
    expect(within(first).getByTestId('review-queue-age').textContent).toContain('waiting');
    // Entry action navigates into the task detail (WP-4.6 contract).
    expect(within(first).getByTestId('review-queue-open-PID00001-T001').getAttribute('href')).toBe(
      '/projects/PID00001/tasks/PID00001-T001',
    );

    // The prefilter means zero-count projects are never requested.
    expect(screen.queryByText(/PID00003/)).toBeNull();
    expect(calls.filter((call) => call.pathname.includes('PID00003'))).toHaveLength(0);
  });

  it('live-adds a row on review.requested and removes it when a decision resolves it', async () => {
    const { calls, stream } = setup({
      counts: { PID00001: 1 },
      tasksByPid: {
        PID00001: [REVIEW_ROW({ id: 'PID00001-T001', updated_at: '2026-10-01T09:00:00Z' })],
      },
      singleTasks: {
        'PID00002-T007': REVIEW_ROW({
          id: 'PID00002-T007',
          project_id: 'PID00002',
          title: 'Escalated elsewhere',
          updated_at: '2026-10-01T11:00:00Z',
        }),
      },
    });
    await waitFor(() => expect(rowIds()).toEqual(['PID00001-T001']));

    // review.requested adds the row (payload carries no row — one GET).
    stream.frame(
      2,
      makeEventEnvelope({
        id: 2,
        type: 'review.requested',
        project_id: 'PID00002',
        task_id: 'PID00002-T007',
        data: { review_reason: 'scope_violation', task_version: 4 },
      }),
    );
    await waitFor(() => expect(rowIds()).toContain('PID00002-T007'));
    expect(
      calls.filter(
        (call) => call.method === 'GET' && call.pathname === '/api/v1/tasks/PID00002-T007',
      ),
    ).toHaveLength(1); // targeted, deduplicated

    // A transition out of in_human_review removes the row (no network).
    const before = calls.length;
    stream.frame(
      3,
      makeEventEnvelope({
        id: 3,
        type: 'review.decided',
        project_id: 'PID00001',
        task_id: 'PID00001-T001',
        data: {
          from_state: 'in_human_review',
          to_state: 'pending',
          reason_code: 'request_changes',
          task_version: 9,
        },
      }),
    );
    await waitFor(() => expect(rowIds()).toEqual(['PID00002-T007']));
    expect(calls.length).toBe(before); // removal is a pure cache write
  });

  it('renders the empty state when nothing awaits review', async () => {
    setup({ counts: { PID00001: 0 }, tasksByPid: {} });
    await waitFor(() => expect(screen.getByText('Nothing to review')).toBeTruthy());
  });

  it('maps listing failures to catalog copy with a retry (Section 20.4 item 5)', async () => {
    setup({ counts: {}, tasksByPid: {}, fail: true });
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('Something went wrong');
    expect(screen.getByRole('button', { name: /try again/i })).toBeTruthy();
  });

  it('keeps rows readable with a visible status while the stream reconnects (Section 13.3)', async () => {
    const { stream } = setup({
      counts: { PID00001: 1 },
      tasksByPid: {
        PID00001: [REVIEW_ROW({ id: 'PID00001-T001', updated_at: '2026-10-01T09:00:00Z' })],
      },
    });
    await waitFor(() => expect(rowIds()).toEqual(['PID00001-T001']));

    // Reach the visible "Live" state, then lose the stream.
    stream.frame(
      2,
      makeEventEnvelope({ id: 2, type: 'system.alert', project_id: 'PID00001', task_id: null }),
    );
    await waitFor(() =>
      expect(screen.getByTestId('stream-status').getAttribute('data-status')).toBe('open'),
    );
    stream.fail();
    // The hook flips to `reconnecting` after its first backoff tick
    // (default 1 s base — Section 13.3 visible status).
    await waitFor(
      () =>
        expect(screen.getByTestId('stream-status').getAttribute('data-status')).not.toBe('open'),
      { timeout: 2500 },
    );
    expect(rowIds()).toEqual(['PID00001-T001']); // rows stay on screen
  });
});
