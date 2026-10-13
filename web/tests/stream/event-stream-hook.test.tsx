/**
 * MT-4.3-04 — SSE stream hook: project filter, Last-Event-ID resume on
 * reconnect, heartbeat tolerance, status transitions, catalog gating and
 * unmount cleanup (Section 9.6; Section 13.3).
 */
import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { EventEnvelope } from '@/lib/api/generated/types.gen';
import { useEventStream } from '@/lib/stream/use-event-stream';
import { installApi, makeEventEnvelope, sseConnection, type SseConnection } from '../helpers/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

/** A queue of SSE connections — one per (re)connect the hook performs. */
function installStreamQueue() {
  const queue: SseConnection[] = [];
  const opened: Array<{ search: string; lastEventId: string | null }> = [];
  installApi([
    {
      method: 'GET',
      match: /\/api\/v1\/events\/stream(\?|$)/,
      respond: ({ search, request }) => {
        const connection = sseConnection();
        queue.push(connection);
        opened.push({ search, lastEventId: request.headers.get('last-event-id') });
        return connection.response;
      },
    },
  ]);
  return { queue, opened };
}

describe('useEventStream (MT-4.3-04)', () => {
  it('connects with the project filter and delivers parsed envelopes to subscribers', async () => {
    const { queue, opened } = installStreamQueue();
    const events: EventEnvelope[] = [];
    const { result } = renderHook(() =>
      useEventStream({
        project: 'PID00001',
        onEvent: (event) => events.push(event),
        retryBaseDelayMs: 1,
      }),
    );

    await waitFor(() => expect(opened).toHaveLength(1));
    expect(opened[0].search).toContain('project=PID00001');
    expect(result.current.status).toBe('connecting');
    expect(result.current.lastEventId).toBeNull();

    queue[0].frame(5, makeEventEnvelope({ id: 5, type: 'task.updated' }));
    await waitFor(() => expect(events).toHaveLength(1));
    expect(events[0].type).toBe('task.updated');
    await waitFor(() => expect(result.current.status).toBe('open'));
    expect(result.current.lastEventId).toBe(5);
  });

  it('tolerates 15 s heartbeat comments without delivering data or dropping the connection', async () => {
    const { queue, opened } = installStreamQueue();
    const events: EventEnvelope[] = [];
    const { result } = renderHook(() =>
      useEventStream({
        project: 'PID00001',
        onEvent: (event) => events.push(event),
        retryBaseDelayMs: 1,
      }),
    );

    await waitFor(() => expect(opened).toHaveLength(1));
    queue[0].heartbeat();
    queue[0].heartbeat();
    queue[0].frame(9, makeEventEnvelope({ id: 9, type: 'task.checkpoint' }));

    await waitFor(() => expect(events).toHaveLength(1));
    expect(events[0].id).toBe(9);
    // Heartbeats neither advance the resume position nor cause a reconnect.
    expect(result.current.lastEventId).toBe(9);
    expect(opened).toHaveLength(1);
    expect(result.current.status).toBe('open');
  });

  it('reconnects after a dropped stream and resumes with Last-Event-ID (no gaps, no duplicates)', async () => {
    const { queue, opened } = installStreamQueue();
    const events: EventEnvelope[] = [];
    const { result } = renderHook(() =>
      useEventStream({
        project: 'PID00001',
        onEvent: (event) => events.push(event),
        retryBaseDelayMs: 1,
      }),
    );

    await waitFor(() => expect(opened).toHaveLength(1));
    queue[0].frame(7, makeEventEnvelope({ id: 7, type: 'task.transitioned' }));
    await waitFor(() => expect(events).toHaveLength(1));
    expect(opened[0].lastEventId).toBeNull(); // first connect never resumes

    queue[0].fail(new Error('connection reset')); // MT-1.10-03 server contract kicks in
    await waitFor(() => expect(opened).toHaveLength(2));
    expect(opened[1].lastEventId).toBe('7'); // the hook remembered the high-water mark

    // Replayed (8) then live (9): both delivered once, in order.
    queue[1].frame(8, makeEventEnvelope({ id: 8, type: 'task.updated' }));
    queue[1].frame(9, makeEventEnvelope({ id: 9, type: 'task.updated' }));
    await waitFor(() => expect(events).toHaveLength(3));
    expect(events.map((event) => event.id)).toEqual([7, 8, 9]);
    await waitFor(() => expect(result.current.status).toBe('open'));
    expect(result.current.lastEventId).toBe(9);
  });

  it('reconnects after a clean stream end the same way', async () => {
    const { queue, opened } = installStreamQueue();
    renderHook(() =>
      useEventStream({ project: 'PID00001', onEvent: () => undefined, retryBaseDelayMs: 1 }),
    );

    await waitFor(() => expect(opened).toHaveLength(1));
    queue[0].frame(3, makeEventEnvelope({ id: 3 }));
    queue[0].close(); // proxy closed the stream without error

    await waitFor(() => expect(opened).toHaveLength(2));
    expect(opened[1].lastEventId).toBe('3');
  });

  it('transitions connecting → open → reconnecting → open', async () => {
    const { queue, opened } = installStreamQueue();
    const { result } = renderHook(() =>
      useEventStream({ project: 'PID00001', onEvent: () => undefined, retryBaseDelayMs: 1 }),
    );

    await waitFor(() => expect(opened).toHaveLength(1));
    expect(result.current.status).toBe('connecting');

    queue[0].frame(1, makeEventEnvelope({ id: 1 }));
    await waitFor(() => expect(result.current.status).toBe('open'));

    queue[0].fail(new Error('gone'));
    await waitFor(() => expect(result.current.status).toBe('reconnecting'));

    await waitFor(() => expect(opened).toHaveLength(2));
    queue[1].frame(2, makeEventEnvelope({ id: 2 }));
    await waitFor(() => expect(result.current.status).toBe('open'));
  });

  it('ignores unknown event types safely but still advances the resume position', async () => {
    const { queue, opened } = installStreamQueue();
    const events: EventEnvelope[] = [];
    renderHook(() =>
      useEventStream({
        project: 'PID00001',
        onEvent: (event) => events.push(event),
        retryBaseDelayMs: 1,
      }),
    );

    await waitFor(() => expect(opened).toHaveLength(1));
    queue[0].frame(4, makeEventEnvelope({ id: 4, type: 'task.exploded' }));
    queue[0].frame(5, makeEventEnvelope({ id: 5, type: 'system.alert', task_id: null }));
    await waitFor(() => expect(queue).toHaveLength(1)); // still no reconnect needed

    // The unknown type is dropped; the valid catalog type is forwarded.
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('system.alert');

    queue[0].close();
    await waitFor(() => expect(opened).toHaveLength(2));
    expect(opened[1].lastEventId).toBe('5'); // nothing is re-delivered on resume
  });

  it('aborts the connection and stops reconnecting on unmount', async () => {
    const { queue, opened } = installStreamQueue();
    const { unmount } = renderHook(() =>
      useEventStream({ project: 'PID00001', onEvent: () => undefined, retryBaseDelayMs: 1 }),
    );

    await waitFor(() => expect(opened).toHaveLength(1));
    queue[0].frame(1, makeEventEnvelope({ id: 1 }));

    unmount();
    queue[0].fail(new Error('after unmount'));
    // Give the loop every chance to misbehave, then prove it did not.
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(opened).toHaveLength(1);
  });
});
