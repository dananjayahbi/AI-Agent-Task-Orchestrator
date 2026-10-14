/**
 * Transition history section (MT-4.6-03; `npm test -- -t transition`).
 *
 * The append-only record rendered from the task-filtered `GET /events`
 * history (Section 9.2 Events row — the published source; no
 * `GET /tasks/{id}/transitions` exists): fetch-on-expand
 * (Section 13.3/13.4), reverse-chronological rows with actor, from → to
 * state, the **verbatim** Section 8.2 reason code and the server
 * timestamp (Principle P8 — read-only), non-transition envelopes
 * filtered out, and distinct loading / empty / error states
 * (Section 20.3, catalog-only copy).
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { TransitionsHistorySection } from '@/components/task/detail/transitions-section';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makeEventEnvelope,
  pageOf,
  renderWithQueryClient,
} from '../helpers/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

const PID = 'PID00001';
const TASK_ID = 'PID00001-T001';

function transitionEvent(id: number, overrides: Partial<Record<string, unknown>> = {}) {
  return makeEventEnvelope({
    id,
    type: 'task.transitioned',
    task_id: TASK_ID,
    occurred_at: `2026-10-01T10:0${id}:00Z`,
    actor: { type: 'owner', ref: 'owner-1' },
    data: {
      from_state: 'draft',
      to_state: 'pending',
      reason_code: 'publish',
      task_version: id,
    },
    ...overrides,
  });
}

function sectionHarness(events: unknown[], options: { fail?: boolean } = {}) {
  const { calls } = installApi([
    {
      method: 'GET',
      match: /\/api\/v1\/events(\?|$)/,
      respond: () =>
        options.fail === true ? errorResponse('SERVER_ERROR', 500) : jsonResponse(pageOf(events)),
    },
  ]);
  return { calls };
}

const eventCalls = (calls: Array<{ pathname: string; search: string }>) =>
  calls.filter((call) => call.pathname === '/api/v1/events');

describe('TransitionsHistorySection (MT-4.6-03)', () => {
  it('fetches on expand only — nothing loads while collapsed (Section 13.3)', async () => {
    const { calls } = sectionHarness([transitionEvent(1)]);
    renderWithQueryClient(<TransitionsHistorySection pid={PID} taskId={TASK_ID} />);

    expect(screen.getByTestId('task-detail-section-transitions')).toBeTruthy();
    expect(eventCalls(calls)).toHaveLength(0);

    fireEvent.click(screen.getByTestId('transitions-toggle'));
    await screen.findByTestId('transition-list');
    expect(eventCalls(calls)).toHaveLength(1);
    expect(eventCalls(calls)[0].search).toContain(`task=${TASK_ID}`); // Section 9.2 filter
  });

  it('renders rows newest first with actor, states, verbatim reason codes and timestamps', async () => {
    sectionHarness([
      transitionEvent(1),
      // Non-transition envelopes are never rendered as history rows.
      makeEventEnvelope({
        id: 2,
        type: 'task.checkpoint',
        task_id: TASK_ID,
        data: { percent: 40 },
      }),
      transitionEvent(3, {
        actor: { type: 'system', ref: 'lease-sweeper' },
        data: {
          from_state: 'in_progress',
          to_state: 'pending',
          reason_code: 'lease_expired',
          task_version: 7,
        },
      }),
      makeEventEnvelope({
        id: 4,
        type: 'review.requested',
        task_id: TASK_ID,
        data: { review_reason: 'test_failure', task_version: 8 },
      }),
    ]);
    renderWithQueryClient(<TransitionsHistorySection pid={PID} taskId={TASK_ID} />);
    fireEvent.click(screen.getByTestId('transitions-toggle'));

    await screen.findByTestId('transition-list');
    const rows = within(screen.getByTestId('transition-list')).getAllByTestId('transition-row');
    expect(rows).toHaveLength(2); // only transition-shaped events

    // Reverse-chronological (newest id first — Section 13.1).
    expect(rows[0].getAttribute('data-reason')).toBe('lease_expired');
    expect(rows[1].getAttribute('data-reason')).toBe('publish');

    // Section 8.2 reason codes verbatim (Section 20.5 — nothing invented).
    expect(within(rows[0]).getByTestId('transition-reason').textContent).toBe('lease_expired');
    expect(within(rows[0]).getByTestId('transition-from').textContent).toContain('In progress');
    expect(within(rows[0]).getByTestId('transition-to').textContent).toContain('Pending');
    expect(within(rows[0]).getByTestId('transition-actor').textContent).toContain('lease-sweeper');
    expect(within(rows[0]).getByTestId('transition-timestamp').getAttribute('datetime')).toBe(
      '2026-10-01T10:03:00Z',
    );
  });

  it('shows the empty state when the task has no transition events', async () => {
    sectionHarness([
      makeEventEnvelope({
        id: 1,
        type: 'task.checkpoint',
        task_id: TASK_ID,
        data: { percent: 10 },
      }),
    ]);
    renderWithQueryClient(<TransitionsHistorySection pid={PID} taskId={TASK_ID} />);
    fireEvent.click(screen.getByTestId('transitions-toggle'));

    await waitFor(() => expect(screen.getByText('No transitions recorded')).toBeTruthy());
  });

  it('maps endpoint failures to catalog copy with a retry (Section 13.3)', async () => {
    sectionHarness([], { fail: true });
    renderWithQueryClient(<TransitionsHistorySection pid={PID} taskId={TASK_ID} />);
    fireEvent.click(screen.getByTestId('transitions-toggle'));

    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('Something went wrong');
    expect(alert.textContent).not.toContain('raw envelope'); // catalog copy only (G-07)
    expect(screen.getByRole('button', { name: /try again|retry/i })).toBeTruthy();
  });
});
