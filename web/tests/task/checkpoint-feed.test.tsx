/**
 * MT-4.6-02 — live checkpoint feed: Section 13.2 component contract
 * (reverse-chronological rows with percent, message, token usage, kind),
 * cursor-gated history (Section 9.2), live `task.checkpoint` patching with
 * no refetch-per-event (Section 13.3), reconnect-replay dedupe
 * (Section 9.6), the session-scoped follow toggle, and the distinct
 * loading / empty / disconnected / error states (Section 20.3, catalog
 * copy only per Section 20.4 item 5).
 */
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { CheckpointFeed } from '@/components/task/detail/checkpoint-feed';
import { TaskDetail } from '@/components/task/detail/task-detail';
import { applyCheckpointEvent, type CheckpointFeedCache } from '@/lib/queries/checkpoints';
import type { EventEnvelope } from '@/lib/api/generated/types.gen';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makeEventEnvelope,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
  type SseConnection,
} from '../helpers/api';
import { makeCheckpoint } from '../helpers/task-detail';

afterEach(() => {
  vi.unstubAllGlobals();
  window.sessionStorage.clear();
});

const PID = 'PID00001';
const TASK_ID = 'PID00001-T001';

/**
 * Full detail-view routes so the page (and its single SSE sink) can render;
 * `checkpointsRespond` is per-test to drive paging/errors.
 */
function detailHarness(checkpointsRespond: (info: { search: string }) => Response): {
  calls: Array<{ pathname: string; search: string }>;
  streams: SseConnection[];
} {
  const streams: SseConnection[] = [];
  const { calls } = installApi([
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/checkpoints(\?|$)/,
      respond: checkpointsRespond,
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/attachments(\?|$)/,
      respond: () => jsonResponse(pageOf([])),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
      respond: () => jsonResponse(makeTask()),
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
  return { calls, streams };
}

const checkpointCalls = (calls: Array<{ pathname: string; search: string }>) =>
  calls.filter((call) => /\/checkpoints(\?|$)/.test(call.pathname + call.search));

function checkpointEvent(id: number, data: Record<string, unknown>): EventEnvelope {
  return makeEventEnvelope({
    id,
    type: 'task.checkpoint',
    task_id: TASK_ID,
    occurred_at: '2026-10-01T12:00:00Z',
    data,
  }) as EventEnvelope;
}

describe('CheckpointFeed (MT-4.6-02)', () => {
  it('renders history reverse-chronological with percent, message, tokens and kind (Section 13.2)', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/checkpoints(\?|$)/,
        respond: () =>
          jsonResponse(
            pageOf([
              // Deliberately out of order — the client mirrors the server sort.
              makeCheckpoint({
                id: 'chk-1',
                timestamp: '2026-10-01T10:00:00Z',
                message: 'Earlier progress',
                percent: 20,
                kind: 'progress',
              }),
              makeCheckpoint({
                id: 'chk-3',
                timestamp: '2026-10-01T12:00:00Z',
                message: 'Latest progress',
                percent: 80,
                kind: 'liveness',
                token_usage: { input: 100, output: 50 },
              }),
              makeCheckpoint({
                id: 'chk-2',
                timestamp: '2026-10-01T11:00:00Z',
                message: '',
                percent: null,
                kind: 'system',
              }),
            ]),
          ),
      },
    ]);
    renderWithQueryClient(<CheckpointFeed pid={PID} taskId={TASK_ID} streamStatus="open" />);

    await waitFor(() => expect(screen.getByTestId('checkpoint-feed-list')).toBeTruthy());
    const rows = screen.getAllByTestId('checkpoint-row');
    expect(rows).toHaveLength(3);
    // Newest first (12:00 → 11:00 → 10:00), regardless of arrival order.
    expect(rows[0].textContent).toContain('Latest progress');
    expect(rows[1].textContent).toContain('No message');
    expect(rows[2].textContent).toContain('Earlier progress');
    // Section 7.2 nullable percent never renders as 0.
    expect(screen.getAllByTestId('checkpoint-percent')[0].textContent).toBe('80%');
    expect(screen.getAllByTestId('checkpoint-percent')[1].textContent).toBe('Progress unknown');
    expect(screen.getAllByTestId('checkpoint-percent')[2].textContent).toBe('20%');
    // Token usage (free JSON) rendered defensively as key/value pairs.
    expect(screen.getByTestId('checkpoint-tokens').textContent).toBe('input: 100 · output: 50');
    // Kind labels.
    expect(screen.getAllByTestId('checkpoint-kind')[0].textContent).toBe('Liveness');
    expect(screen.getAllByTestId('checkpoint-kind')[1].textContent).toBe('System');
    expect(screen.getAllByTestId('checkpoint-kind')[2].textContent).toBe('Progress');
    // Empty message degrades to a placeholder, not a blank line.
    expect(screen.getAllByTestId('checkpoint-message')[1].textContent).toContain('No message');
    // Stream indicator reflects the hook status (Section 13.3).
    expect(screen.getByTestId('checkpoint-feed-stream').getAttribute('data-status')).toBe('open');
  });

  it('appends live task.checkpoint events with zero refetches (Section 13.3 patching)', async () => {
    const { calls, streams } = detailHarness(() =>
      jsonResponse(pageOf([makeCheckpoint({ id: 'chk-1', message: 'From history' })])),
    );
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getAllByTestId('checkpoint-row')).toHaveLength(1));
    const baseline = checkpointCalls(calls).length;

    streams[0].frame(
      2,
      checkpointEvent(2, {
        checkpoint_id: 'chk-live',
        attempt_number: 1,
        kind: 'progress',
        percent: 90,
        session_id: 'sess-1',
        message: 'Live checkpoint',
        token_usage: null,
      }),
    );

    await waitFor(() => expect(screen.getAllByTestId('checkpoint-row')).toHaveLength(2));
    expect(screen.getAllByTestId('checkpoint-message')[0].textContent).toContain('Live checkpoint');
    // Acceptance: the live row arrived via cache patch, not a refetch.
    expect(checkpointCalls(calls)).toHaveLength(baseline);
  });

  it('does not duplicate replayed checkpoints after a reconnect (Section 9.6)', async () => {
    const { calls, streams } = detailHarness(() =>
      jsonResponse(pageOf([makeCheckpoint({ id: 'chk-1', message: 'From history' })])),
    );
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getAllByTestId('checkpoint-row')).toHaveLength(1));
    const baseline = checkpointCalls(calls).length;

    const replay = checkpointEvent(2, {
      checkpoint_id: 'chk-live',
      message: 'Live checkpoint',
      percent: 90,
      kind: 'progress',
    });
    streams[0].frame(2, replay);
    // Reconnect replay: same checkpoint id delivered again under a new event id.
    streams[0].frame(9, { ...replay, id: 9 } as EventEnvelope);

    await waitFor(() => expect(screen.getAllByTestId('checkpoint-row')).toHaveLength(2));
    expect(screen.getAllByTestId('checkpoint-message')[0].textContent).toContain('Live checkpoint');
    expect(checkpointCalls(calls)).toHaveLength(baseline);
  });

  it('ignores malformed checkpoint events without breaking the feed', async () => {
    const { streams } = detailHarness(() =>
      jsonResponse(pageOf([makeCheckpoint({ id: 'chk-1', message: 'From history' })])),
    );
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getAllByTestId('checkpoint-row')).toHaveLength(1));

    streams[0].frame(2, checkpointEvent(2, { message: 'no checkpoint id' }));
    streams[0].frame(
      3,
      makeEventEnvelope({ id: 3, type: 'task.updated', task_id: TASK_ID, data: {} }),
    );

    // Nothing rendered, nothing crashed.
    expect(screen.getAllByTestId('checkpoint-row')).toHaveLength(1);
    expect(screen.getByTestId('checkpoint-feed')).toBeTruthy();
  });

  it('shows the empty state when the task has no checkpoints', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/checkpoints(\?|$)/,
        respond: () => jsonResponse(pageOf([])),
      },
    ]);
    renderWithQueryClient(<CheckpointFeed pid={PID} taskId={TASK_ID} streamStatus="open" />);
    await waitFor(() => expect(screen.getByText('No checkpoints yet')).toBeTruthy());
  });

  it('shows a distinct loading state while history is pending', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/checkpoints(\?|$)/,
        respond: () => new Promise<Response>(() => {}),
      },
    ]);
    renderWithQueryClient(<CheckpointFeed pid={PID} taskId={TASK_ID} streamStatus="open" />);
    expect(screen.getByText('Loading checkpoints…')).toBeTruthy();
  });

  it('maps checkpoint errors to catalog copy only', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/checkpoints(\?|$)/,
        respond: () => errorResponse('SERVER_ERROR', 500, 'internal stack trace'),
      },
    ]);
    renderWithQueryClient(<CheckpointFeed pid={PID} taskId={TASK_ID} streamStatus="open" />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toContain('Something went wrong');
    expect(alert.textContent).not.toContain('internal stack trace');
  });

  it('keeps history visible with a disconnected indicator when the stream drops', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/checkpoints(\?|$)/,
        respond: () => jsonResponse(pageOf([makeCheckpoint()])),
      },
    ]);
    renderWithQueryClient(<CheckpointFeed pid={PID} taskId={TASK_ID} streamStatus="closed" />);
    await waitFor(() => expect(screen.getByTestId('checkpoint-row')).toBeTruthy());
    const indicator = screen.getByTestId('checkpoint-feed-stream');
    expect(indicator.getAttribute('data-status')).toBe('closed');
    expect(indicator.textContent).toContain('Updates paused');
    // The already-loaded history is not blocked by the disconnect.
    expect(screen.getByTestId('checkpoint-feed-list')).toBeTruthy();
  });

  it('follow toggle is user-controllable and persists per session (MT risk note)', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/checkpoints(\?|$)/,
        respond: () => jsonResponse(pageOf([makeCheckpoint()])),
      },
    ]);
    const { unmount } = renderWithQueryClient(
      <CheckpointFeed pid={PID} taskId={TASK_ID} streamStatus="open" />,
    );
    await waitFor(() => expect(screen.getByTestId('checkpoint-feed-follow')).toBeTruthy());
    // Default on.
    const toggle = screen.getByTestId('checkpoint-feed-follow') as HTMLInputElement;
    expect(toggle.checked).toBe(true);

    fireEvent.click(toggle);
    expect(toggle.checked).toBe(false);
    expect(window.sessionStorage.getItem('task-detail:checkpoint-follow')).toBe('off');

    // A fresh mount in the same session restores the stored choice.
    unmount();
    renderWithQueryClient(<CheckpointFeed pid={PID} taskId={TASK_ID} streamStatus="open" />);
    await waitFor(() => expect(screen.getByTestId('checkpoint-feed-follow')).toBeTruthy());
    expect((screen.getByTestId('checkpoint-feed-follow') as HTMLInputElement).checked).toBe(false);
  });

  it('loads older pages through the cursor without refetching or dropping live rows', async () => {
    const { calls } = installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/checkpoints(\?|$)/,
        respond: ({ search }) => {
          const cursor = new URLSearchParams(search).get('cursor');
          if (cursor === null) {
            return jsonResponse(
              pageOf(
                [
                  makeCheckpoint({
                    id: 'chk-new',
                    message: 'Newest',
                    timestamp: '2026-10-01T12:00:00Z',
                  }),
                ],
                'cursor-1',
              ),
            );
          }
          return jsonResponse(
            pageOf([
              makeCheckpoint({
                id: 'chk-old',
                message: 'Oldest',
                timestamp: '2026-10-01T09:00:00Z',
              }),
              // Overlap the first page — dedupe must drop the repeat.
              makeCheckpoint({
                id: 'chk-new',
                message: 'Newest',
                timestamp: '2026-10-01T12:00:00Z',
              }),
            ]),
          );
        },
      },
    ]);
    renderWithQueryClient(<CheckpointFeed pid={PID} taskId={TASK_ID} streamStatus="open" />);
    await waitFor(() => expect(screen.getByTestId('checkpoint-feed-older')).toBeTruthy());
    expect(checkpointCalls(calls)).toHaveLength(1);

    fireEvent.click(screen.getByTestId('checkpoint-feed-older'));

    await waitFor(() => expect(screen.getAllByTestId('checkpoint-row')).toHaveLength(2));
    const rows = screen.getAllByTestId('checkpoint-row');
    expect(rows[0].textContent).toContain('Newest');
    expect(rows[1].textContent).toContain('Oldest');
    // The second page request carried the cursor (Section 9.2).
    expect(checkpointCalls(calls)[1].search).toContain('cursor=cursor-1');
    // Next cursor exhausted — the button disappears.
    await waitFor(() => expect(screen.queryByTestId('checkpoint-feed-older')).toBeNull());
  });
});

describe('applyCheckpointEvent (MT-4.6-02 reducer)', () => {
  const base: CheckpointFeedCache = { rows: [], nextCursor: null };

  it('builds a row from the WP-1.8 event payload with the envelope timestamp', () => {
    const next = applyCheckpointEvent(
      base,
      checkpointEvent(1, {
        checkpoint_id: 'chk-live',
        attempt_number: 2,
        kind: 'progress',
        percent: 55,
        session_id: 'sess-9',
        message: 'From event',
        token_usage: { total: 10 },
      }),
    );
    expect(next.rows).toHaveLength(1);
    expect(next.rows[0]).toMatchObject({
      id: 'chk-live',
      task_id: TASK_ID,
      attempt_number: 2,
      percent: 55,
      message: 'From event',
      timestamp: '2026-10-01T12:00:00Z',
      kind: 'progress',
    });
  });

  it('returns the cache untouched for non-checkpoint events or missing ids', () => {
    const other = makeEventEnvelope({ type: 'task.updated', data: {} }) as EventEnvelope;
    expect(applyCheckpointEvent(base, other)).toBe(base);
    const noId = checkpointEvent(1, { message: 'x' });
    expect(applyCheckpointEvent(base, noId)).toBe(base);
  });

  it('dedupes replays on checkpoint id (Section 9.6)', () => {
    const event = checkpointEvent(1, { checkpoint_id: 'chk-live', message: 'Once' });
    const once = applyCheckpointEvent(base, event);
    const twice = applyCheckpointEvent(once, { ...event, id: 99 } as EventEnvelope);
    expect(twice.rows).toHaveLength(1);
  });
});
