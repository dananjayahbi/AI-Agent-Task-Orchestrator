'use client';

/**
 * Checkpoint feed (MT-4.6-02; Section 13.2 "Checkpoint feed:
 * reverse-chronological live list with percent, message, token usage,
 * and auto-scroll toggle").
 *
 * Rows render exactly the Section 7.2 Task Checkpoint fields: `message`,
 * `percent` (0-100, nullable — never drawn as 0 when absent), free-JSON
 * `token_usage` (rendered defensively: primitive entries as `key value`
 * pairs, unknown shapes collapsed to nothing — no invented schema; MT
 * risk note), `kind` (`progress` / `liveness` / `system`) and the server
 * `timestamp`.
 *
 * Data flow: the first page comes from `GET /tasks/{id}/checkpoints`
 * (cursor-gated); older pages load on demand; live rows arrive via
 * `task.checkpoint` events patched into the same cache entry by
 * `useTaskDetailLiveUpdates` (Section 13.3 — no refetch-per-event) and
 * dedupe on reconnect replay (Section 9.6). The stream connection
 * status (Section 13.3 hook contract) shows as a disconnected
 * indicator without blocking the history already on screen.
 *
 * Auto-scroll: newest-at-top is the default reading order, so "follow"
 * scrolls the newest row into view when it arrives. The toggle persists
 * per user session (`sessionStorage` — the MT risk note's recorded
 * default; account-level persistence would need a backend preference).
 */
import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/errors/error-state';
import { EmptyState } from '@/components/states/empty-state';
import { LoadingState } from '@/components/states/loading-state';
import type { Checkpoint } from '@/lib/api/generated/types.gen';
import { resolveError } from '@/lib/errors';
import { loadOlderCheckpoints, useTaskCheckpointsQuery } from '@/lib/queries/checkpoints';
import type { StreamStatus } from '@/lib/stream/use-event-stream';
import { cn } from 'cn';

const FOLLOW_STORAGE_KEY = 'task-detail:checkpoint-follow';

/** Session-scoped follow toggle (Section 13.2; MT risk note: session default). */
function readFollowPref(): boolean {
  if (typeof window === 'undefined') return true;
  try {
    return window.sessionStorage.getItem(FOLLOW_STORAGE_KEY) !== 'off';
  } catch {
    return true; // storage unavailable (privacy mode) — default stands
  }
}

function writeFollowPref(value: boolean): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(FOLLOW_STORAGE_KEY, value ? 'on' : 'off');
  } catch {
    // Persistence is best-effort; the in-memory toggle still works.
  }
}

/** Section 7.2: percent is nullable — absent renders as "unknown", never 0. */
function percentLabel(percent: number | null): string {
  return percent === null ? 'Progress unknown' : `${Math.round(percent)}%`;
}

/**
 * `token_usage` is free JSON (Section 7.2) — render primitive entries
 * as `key: value` pairs and nothing for shapes we cannot name (MT risk
 * note: no invented schema; the payload is WP-1.8's pass-through
 * storage, so any key the agent reported renders verbatim).
 */
function tokenUsageLabel(usage: unknown): string | null {
  if (usage === null || usage === undefined) return null;
  if (typeof usage !== 'object' || Array.isArray(usage)) return null;
  const entries = Object.entries(usage as Record<string, unknown>).filter(([, value]) => {
    const kind = typeof value;
    return kind === 'string' || kind === 'number' || kind === 'boolean';
  });
  if (entries.length === 0) return null;
  return entries.map(([key, value]) => `${key}: ${String(value)}`).join(' · ');
}

const KIND_LABELS: Record<string, string> = {
  progress: 'Progress',
  liveness: 'Liveness',
  system: 'System',
};

export function CheckpointRow({ checkpoint }: { checkpoint: Checkpoint }) {
  const tokens = tokenUsageLabel(checkpoint.token_usage);
  return (
    <li
      data-testid="checkpoint-row"
      data-kind={checkpoint.kind}
      className="rounded-md border border-border bg-card p-2.5 text-card-foreground"
    >
      <div className="flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
        <span data-testid="checkpoint-kind">{KIND_LABELS[checkpoint.kind] ?? checkpoint.kind}</span>
        <time dateTime={checkpoint.timestamp} data-testid="checkpoint-timestamp">
          {new Date(checkpoint.timestamp).toLocaleString()}
        </time>
      </div>
      <p data-testid="checkpoint-message" className="mt-1 text-sm break-words">
        {checkpoint.message === '' ? (
          <span className="text-muted-foreground">No message</span>
        ) : (
          checkpoint.message
        )}
      </p>
      <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
        <span data-testid="checkpoint-percent">{percentLabel(checkpoint.percent)}</span>
        {tokens !== null && (
          <span data-testid="checkpoint-tokens" title="Reported token accounting">
            {tokens}
          </span>
        )}
      </div>
    </li>
  );
}

type CheckpointFeedProps = {
  pid: string;
  taskId: string;
  /** Section 13.3 visible connection status from the view's stream hook. */
  streamStatus: StreamStatus;
};

export function CheckpointFeed({ pid, taskId, streamStatus }: CheckpointFeedProps) {
  const queryClient = useQueryClient();
  const feedQuery = useTaskCheckpointsQuery(pid, taskId);
  const [follow, setFollow] = useState(readFollowPref);
  const listRef = useRef<HTMLUListElement | null>(null);
  const newestId = feedQuery.data?.rows[0]?.id ?? null;
  const [loadingOlder, setLoadingOlder] = useState(false);

  // Follow behavior: keep the newest row in view when it arrives.
  useEffect(() => {
    if (!follow) return;
    listRef.current?.scrollIntoView?.({ block: 'start' });
  }, [follow, newestId]);

  if (feedQuery.isPending) {
    return <LoadingState label="Loading checkpoints…" />;
  }
  if (feedQuery.isError) {
    const friendly = resolveError(feedQuery.error);
    return (
      <ErrorState
        title={friendly.title}
        message={friendly.message}
        requestId={friendly.requestId}
        onRetry={() => void feedQuery.refetch()}
      />
    );
  }

  const { rows, nextCursor } = feedQuery.data;

  return (
    <div className="grid gap-3" data-testid="checkpoint-feed">
      <div className="flex items-center justify-between gap-2">
        <span
          data-testid="checkpoint-feed-stream"
          data-status={streamStatus}
          role="status"
          aria-live="polite"
          className={cn(
            'inline-flex items-center gap-1.5 text-xs',
            streamStatus === 'closed' || streamStatus === 'reconnecting'
              ? 'text-destructive'
              : 'text-muted-foreground',
          )}
        >
          <span
            aria-hidden="true"
            className={cn(
              'size-2 rounded-full',
              streamStatus === 'open'
                ? 'bg-primary'
                : streamStatus === 'closed'
                  ? 'bg-destructive'
                  : 'animate-pulse bg-muted-foreground',
            )}
          />
          {streamStatus === 'open'
            ? 'Live'
            : streamStatus === 'closed'
              ? 'Updates paused — reload to refresh'
              : 'Reconnecting…'}
        </span>
        <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <input
            type="checkbox"
            data-testid="checkpoint-feed-follow"
            checked={follow}
            onChange={(event) => {
              setFollow(event.target.checked);
              writeFollowPref(event.target.checked);
            }}
            className="size-3.5 accent-primary"
          />
          Follow newest
        </label>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          title="No checkpoints yet"
          description="Progress reports from the worker will appear here as they arrive."
        />
      ) : (
        <ul ref={listRef} data-testid="checkpoint-feed-list" className="grid gap-2">
          {rows.map((checkpoint) => (
            <CheckpointRow key={checkpoint.id} checkpoint={checkpoint} />
          ))}
        </ul>
      )}

      {nextCursor !== null && rows.length > 0 && (
        <Button
          variant="outline"
          size="sm"
          data-testid="checkpoint-feed-older"
          disabled={loadingOlder}
          onClick={() => {
            setLoadingOlder(true);
            void loadOlderCheckpoints(queryClient, pid, taskId)
              .catch(() => undefined)
              .finally(() => setLoadingOlder(false));
          }}
        >
          {loadingOlder ? 'Loading…' : 'Load older checkpoints'}
        </Button>
      )}
    </div>
  );
}
