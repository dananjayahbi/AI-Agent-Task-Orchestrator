'use client';

/**
 * SSE stream hook (MT-4.3-04; parent plan Section 13.3 "The stream hook
 * handles reconnect, last-event-id resume, and visible connection
 * status"; Section 9.6 wire contract).
 *
 * Transport: the OpenAPI-generated `GET /events/stream` operation only
 * (NFR-11 — no bespoke fetch layer). The generated SSE client parses
 * frames, tolerates heartbeat comment lines (they carry no `data:`, so
 * they never reach subscribers and never reset event state — Section 9.6,
 * MT-1.10-04) and aborts cleanly on `signal`.
 *
 * Reconnect + resume: this hook owns the loop (the generated client's
 * internal retry is disabled with `sseMaxRetryAttempts: 1` so there is
 * exactly one backoff authority). The highest received envelope id is
 * remembered and sent as the `Last-Event-ID` header on the next connect —
 * the backend contract accepts that header *or* the `last_event_id` query
 * parameter (MT-1.10-03); the header is used because it is the SSE
 * standard and passes through the generated client without inventing a
 * query parameter the schema does not expose. The server then replays the
 * missed events before switching to live (no gaps, no duplicates).
 *
 * Delivery discipline (separation for MT-4.3-05): parsed Section 9.6
 * envelopes are handed to `onEvent` — the hook never mutates any cache.
 * Unknown event types are ignored safely, but still advance the resume
 * position so a reconnect never re-delivers them.
 */
import { useEffect, useRef, useState } from 'react';

// The `@/lib/api` barrel (not the generated sdk directly): it carries the
// runtime client configuration — same-origin base URL, credentialed fetch —
// and is the NFR-11 entry point every UI-layer call uses.
import { apiV1EventsStreamRetrieve } from '@/lib/api';
import type { EventEnvelope } from '@/lib/api/generated/types.gen';
import { isCatalogEventType } from '@/lib/stream/event-catalog';

export type StreamStatus = 'connecting' | 'open' | 'reconnecting' | 'closed';

export type UseEventStreamOptions = {
  /**
   * Section 9.6 `project` filter — fixed for the subscription. Omit for
   * a cross-project subscription (the filters are optional in
   * Section 9.6; authorization still scopes the feed — MT-4.8-01's
   * review queue is the current consumer).
   */
  project?: string;
  /** Subscriber sink; kept in a ref so it never re-opens the stream. */
  onEvent: (event: EventEnvelope) => void;
  /** Reconnect backoff base (exponential, capped at 30 s). Test knob. */
  retryBaseDelayMs?: number;
};

const DEFAULT_RETRY_BASE_DELAY_MS = 1000;
const MAX_RETRY_DELAY_MS = 30_000;

/** Shape gate for one parsed `data:` payload. */
function parseEnvelope(data: unknown): EventEnvelope | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const candidate = data as Partial<EventEnvelope>;
  if (typeof candidate.id !== 'number' || !Number.isFinite(candidate.id)) {
    return null;
  }
  if (typeof candidate.type !== 'string') {
    return null;
  }
  return candidate as EventEnvelope;
}

export function useEventStream(options: UseEventStreamOptions): {
  status: StreamStatus;
  lastEventId: number | null;
} {
  const { project, onEvent, retryBaseDelayMs = DEFAULT_RETRY_BASE_DELAY_MS } = options;
  const [status, setStatus] = useState<StreamStatus>('connecting');
  const [lastEventId, setLastEventId] = useState<number | null>(null);

  const onEventRef = useRef(onEvent);
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    const controller = new AbortController();
    let disposed = false;
    let resumeFrom: number | null = null;
    let attempt = 0;

    const safeSetStatus = (next: StreamStatus) => {
      if (!disposed) setStatus(next);
    };
    const safeSetLastEventId = (next: number) => {
      if (!disposed) setLastEventId(next);
    };

    const backoff = () =>
      new Promise<void>((resolve) => {
        const delay = Math.min(retryBaseDelayMs * 2 ** attempt, MAX_RETRY_DELAY_MS);
        attempt += 1;
        const finish = () => {
          clearTimeout(timer);
          controller.signal.removeEventListener('abort', finish);
          resolve();
        };
        const timer = setTimeout(finish, delay);
        controller.signal.addEventListener('abort', finish);
      });

    void (async () => {
      while (!controller.signal.aborted) {
        safeSetStatus(resumeFrom === null ? 'connecting' : 'reconnecting');
        try {
          const { stream } = await apiV1EventsStreamRetrieve({
            ...(project !== undefined && project !== '' ? { query: { project } } : {}),
            ...(resumeFrom !== null ? { headers: { 'Last-Event-ID': String(resumeFrom) } } : {}),
            signal: controller.signal,
            // One backoff authority: the hook loop below, not the client.
            sseMaxRetryAttempts: 1,
          });
          for await (const data of stream) {
            const envelope = parseEnvelope(data);
            if (envelope === null) {
              continue;
            }
            attempt = 0; // stream progress resets the backoff ladder
            if (resumeFrom === null || envelope.id > resumeFrom) {
              resumeFrom = envelope.id;
              safeSetLastEventId(resumeFrom);
            }
            safeSetStatus('open');
            if (isCatalogEventType(envelope.type)) {
              onEventRef.current(envelope);
            }
          }
          if (controller.signal.aborted) {
            break;
          }
          // Clean end (server/proxy closed the stream): reconnect + resume.
        } catch {
          if (controller.signal.aborted) {
            break;
          }
          // Network/parsing failure: fall through to the backoff above.
        }
        await backoff();
      }
      safeSetStatus('closed');
    })();

    return () => {
      disposed = true;
      controller.abort();
    };
  }, [project, retryBaseDelayMs]);

  return { status, lastEventId };
}
