/**
 * Stream connection status (MT-4.3-04 consumer; Section 13.3 "visible
 * connection status"). Placement/styling lives with the board (MT-4.3-04
 * out-of-scope note) — the hook itself only exposes the status value.
 */
import { cn } from 'cn';
import type { StreamStatus } from '@/lib/stream/use-event-stream';

const STATUS_COPY: Record<StreamStatus, string> = {
  connecting: 'Connecting…',
  open: 'Live',
  reconnecting: 'Reconnecting…',
  closed: 'Offline',
};

const STATUS_DOT: Record<StreamStatus, string> = {
  connecting: 'bg-muted-foreground',
  open: 'bg-primary',
  reconnecting: 'bg-muted-foreground animate-pulse',
  closed: 'bg-destructive',
};

export function StreamStatusIndicator({ status }: { status: StreamStatus }) {
  return (
    <span
      data-testid="stream-status"
      data-status={status}
      role="status"
      aria-live="polite"
      className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"
    >
      <span aria-hidden="true" className={cn('size-2 rounded-full', STATUS_DOT[status])} />
      {STATUS_COPY[status]}
    </span>
  );
}
