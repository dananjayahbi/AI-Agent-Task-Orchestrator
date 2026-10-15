/**
 * MT-4.11-02 — keyboard navigation for board and dialogs (Section 13.4;
 * NFR-13 / WCAG 2.1 AA; Section 18 Web UI row: core flows must pass by
 * keyboard).
 *
 * jsdom has no native button activation and no layout engine, so these
 * tests drive the flows with the established repo convention — focus,
 * keydown, then the click a real browser would dispatch — and pin the
 * keyboard *contract* end to end on the rendered surfaces:
 *
 *  1. board move by keyboard routes the identical map verdict, contract
 *     payload and rejection copy as the drag path (FR-WEB-02 — keyboard
 *     is an additional input channel, never a second rule source);
 *  2. the destination picker traps focus while open and restores it to
 *     the trigger on Escape (closing a picker is always safe);
 *  3. create task completes keyboard-only: New task → modal (focus
 *     lands inside) → title → submit POSTs the documented body;
 *  4. the three review actions (approve, request changes, reassign)
 *     complete keyboard-only with the MT-4.4-03 bodies intact (T15
 *     resolution binding, T16 note rule);
 *  5. focus is visibly indicated — the base-layer :focus-visible
 *     fallback plus the component-level rings/outlines on interactive
 *     elements (NFR-13).
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import type { ComponentProps } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import { TaskDetail } from '@/components/task/detail/task-detail';
import { REJECTED_AGENT_OWNED_EXPLANATION } from '@/lib/board/move-map';
import type { BoardState } from '@/lib/board/states';
import type { Task } from '@/lib/api/generated/types.gen';
import {
  installApi,
  installBoardApi,
  jsonResponse,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
  type RecordedCall,
  type Route,
} from '../helpers/api';
import { makeResolution } from '../helpers/task-detail';

afterEach(() => {
  vi.unstubAllGlobals();
});

const PID = 'PID00001';
const TASK_ID = 'PID00001-T001';

/**
 * jsdom buttons do not activate on Enter — mirror the browser contract:
 * focus the control, send the key, then dispatch the click a real
 * browser would fire from that keystroke.
 */
function activateByKeyboard(element: HTMLElement, key = 'Enter'): void {
  element.focus();
  fireEvent.keyDown(element, { key });
  fireEvent.click(element);
}

function mountBoard(tasks: Task[], props: Partial<ComponentProps<typeof Board>> = {}) {
  const { calls } = installBoardApi({
    tasks,
    sse: () => sseConnection().response,
    // The approve dialog loads submissions for the T15 binding seam.
    extraRoutes: [
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/resolutions(\?|$)/,
        respond: () => jsonResponse(pageOf([makeResolution()])),
      },
    ],
  });
  const view = renderWithQueryClient(<Board pid={PID} {...props} />);
  return { calls, ...view };
}

function column(state: BoardState): HTMLElement {
  return screen.getByTestId(`board-column-${state}`);
}

function noticeText(): string {
  return screen.getByTestId('board-move-notice').textContent ?? '';
}

const networkCalls = (calls: RecordedCall[]) => calls;

describe('board move by keyboard (MT-4.11-02)', () => {
  it('routes the identical contract payload as a drop — no mouse, no network call', async () => {
    const onMove = vi.fn();
    const onDialog = vi.fn();
    const { calls } = mountBoard([makeTask({ id: TASK_ID, state: 'draft' })], {
      onMove,
      onDialog,
    });
    await screen.findByTestId('task-card');
    const callsBefore = calls.length;

    // Non-drag channel: the card's native Move button → destination picker.
    activateByKeyboard(screen.getByRole('button', { name: `Move task ${TASK_ID}` }));
    const dialog = await screen.findByTestId('move-destination-dialog');
    // Section 13.4: the dialog takes focus on open (Radix focus trap).
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));

    // Keyboard pick of an Owner-valid destination — same map, same route.
    activateByKeyboard(screen.getByTestId('move-option-pending'));
    await waitFor(() => expect(screen.queryByTestId('move-destination-dialog')).toBeNull());

    expect(onMove).toHaveBeenCalledTimes(1);
    const [task, target, action] = onMove.mock.calls[0];
    expect(task.id).toBe(TASK_ID);
    expect(task.version).toBe(1); // Section 8.2: the version the view saw
    expect(target).toBe('pending'); // canonical snake_case (ADR-010)
    expect(action).toBe('publish'); // identical to the drag path's action
    expect(onDialog).not.toHaveBeenCalled();
    expect(calls.length).toBe(callsBefore); // the pick itself sends nothing
  });

  it('keyboard-picked rejected moves explain with the identical map copy and send nothing', async () => {
    const onMove = vi.fn();
    const { calls } = mountBoard([makeTask({ id: TASK_ID, state: 'draft' })], { onMove });
    await screen.findByTestId('task-card');
    const callsBefore = calls.length;

    activateByKeyboard(screen.getByRole('button', { name: `Move task ${TASK_ID}` }));
    await screen.findByTestId('move-destination-dialog');
    activateByKeyboard(screen.getByTestId('move-option-in_progress'));
    await waitFor(() => expect(screen.queryByTestId('move-destination-dialog')).toBeNull());

    // Section 13.2 semantics are input-independent: the drag path's exact
    // explanation constant, the card stays, and no request is made.
    expect(noticeText()).toBe(REJECTED_AGENT_OWNED_EXPLANATION);
    expect(within(column('draft')).getByTestId('task-card')).toBeTruthy();
    expect(onMove).not.toHaveBeenCalled();
    expect(networkCalls(calls).length).toBe(callsBefore);
  });

  it('traps focus in the picker and restores it to the trigger on Escape', async () => {
    mountBoard([makeTask({ id: TASK_ID, state: 'draft' })]);
    await screen.findByTestId('task-card');

    const moveButton = screen.getByRole('button', { name: `Move task ${TASK_ID}` });
    // Real browsers focus the clicked control before the dialog opens.
    moveButton.focus();
    fireEvent.click(moveButton);
    const dialog = await screen.findByTestId('move-destination-dialog');
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));

    // While open, focus never escapes the dialog — Tab from any inside
    // element stays contained (Radix FocusScope; jsdom has no layout so
    // we pin containment, not the wrap-around order).
    fireEvent.keyDown(document.activeElement as Element, { key: 'Tab' });
    expect(dialog.contains(document.activeElement)).toBe(true);

    // Escape cancels the pick and returns focus to the trigger.
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('move-destination-dialog')).toBeNull());
    await waitFor(() => expect(document.activeElement).toBe(moveButton));
    // A cancelled pick is a no-op: no move, no announcement.
    expect(noticeText()).toBe('');
  });
});

describe('create task by keyboard (MT-4.11-02)', () => {
  it('completes keyboard-only: New task → modal focus → title → submit POSTs the draft', async () => {
    const { calls } = installBoardApi({
      tasks: [],
      sse: () => sseConnection().response,
      extraRoutes: [
        {
          method: 'POST',
          match: /\/api\/v1\/projects\/PID00001\/tasks$/,
          respond: () =>
            jsonResponse(
              makeTask({
                id: 'PID00001-T009',
                title: 'Keyboard-created task',
                state: 'draft',
                version: 1,
              }),
            ),
        },
      ],
    });
    renderWithQueryClient(<Board pid={PID} />);
    await screen.findByTestId('board-new-task');

    activateByKeyboard(screen.getByTestId('board-new-task'));
    const modal = await screen.findByTestId('task-form-modal');
    // Section 13.4: focus lands inside the dialog on open.
    await waitFor(() => expect(modal.contains(document.activeElement)).toBe(true));

    // Type the title and submit via the keyboard path (form button).
    fireEvent.change(within(modal).getByLabelText('Title'), {
      target: { value: 'Keyboard-created task' },
    });
    activateByKeyboard(screen.getByTestId('task-form-submit'));
    // Documented Board behavior: after create the modal stays open and
    // switches to edit mode for the saved row (server truth adopted).
    await waitFor(() =>
      expect(screen.getByTestId('task-form-submit').textContent).toBe('Save changes'),
    );

    const creates = calls.filter(
      (call) => call.method === 'POST' && call.pathname === '/api/v1/projects/PID00001/tasks',
    );
    expect(creates).toHaveLength(1);
    expect((creates[0]?.body as { title?: string }).title).toBe('Keyboard-created task');
  });
});

/** TaskDetail routes for the review panel's keyboard-only flows. */
function detailWithReview(options: { reviewResponse?: unknown } = {}) {
  const taskRow = makeTask({
    id: TASK_ID,
    state: 'in_human_review',
    review_reason: 'test_failure',
    version: 4,
  });
  const routes: Route[] = [
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/resolutions(\?|$)/,
      respond: () => jsonResponse(pageOf([makeResolution()])),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/audit-reports(\?|$)/,
      respond: () => jsonResponse(pageOf([])),
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
      respond: () => jsonResponse({ files: [], truncated: false }),
    },
    {
      method: 'POST',
      match: /\/api\/v1\/tasks\/[^/]+\/review$/,
      respond: () =>
        jsonResponse(
          options.reviewResponse ?? {
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
              state: 'in_human_review',
              version: 5,
              review_reason: 'test_failure',
              merge_status: 'pending',
            },
          },
        ),
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
  const view = renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
  return { calls, ...view };
}

const reviewCalls = (calls: RecordedCall[]) =>
  calls.filter((call) => call.method === 'POST' && call.pathname.endsWith('/review'));

describe('review actions by keyboard (MT-4.11-02)', () => {
  it('approve completes keyboard-only and binds the displayed resolution (T15)', async () => {
    const api = detailWithReview();
    await waitFor(() =>
      expect((screen.getByTestId('review-approve-open') as HTMLButtonElement).disabled).toBe(false),
    );

    activateByKeyboard(screen.getByTestId('review-approve-open'));
    const dialog = await screen.findByTestId('approve-merge-dialog');
    // Focus moves into the confirmation and stays there.
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));
    fireEvent.keyDown(document.activeElement as Element, { key: 'Tab' });
    expect(dialog.contains(document.activeElement)).toBe(true);

    activateByKeyboard(screen.getByTestId('approve-confirm'));
    await waitFor(() => expect(screen.getByTestId('review-notice')).toBeTruthy());

    const posts = reviewCalls(api.calls);
    expect(posts).toHaveLength(1);
    expect(posts[0]?.body).toEqual({
      decision: 'approve',
      version: 4, // the version the dialog saw (Section 8.2 rule 3)
      resolution_id: 'res-0002', // the displayed resolution (MT-3.6-04)
    });
    // Section 8.1 honesty: merge pending, never "completed".
    const notice = screen.getByTestId('review-notice').textContent ?? '';
    expect(notice).toContain('merge pending');
    expect(notice).not.toContain('completed');
    expect(screen.queryByTestId('approve-merge-dialog')).toBeNull();
  });

  it('request changes completes keyboard-only with the mandatory-note rule intact (T16)', async () => {
    const api = detailWithReview({
      reviewResponse: {
        decision: {
          id: 'rd-0002',
          task_id: TASK_ID,
          resolution_id: 'res-0002',
          decision: 'request_changes',
          note: 'Narrow the scope.',
          decided_by: 'user-1',
          decided_via: 'web',
          decided_at: '2026-10-01T11:00:00Z',
        },
        task: {
          id: TASK_ID,
          state: 'pending',
          version: 5,
          review_reason: null,
          merge_status: 'none',
        },
      },
    });
    await waitFor(() => expect(screen.getByTestId('review-request-changes-open')).toBeTruthy());

    activateByKeyboard(screen.getByTestId('review-request-changes-open'));
    const dialog = await screen.findByTestId('request-changes-dialog');
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));

    // Empty note: the guard fires, nothing is sent, the dialog stays open.
    activateByKeyboard(screen.getByTestId('request-changes-confirm'));
    expect(await screen.findByTestId('request-changes-note-error')).toBeTruthy();
    expect(reviewCalls(api.calls)).toHaveLength(0);
    expect(screen.getByTestId('request-changes-dialog')).toBeTruthy();

    // Type the note and confirm — the note becomes the request body.
    const note = screen.getByTestId('request-changes-note');
    note.focus();
    fireEvent.change(note, { target: { value: 'Narrow the scope.' } });
    activateByKeyboard(screen.getByTestId('request-changes-confirm'));
    await waitFor(() => expect(reviewCalls(api.calls)).toHaveLength(1));
    expect(reviewCalls(api.calls)[0]?.body).toEqual({
      decision: 'request_changes',
      version: 4,
      note: 'Narrow the scope.',
    });
  });

  it('reassign completes keyboard-only', async () => {
    const api = detailWithReview({
      reviewResponse: {
        decision: {
          id: 'rd-0003',
          task_id: TASK_ID,
          resolution_id: null,
          decision: 'reassign',
          note: '',
          decided_by: 'user-1',
          decided_via: 'web',
          decided_at: '2026-10-01T11:00:00Z',
        },
        task: {
          id: TASK_ID,
          state: 'pending',
          version: 5,
          review_reason: null,
          merge_status: 'none',
        },
      },
    });
    await waitFor(() => expect(screen.getByTestId('review-reassign-open')).toBeTruthy());

    activateByKeyboard(screen.getByTestId('review-reassign-open'));
    await screen.findByTestId('request-changes-dialog');
    activateByKeyboard(screen.getByTestId('request-changes-reassign'));
    await waitFor(() => expect(reviewCalls(api.calls)).toHaveLength(1));
    // Empty note → the body omits the field entirely (reassignBody).
    expect(reviewCalls(api.calls)[0]?.body).toEqual({ decision: 'reassign', version: 4 });
  });
});

describe('visible focus indication (MT-4.11-02)', () => {
  it('ships a base-layer :focus-visible fallback for elements without a component ring', () => {
    const css = readFileSync(join(process.cwd(), 'app', 'globals.css'), 'utf8');
    expect(css).toMatch(/:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--ring\)/);
  });

  it('marks the board interactive controls with focus-visible rings/outlines', async () => {
    mountBoard([makeTask({ id: TASK_ID, state: 'draft' })]);
    await screen.findByTestId('task-card');

    // Shared Button primitive (New task) carries the focus-visible ring.
    expect(screen.getByTestId('board-new-task').className).toContain('focus-visible:ring');
    // The card's Move control outlines on keyboard focus…
    const moveButton = screen.getByRole('button', { name: `Move task ${TASK_ID}` });
    expect(moveButton.className).toContain('focus-visible:outline');
    // …as do the picker's destination rows…
    fireEvent.click(moveButton);
    await screen.findByTestId('move-destination-dialog');
    expect(screen.getByTestId('move-option-pending').className).toContain('focus-visible:outline');
    // …and the virtualized card rows themselves (roving focus targets).
    const row = document.querySelector('[data-index]');
    expect(row?.className ?? '').toContain('focus-visible:ring-2');
  });
});
