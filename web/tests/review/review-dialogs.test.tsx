/**
 * Review dialogs (MT-4.4-03; `npm test -- -t review-dialogs`).
 *
 * Proves Section 13.2's dialog rules end-to-end on the rendered board:
 * both `dialog` verdicts open their confirmation (never a plain move),
 * approve binds the **displayed** resolution via `POST /tasks/{id}/review`
 * with the version the dialog saw (Section 8.2 rule 3, MT-3.6-04),
 * request changes enforces the mandatory note before any request
 * (T16 guard), reassign sends `reassign`, endpoint failures keep the
 * dialog open with catalog-mapped copy (Section 13.3), and the dialogs
 * are keyboard-operable (Section 13.4 — Radix focus + Escape, reached
 * through the non-drag destination picker too).
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import type { Resolution, Task } from '@/lib/api/generated/types.gen';
import type { BoardState } from '@/lib/board/states';
import {
  installBoardApi,
  jsonResponse,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
} from '../helpers/api';
import { makeResolution } from '../helpers/task-detail';

afterEach(() => {
  vi.unstubAllGlobals();
});

const REVIEW_TASK_ID = 'PID00001-T005';

type ReviewOutcome = { status: number; payload: unknown };

function setup(
  tasks: Task[],
  options: {
    resolutions?: Resolution[];
    review?: () => ReviewOutcome;
  } = {},
) {
  const { resolutions = [makeResolution()], review } = options;
  const { calls } = installBoardApi({
    tasks,
    sse: () => sseConnection().response,
    extraRoutes: [
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/resolutions(\?|$)/,
        respond: () => jsonResponse(pageOf(resolutions)),
      },
      {
        method: 'POST',
        match: /\/api\/v1\/tasks\/[^/]+\/review$/,
        respond: () => {
          const outcome = review?.() ?? {
            status: 201,
            payload: {
              decision: { id: 'dec-1' },
              task: {
                id: REVIEW_TASK_ID,
                state: 'in_human_review',
                version: 4,
                review_reason: 'test_failure',
                merge_status: 'pending',
              },
            },
          };
          return jsonResponse(outcome.payload, outcome.status);
        },
      },
    ],
  });
  const view = renderWithQueryClient(<Board pid="PID00001" />);
  return { calls, ...view };
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

const reviewCalls = (calls: Array<{ method: string; pathname: string; body: unknown }>) =>
  calls.filter((call) => call.method === 'POST' && call.pathname.endsWith('/review'));

describe('review-dialogs (MT-4.4-03)', () => {
  it('drops onto completed open the approve-and-merge confirmation — never a plain move', async () => {
    const { calls } = setup([
      makeTask({
        id: REVIEW_TASK_ID,
        state: 'in_human_review',
        version: 3,
        review_reason: 'test_failure',
      }),
    ]);
    await screen.findByTestId('task-card');

    dragTo('in_human_review', 'completed');

    const dialog = await screen.findByTestId('approve-merge-dialog');
    expect(dialog.textContent).toContain(REVIEW_TASK_ID);
    // Section 8.1 honesty: the copy never claims a direct completed move.
    expect(dialog.textContent).toContain('approved, merging');
    expect(dialog.textContent).not.toMatch(/moves? (the task )?to Completed/);
    // The card never left its column on a dialog verdict (Section 13.2).
    expect(within(column('in_human_review')).getByTestId('task-card')).toBeTruthy();
    expect(reviewCalls(calls)).toHaveLength(0); // open sends nothing
    // The displayed resolution context is what approval will bind to.
    await screen.findByTestId('approve-resolution-context');
    expect(screen.getByTestId('approve-resolution-context').textContent).toContain('attempt 2');
  });

  it('approve sends the viewed resolution_id and the version the dialog saw', async () => {
    const { calls } = setup(
      [makeTask({ id: REVIEW_TASK_ID, state: 'in_human_review', version: 3 })],
      {
        resolutions: [
          makeResolution({ id: 'res-1', attempt_number: 1 }),
          makeResolution({ id: 'res-2', attempt_number: 2 }),
        ],
      },
    );
    await screen.findByTestId('task-card');

    dragTo('in_human_review', 'completed');
    await screen.findByTestId('approve-resolution-context');
    // Newest attempt is the one displayed — and the one bound (MT-3.6-04).
    expect(screen.getByTestId('approve-resolution-context').textContent).toContain('attempt 2');

    fireEvent.click(screen.getByTestId('approve-confirm'));

    await waitFor(() => expect(reviewCalls(calls)).toHaveLength(1));
    const body = reviewCalls(calls)[0].body as Record<string, unknown>;
    expect(body).toEqual({
      decision: 'approve',
      version: 3, // Section 8.2: the version the dialog saw
      resolution_id: 'res-2',
    });
    await waitFor(() => expect(screen.queryByTestId('approve-merge-dialog')).toBeNull());
    // Success states the true result — merge pending, not completed (Section 8.1).
    expect(noticeText()).toContain('merge pending');
    expect(noticeText().toLowerCase()).not.toContain('moved to completed');
  });

  it('approve stays blocked while no resolution exists (T15 guard)', async () => {
    setup([makeTask({ id: REVIEW_TASK_ID, state: 'in_human_review' })], { resolutions: [] });
    await screen.findByTestId('task-card');

    dragTo('in_human_review', 'completed');
    await screen.findByTestId('approve-merge-dialog');

    await waitFor(() =>
      expect(screen.getByTestId('approve-blocked').textContent).toContain('no resolution'),
    );
    expect(screen.getByTestId('approve-confirm')).toHaveProperty('disabled', true);
  });

  it('request changes enforces the mandatory note client-side, then sends it (T16)', async () => {
    const { calls } = setup(
      [makeTask({ id: REVIEW_TASK_ID, state: 'in_human_review', version: 5 })],
      {
        review: () => ({
          status: 201,
          payload: {
            decision: { id: 'dec-2' },
            task: {
              id: REVIEW_TASK_ID,
              state: 'pending',
              version: 6,
              review_reason: 'test_failure',
              merge_status: 'none',
            },
          },
        }),
      },
    );
    await screen.findByTestId('task-card');

    dragTo('in_human_review', 'pending');
    await screen.findByTestId('request-changes-dialog');

    // Empty note: validation fires before any request (courtesy gate —
    // the server enforces T16 too).
    fireEvent.click(screen.getByTestId('request-changes-confirm'));
    expect(screen.getByTestId('request-changes-note-error').textContent).toContain(
      'note is required',
    );
    expect(reviewCalls(calls)).toHaveLength(0);
    expect(screen.getByTestId('request-changes-dialog')).toBeTruthy(); // still open

    fireEvent.change(screen.getByTestId('request-changes-note'), {
      target: { value: '  Fix the failing tests first.  ' },
    });
    fireEvent.click(screen.getByTestId('request-changes-confirm'));

    await waitFor(() => expect(reviewCalls(calls)).toHaveLength(1));
    expect(reviewCalls(calls)[0].body).toEqual({
      decision: 'request_changes',
      version: 5,
      note: 'Fix the failing tests first.', // trimmed
    });
    await waitFor(() => expect(screen.queryByTestId('request-changes-dialog')).toBeNull());
    expect(noticeText()).toContain('Pending');
  });

  it('reassign sends `reassign` with an optional note', async () => {
    const { calls } = setup(
      [makeTask({ id: REVIEW_TASK_ID, state: 'in_human_review', version: 2 })],
      {
        review: () => ({
          status: 201,
          payload: {
            decision: { id: 'dec-3' },
            task: {
              id: REVIEW_TASK_ID,
              state: 'pending',
              version: 3,
              review_reason: null,
              merge_status: 'none',
            },
          },
        }),
      },
    );
    await screen.findByTestId('task-card');

    dragTo('in_human_review', 'pending');
    await screen.findByTestId('request-changes-dialog');

    fireEvent.click(screen.getByTestId('request-changes-reassign'));

    await waitFor(() => expect(reviewCalls(calls)).toHaveLength(1));
    expect(reviewCalls(calls)[0].body).toEqual({ decision: 'reassign', version: 2 });
    await waitFor(() => expect(screen.queryByTestId('request-changes-dialog')).toBeNull());
    expect(noticeText()).toContain('worker was cleared');
  });

  it('endpoint failure keeps the dialog open with catalog-mapped copy (Section 13.3)', async () => {
    const { calls } = setup(
      [makeTask({ id: REVIEW_TASK_ID, state: 'in_human_review', version: 2 })],
      {
        review: () => ({
          status: 409,
          payload: {
            error: {
              code: 'VERSION_CONFLICT',
              message: 'stale row version',
              retryable: false,
              details: null,
              correlation_id: 'corr-1',
            },
          },
        }),
      },
    );
    await screen.findByTestId('task-card');

    dragTo('in_human_review', 'pending');
    await screen.findByTestId('request-changes-dialog');
    fireEvent.change(screen.getByTestId('request-changes-note'), { target: { value: 'Retry me' } });
    fireEvent.click(screen.getByTestId('request-changes-confirm'));

    const alert = await screen.findByTestId('request-changes-error');
    // Catalog copy only — never the raw envelope message (G-07).
    expect(alert.textContent).toContain('Outdated version');
    expect(alert.textContent).not.toContain('stale row version');
    expect(screen.getByTestId('request-changes-dialog')).toBeTruthy(); // stays open
    expect(noticeText()).toContain('Outdated version');
    // Rollback refresh of the affected row (MT-4.4-04).
    expect(calls.some((call) => call.pathname === `/api/v1/tasks/${REVIEW_TASK_ID}`)).toBe(true);
  });

  it('is keyboard-operable: picker path, focus lands inside, Escape cancels without a call', async () => {
    const { calls } = setup([
      makeTask({ id: REVIEW_TASK_ID, state: 'in_human_review', version: 3 }),
    ]);
    await screen.findByTestId('task-card');

    // Non-drag channel: the card's Move button → destination picker.
    fireEvent.click(screen.getByTestId('task-card-move'));
    await screen.findByTestId('move-destination-dialog');
    fireEvent.click(screen.getByTestId('move-option-completed'));

    const dialog = await screen.findByTestId('approve-merge-dialog');
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));

    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('approve-merge-dialog')).toBeNull());
    expect(within(column('in_human_review')).getByTestId('task-card')).toBeTruthy();
    expect(reviewCalls(calls)).toHaveLength(0);
    expect(noticeText()).toBe('');
  });
});
