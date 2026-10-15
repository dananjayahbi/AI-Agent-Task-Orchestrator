/**
 * MT-4.8-04 — merge-status display (Section 8.1 sub-status cycle;
 * Section 7.2 canonical values; ADR-010 label/value separation):
 *
 *  - one shared badge across the review panel, the detail header
 *    (post-review: merged lands there after T17), the queue row and
 *    the board card — canonical `merge_status` on `data-merge-status`,
 *    Section 8.1's verbatim "approved, merging" for the merging phase;
 *  - the live cycle driven by SSE merge.* events through targeted
 *    refetches (WP-4.3 pattern) on the detail page and the queue;
 *  - reconnect reconciliation: the badge catches up from the frame the
 *    resumed connection replays (Last-Event-ID resume itself is
 *    MT-1.10's proven contract);
 *  - the T18 conflict branch and the manual-strategy approve that
 *    lands completed/merged straight from the response — no phantom
 *    "merging" client-side (OQ-06).
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ReviewQueue } from '@/components/review/review-queue';
import { TaskCard } from '@/components/board/task-card';
import { TaskDetail } from '@/components/task/detail/task-detail';
import {
  installApi,
  jsonResponse,
  makeEventEnvelope,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
  type SseConnection,
} from '../helpers/api';
import { makeAuditReport, makeResolution } from '../helpers/task-detail';

afterEach(() => {
  vi.unstubAllGlobals();
});

const PID = 'PID00001';
const TASK_ID = 'PID00001-T001';
const NOW = Date.parse('2026-10-01T10:00:00Z');

const reviewRow = (overrides: Partial<ReturnType<typeof makeTask>> = {}) =>
  makeTask({
    state: 'in_human_review',
    review_reason: 'test_failure',
    merge_status: 'pending',
    version: 4,
    ...overrides,
  });

/** TaskDetail routes with a mutable row + captured SSE connections. */
function detailHarness(options: { taskRow?: unknown; reviewResponse?: unknown } = {}) {
  let currentRow: unknown = options.taskRow ?? reviewRow();
  const connections: SseConnection[] = [];
  installApi([
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/resolutions(\?|$)/,
      respond: () => jsonResponse(pageOf([makeResolution()])),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/audit-reports(\?|$)/,
      respond: () => jsonResponse(pageOf([makeAuditReport()])),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/attachments(\?|$)/,
      respond: () => jsonResponse(pageOf([])),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/checkpoints(\?|$)/,
      respond: () => jsonResponse(pageOf([])),
    },
    {
      method: 'POST',
      match: /\/api\/v1\/tasks\/[^/]+\/review$/,
      respond: () => jsonResponse(options.reviewResponse ?? {}),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
      respond: () => jsonResponse(currentRow),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/events\/stream(\?|$)/,
      respond: () => {
        const connection = sseConnection();
        connections.push(connection);
        return connection.response;
      },
    },
  ]);
  return {
    connections,
    setTaskRow: (row: unknown) => {
      currentRow = row;
    },
  };
}

async function waitForApproveReady() {
  await waitFor(() =>
    expect((screen.getByTestId('review-approve-open') as HTMLButtonElement).disabled).toBe(false),
  );
}

describe('merge-status display (MT-4.8-04)', () => {
  it('cycles pending → merging → merged across the panel and the detail header', async () => {
    const harness = detailHarness();
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);

    // Pending seed: the panel hosts the badge while the task is in review.
    await waitFor(() =>
      expect(screen.getByTestId('review-merge-badge').getAttribute('data-merge-status')).toBe(
        'pending',
      ),
    );
    expect(screen.getByTestId('review-merge-badge').textContent).toBe('approved, waiting');
    expect(screen.queryByTestId('task-detail-merge-badge')).toBeNull();

    // merge.started → the executor is working.
    harness.setTaskRow(reviewRow({ merge_status: 'merging', version: 5 }));
    harness.connections[0]?.frame(1, makeEventEnvelope({ id: 1, type: 'merge.started' }));
    await waitFor(() =>
      expect(screen.getByTestId('review-merge-badge').getAttribute('data-merge-status')).toBe(
        'merging',
      ),
    );
    expect(screen.getByTestId('review-merge-badge').textContent).toBe('approved, merging');

    // merge.succeeded + the T17 transition: completed / merged. The
    // panel (a review-state surface) goes; the header carries the badge.
    harness.setTaskRow(
      makeTask({ state: 'completed', review_reason: null, merge_status: 'merged', version: 6 }),
    );
    harness.connections[0]?.frame(2, makeEventEnvelope({ id: 2, type: 'merge.succeeded' }));
    harness.connections[0]?.frame(3, makeEventEnvelope({ id: 3, type: 'task.transitioned' }));
    await waitFor(() => expect(screen.queryByTestId('review-panel')).toBeNull());
    const badge = screen.getByTestId('task-detail-merge-badge');
    expect(badge.getAttribute('data-merge-status')).toBe('merged');
    expect(badge.textContent).toBe('merged');
    expect(screen.getByTestId('task-detail-state').textContent).toBe('Completed');
  });

  it('shows the T18 conflict branch on the panel with the merge_conflict reason', async () => {
    const harness = detailHarness({ taskRow: reviewRow({ merge_status: 'merging' }) });
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId('review-merge-badge').getAttribute('data-merge-status')).toBe(
        'merging',
      ),
    );

    harness.setTaskRow(
      reviewRow({ merge_status: 'conflict', review_reason: 'merge_conflict', version: 5 }),
    );
    harness.connections[0]?.frame(1, makeEventEnvelope({ id: 1, type: 'merge.failed' }));

    await waitFor(() =>
      expect(screen.getByTestId('review-merge-badge').getAttribute('data-merge-status')).toBe(
        'conflict',
      ),
    );
    expect(screen.getByTestId('review-merge-badge').textContent).toBe('merge conflict');
    expect(screen.getByTestId('review-reason-item').textContent).toContain('(merge_conflict)');
    // The panel keeps hosting the actions — the reviewer can decide again.
    await waitForApproveReady();
  });

  it('catches up after a dropped stream: the replayed frame lands on the new connection', async () => {
    const harness = detailHarness();
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId('review-merge-badge').getAttribute('data-merge-status')).toBe(
        'pending',
      ),
    );

    // The merge finishes while the stream is down; the row settles.
    harness.setTaskRow(
      makeTask({ state: 'completed', review_reason: null, merge_status: 'merged', version: 6 }),
    );
    harness.connections[0]?.fail(new Error('connection reset'));

    // The hook reconnects (Last-Event-ID resume is its MT-1.10 contract);
    // the replayed merge event must still move the badge.
    await waitFor(() => expect(harness.connections).toHaveLength(2), { timeout: 4000 });
    harness.connections[1]?.frame(7, makeEventEnvelope({ id: 7, type: 'merge.succeeded' }));
    await waitFor(() => expect(screen.queryByTestId('review-panel')).toBeNull(), {
      timeout: 4000,
    });
    expect(screen.getByTestId('task-detail-merge-badge').getAttribute('data-merge-status')).toBe(
      'merged',
    );
  });

  it('tracks the queue row badge live and drops the row when review ends', async () => {
    let singleTask: unknown = reviewRow({ updated_at: '2026-10-01T09:00:00Z' });
    const conn = sseConnection();
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/dashboard\/summary(\?|$)/,
        respond: () =>
          jsonResponse({
            projects: [
              {
                project_id: PID,
                name: 'Project',
                state_counts: {
                  draft: 0,
                  pending: 0,
                  in_progress: 0,
                  to_be_audited: 0,
                  in_human_review: 1,
                  completed: 0,
                },
                velocity: 0,
                active_agents: 0,
              },
            ],
          }),
      },
      {
        method: 'GET',
        match: new RegExp(`/api/v1/projects/${PID}/tasks(\\?|$)`),
        respond: () => jsonResponse(pageOf([singleTask])),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
        respond: () => jsonResponse(singleTask),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/events\/stream(\?|$)/,
        respond: () => conn.response,
      },
    ]);
    renderWithQueryClient(<ReviewQueue />);
    const badgeId = `review-queue-merge-${TASK_ID}`;

    await waitFor(() =>
      expect(screen.getByTestId(badgeId).getAttribute('data-merge-status')).toBe('pending'),
    );

    // merge.started → one targeted refetch refreshes the badge in place.
    singleTask = reviewRow({ merge_status: 'merging', version: 5 });
    conn.frame(1, makeEventEnvelope({ id: 1, type: 'merge.started' }));
    await waitFor(() =>
      expect(screen.getByTestId(badgeId).getAttribute('data-merge-status')).toBe('merging'),
    );

    // merge.succeeded → the task left review; the row is dropped.
    singleTask = makeTask({ state: 'completed', review_reason: null, merge_status: 'merged' });
    conn.frame(2, makeEventEnvelope({ id: 2, type: 'merge.succeeded' }));
    await waitFor(() => expect(screen.queryByTestId(badgeId)).toBeNull());
    expect(screen.queryByTestId('review-queue-row')).toBeNull();
  });

  it('shows the failure branch on the board card and skips the merged state', () => {
    const { rerender } = render(
      <TaskCard nowMs={NOW} task={reviewRow({ merge_status: 'conflict' })} />,
    );
    const conflict = screen.getByTestId('task-card-merge-badge');
    expect(conflict.getAttribute('data-merge-status')).toBe('conflict');
    expect(conflict.textContent).toBe('merge conflict');

    rerender(
      <TaskCard nowMs={NOW} task={makeTask({ state: 'in_progress', merge_status: 'failed' })} />,
    );
    expect(screen.getByTestId('task-card-merge-badge').textContent).toBe('merge failed');

    // Completed column already states the outcome — no badge noise.
    rerender(
      <TaskCard nowMs={NOW} task={makeTask({ state: 'completed', merge_status: 'merged' })} />,
    );
    expect(screen.queryByTestId('task-card-merge-badge')).toBeNull();
  });

  it('manual-strategy approve lands completed/merged straight from the response', async () => {
    detailHarness({
      reviewResponse: {
        decision: {
          id: 'rd-0001',
          task_id: TASK_ID,
          resolution_id: 'res-0002',
          decision: 'approve',
          note: '',
          decided_by: 'user-1',
          decided_via: 'web',
          decided_at: '2026-10-01T11:00:00Z',
        },
        task: {
          id: TASK_ID,
          state: 'completed',
          version: 5,
          review_reason: null,
          merge_status: 'merged',
        },
      },
    });
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
    await waitForApproveReady();

    fireEvent.click(screen.getByTestId('review-approve-open'));
    await waitFor(() => expect(screen.getByTestId('approve-confirm')).toBeTruthy());
    fireEvent.click(screen.getByTestId('approve-confirm'));

    await waitFor(() =>
      expect(screen.getByTestId('task-detail-state').textContent).toBe('Completed'),
    );
    expect(screen.queryByTestId('review-panel')).toBeNull();
    expect(screen.getByTestId('task-detail-merge-badge').getAttribute('data-merge-status')).toBe(
      'merged',
    );
    // The client never invents a "merging" phase (OQ-06 risk note).
    expect(document.querySelector('[data-merge-status="merging"]')).toBeNull();
  });
});
