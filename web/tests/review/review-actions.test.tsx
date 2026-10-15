/**
 * MT-4.8-03 — review actions in the panel (Section 11.5's three actions,
 * Section 13.2 confirmations, Section 8.2 T15/T16 guards):
 *
 *  - approve binds the displayed resolution + version (WP-3.6 stale
 *    protection), records the decision with `decided_via: web`
 *    (Section 7.2) shown from the response record, and never claims
 *    completion (Section 8.1 / ADR-008 — "merge pending" copy);
 *  - request changes keeps the mandatory-note guard and returns the
 *    task to `pending` with the note as latest feedback (T16);
 *  - reassign returns to `pending` without a note;
 *  - VERSION_CONFLICT keeps the dialog open, announces catalog-only
 *    copy (G-07) and refreshes the detail row to server truth;
 *  - double-submit is guarded and T15's "resolution must exist" guard
 *    disables approve at the panel itself.
 *
 * The dialogs and the shared mutation are the MT-4.4-03 stack — these
 * tests prove the panel hosts them correctly in the detail context.
 */
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { TaskDetail } from '@/components/task/detail/task-detail';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
  type RecordedCall,
  type Route,
} from '../helpers/api';
import { makeAuditReport, makeResolution } from '../helpers/task-detail';
import { patchBodyPayload, SINGLE_FILE_PATCH } from '../diff/fixtures';

afterEach(() => {
  vi.unstubAllGlobals();
});

const PID = 'PID00001';
const TASK_ID = 'PID00001-T001';

const reviewTask = (overrides: Partial<ReturnType<typeof makeTask>> = {}) =>
  makeTask({ state: 'in_human_review', review_reason: 'test_failure', version: 4, ...overrides });

function decisionRecord(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 'rd-0001',
    task_id: TASK_ID,
    resolution_id: 'res-0002',
    decision: 'approve',
    note: '',
    decided_by: 'user-1',
    decided_via: 'web',
    decided_at: '2026-10-01T11:00:00Z',
    ...overrides,
  };
}

function decisionResponse(overrides: {
  decision?: Record<string, unknown>;
  task?: Record<string, unknown>;
}) {
  return {
    decision: decisionRecord(overrides.decision ?? {}),
    task: {
      id: TASK_ID,
      state: 'in_human_review',
      version: 5,
      review_reason: 'test_failure',
      merge_status: 'pending',
      ...(overrides.task ?? {}),
    },
  };
}

function actionHarness(
  options: {
    taskRow?: unknown;
    resolutions?: unknown[];
    reviewResponse?: unknown;
    reviewHang?: boolean;
  } = {},
): { calls: RecordedCall[]; setTaskRow: (row: unknown) => void } {
  let taskRow: unknown = options.taskRow ?? reviewTask();
  const routes: Route[] = [
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/resolutions(\?|$)/,
      respond: () => jsonResponse(pageOf(options.resolutions ?? [makeResolution()])),
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
      method: 'GET',
      match: /\/api\/v1\/resolutions\/[^/]+\/patch(\?|$)/,
      respond: () => jsonResponse(patchBodyPayload(SINGLE_FILE_PATCH)),
    },
    {
      method: 'POST',
      match: /\/api\/v1\/tasks\/[^/]+\/review$/,
      respond:
        options.reviewHang === true
          ? () => new Promise<Response>(() => {})
          : () =>
              // Already-built responses (error envelopes) pass through as-is.
              options.reviewResponse instanceof Response
                ? options.reviewResponse
                : jsonResponse(options.reviewResponse ?? decisionResponse({})),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
      respond: () => jsonResponse(taskRow),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/events\/stream(\?|$)/,
      respond: () => sseConnection().response,
    },
  ];
  const { calls } = installApi(routes);
  return {
    calls,
    setTaskRow: (row: unknown) => {
      taskRow = row;
    },
  };
}

const reviewPosts = (calls: RecordedCall[]) =>
  calls.filter((call) => call.method === 'POST' && call.pathname.endsWith('/review'));

function renderDetail() {
  return renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
}

/** The approve control unlocks once the resolutions query settles (T15). */
async function waitForApproveReady() {
  await waitFor(() =>
    expect((screen.getByTestId('review-approve-open') as HTMLButtonElement).disabled).toBe(false),
  );
}

describe('ReviewPanel actions (MT-4.8-03)', () => {
  it('approve binds the displayed resolution + version and records the web decision', async () => {
    const api = actionHarness();
    renderDetail();
    await waitForApproveReady();

    fireEvent.click(screen.getByTestId('review-approve-open'));
    await waitFor(() => expect(screen.getByTestId('approve-merge-dialog')).toBeTruthy());
    // The dialog shows exactly what gets bound (MT-3.6-04 stale protection).
    expect(screen.getByTestId('approve-resolution-context').textContent).toContain(
      'You are approving attempt 2',
    );

    fireEvent.click(screen.getByTestId('approve-confirm'));
    await waitFor(() => expect(screen.getByTestId('review-notice')).toBeTruthy());

    const posts = reviewPosts(api.calls);
    expect(posts).toHaveLength(1);
    expect(posts[0]?.body).toEqual({
      decision: 'approve',
      version: 4,
      resolution_id: 'res-0002',
    });
    // Success states the true result — merge pending, never completed.
    const notice = screen.getByTestId('review-notice').textContent ?? '';
    expect(notice).toContain('merge pending');
    expect(notice).not.toContain('completed');
    // The recorded decision surfaces with its decided_via channel
    // (Section 7.2/11.5 — decisions are recorded server-side).
    const record = screen.getByTestId('review-decision-record').textContent ?? '';
    expect(record).toContain('approve');
    expect(record).toContain('web');
    // Dialog closed on success; the detail row settles to the response
    // identity (T15 keeps the state — merge_status is the sub-status).
    expect(screen.queryByTestId('approve-merge-dialog')).toBeNull();
    await waitFor(() =>
      expect(screen.getByTestId('task-detail').getAttribute('data-task-version')).toBe('5'),
    );
    expect(screen.getByTestId('task-detail-state').textContent).toBe('Human review');
  });

  it('request changes enforces the note, sends it, and the task returns to pending', async () => {
    const api = actionHarness({
      reviewResponse: decisionResponse({
        decision: decisionRecord({ decision: 'request_changes', note: 'Narrow the scope.' }),
        task: { state: 'pending', version: 5, review_reason: null, merge_status: 'none' },
      }),
    });
    renderDetail();
    await waitFor(() => expect(screen.getByTestId('review-request-changes-open')).toBeTruthy());

    fireEvent.click(screen.getByTestId('review-request-changes-open'));
    await waitFor(() => expect(screen.getByTestId('request-changes-dialog')).toBeTruthy());
    // T16 note guard fires before any request (client courtesy; server enforces).
    fireEvent.click(screen.getByTestId('request-changes-confirm'));
    expect(screen.getByTestId('request-changes-note-error')).toBeTruthy();
    expect(reviewPosts(api.calls)).toHaveLength(0);

    fireEvent.change(screen.getByTestId('request-changes-note'), {
      target: { value: 'Narrow the scope.' },
    });
    fireEvent.click(screen.getByTestId('request-changes-confirm'));

    await waitFor(() => expect(reviewPosts(api.calls)).toHaveLength(1));
    expect(reviewPosts(api.calls)[0]?.body).toEqual({
      decision: 'request_changes',
      version: 4,
      note: 'Narrow the scope.',
    });
    // Settle: the task leaves review — the panel (its host) goes with it.
    await waitFor(() => expect(screen.queryByTestId('review-panel')).toBeNull());
    expect(screen.getByTestId('task-detail-state').textContent).toBe('Pending');
  });

  it('reassign returns to pending without requiring a note', async () => {
    const api = actionHarness({
      reviewResponse: decisionResponse({
        decision: decisionRecord({ decision: 'reassign', resolution_id: 'res-0002' }),
        task: { state: 'pending', version: 5, review_reason: null, merge_status: 'none' },
      }),
    });
    renderDetail();
    await waitFor(() => expect(screen.getByTestId('review-reassign-open')).toBeTruthy());

    fireEvent.click(screen.getByTestId('review-reassign-open'));
    await waitFor(() => expect(screen.getByTestId('request-changes-dialog')).toBeTruthy());
    fireEvent.click(screen.getByTestId('request-changes-reassign'));

    await waitFor(() => expect(reviewPosts(api.calls)).toHaveLength(1));
    expect(reviewPosts(api.calls)[0]?.body).toEqual({ decision: 'reassign', version: 4 });
    await waitFor(() => expect(screen.queryByTestId('review-panel')).toBeNull());
    expect(screen.getByTestId('task-detail-state').textContent).toBe('Pending');
  });

  it('VERSION_CONFLICT keeps the dialog open, announces catalog copy, refreshes to truth', async () => {
    const api = actionHarness({
      // The envelope message must never surface (G-07) — catalog only.
      reviewResponse: errorResponse('VERSION_CONFLICT', 409, 'The resolution binding is stale.'),
    });
    renderDetail();
    await waitForApproveReady();
    // The conflict refresh will read the server's newer row.
    api.setTaskRow(reviewTask({ version: 9 }));

    fireEvent.click(screen.getByTestId('review-approve-open'));
    await waitFor(() => expect(screen.getByTestId('approve-confirm')).toBeTruthy());
    fireEvent.click(screen.getByTestId('approve-confirm'));

    await waitFor(() => expect(screen.getByTestId('review-notice')).toBeTruthy());
    const notice = screen.getByTestId('review-notice').textContent ?? '';
    expect(notice).toContain('Outdated version'); // catalog title for VERSION_CONFLICT
    expect(notice).toContain('server’s current state'); // refresh explained
    expect(notice).not.toContain('stale'); // raw envelope text never leaks
    // The dialog stays open for retry (Section 13.3) with its own copy.
    expect(screen.getByTestId('approve-error')).toBeTruthy();
    // The detail row refreshes to server truth — no blind retry.
    await waitFor(() =>
      expect(screen.getByTestId('task-detail').getAttribute('data-task-version')).toBe('9'),
    );
    expect(
      api.calls.filter((call) => call.method === 'GET' && call.pathname.endsWith(`/${TASK_ID}`)),
    ).toHaveLength(2);
  });

  it('guards double-submit: the confirm is disabled while in flight', async () => {
    const api = actionHarness({ reviewHang: true });
    renderDetail();
    await waitForApproveReady();

    fireEvent.click(screen.getByTestId('review-approve-open'));
    await waitFor(() => expect(screen.getByTestId('approve-confirm')).toBeTruthy());
    fireEvent.click(screen.getByTestId('approve-confirm'));

    await waitFor(() =>
      expect((screen.getByTestId('approve-confirm') as HTMLButtonElement).disabled).toBe(true),
    );
    expect(screen.getByTestId('approve-confirm').textContent).toBe('Approving…');
    fireEvent.click(screen.getByTestId('approve-confirm'));
    expect(reviewPosts(api.calls)).toHaveLength(1);
    // The panel's own controls stay locked to the same pending mutation.
    expect((screen.getByTestId('review-approve-open') as HTMLButtonElement).disabled).toBe(true);
  });

  it('T15 guard at the panel: approve is disabled while no resolution exists', async () => {
    actionHarness({ resolutions: [] });
    renderDetail();
    await waitFor(() => expect(screen.getByTestId('review-approve-blocked')).toBeTruthy());

    expect((screen.getByTestId('review-approve-open') as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByTestId('review-approve-blocked').textContent).toContain('resolution');
    // The note actions need no resolution — they stay available.
    expect((screen.getByTestId('review-request-changes-open') as HTMLButtonElement).disabled).toBe(
      false,
    );
  });
});
