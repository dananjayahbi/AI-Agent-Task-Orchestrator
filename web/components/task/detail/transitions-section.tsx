'use client';

/**
 * Transition history section (MT-4.6-03; Section 13.1 task-detail row —
 * "transitions history"; Principle P8 — read-only, append-only).
 *
 * Reverse-chronological rows from the task's transition record: actor,
 * from → to state, reason code and the server timestamp — exactly the
 * Section 7.2 fields. Reason codes render **verbatim** from the event
 * payload (Section 8.2 catalog, Section 20.5 — nothing invented); states
 * get display labels next to their canonical keys. Fetch-on-expand keeps
 * the first load light (Section 13.3/13.4); loading / empty / error
 * states are distinct (Section 20.3) with catalog-only copy
 * (Section 20.4 item 5).
 *
 * Source: the task-filtered `GET /events` history — see
 * `lib/queries/transitions.ts` for why the published event log is the
 * contract-faithful source (no `GET /tasks/{id}/transitions` exists).
 */
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/errors/error-state';
import { EmptyState } from '@/components/states/empty-state';
import { LoadingState } from '@/components/states/loading-state';
import { STATE_LABELS } from '@/lib/board/states';
import { resolveError } from '@/lib/errors';
import { useTaskTransitionHistoryQuery, type TransitionRow } from '@/lib/queries/transitions';

function actorLabel(row: TransitionRow): string {
  const ref = row.actorRef.trim();
  return ref === '' ? row.actorType : `${row.actorType}: ${ref}`;
}

function stateLabel(state: string): string {
  return state in STATE_LABELS ? STATE_LABELS[state as keyof typeof STATE_LABELS] : state;
}

function TransitionRowView({ row }: { row: TransitionRow }) {
  return (
    <li
      data-testid="transition-row"
      data-reason={row.reasonCode}
      className="grid gap-1 rounded-md border border-border bg-card p-2.5 text-card-foreground"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="font-medium text-foreground">
          <span className="font-mono" data-testid="transition-from">
            {stateLabel(row.fromState)}
          </span>
          <span aria-hidden="true" className="mx-1 text-muted-foreground">
            →
          </span>
          <span className="font-mono" data-testid="transition-to">
            {stateLabel(row.toState)}
          </span>
        </span>
        <time
          dateTime={row.occurredAt}
          data-testid="transition-timestamp"
          className="text-[11px] text-muted-foreground"
        >
          {new Date(row.occurredAt).toLocaleString()}
        </time>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
        <span data-testid="transition-actor" aria-label={`Actor ${actorLabel(row)}`}>
          {actorLabel(row)}
        </span>
        {/* Section 8.2 reason code, verbatim (Section 20.5). */}
        <span
          className="rounded-full bg-muted px-2 py-0.5 font-mono"
          data-testid="transition-reason"
        >
          {row.reasonCode}
        </span>
        {row.taskVersion !== null && <span>v{row.taskVersion}</span>}
      </div>
    </li>
  );
}

type TransitionsHistorySectionProps = {
  pid: string;
  taskId: string;
};

export function TransitionsHistorySection({ pid, taskId }: TransitionsHistorySectionProps) {
  const [expanded, setExpanded] = useState(false);
  const historyQuery = useTaskTransitionHistoryQuery(pid, taskId, expanded);

  return (
    <section
      data-testid="task-detail-section-transitions"
      aria-label="Transition history"
      className="grid gap-2"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">Transition history</h2>
        <Button
          size="sm"
          variant="outline"
          data-testid="transitions-toggle"
          aria-expanded={expanded}
          onClick={() => setExpanded((open) => !open)}
        >
          {expanded ? 'Hide' : 'Show'}
        </Button>
      </div>

      {!expanded ? (
        <p className="text-xs text-muted-foreground">
          Collapsed — open to load the append-only transition record (read-only).
        </p>
      ) : historyQuery.isPending ? (
        <LoadingState label="Loading transition history…" />
      ) : historyQuery.isError ? (
        <ErrorState
          title={resolveError(historyQuery.error).title}
          message={resolveError(historyQuery.error).message}
          requestId={resolveError(historyQuery.error).requestId}
          onRetry={() => void historyQuery.refetch()}
        />
      ) : historyQuery.data.length === 0 ? (
        <EmptyState
          title="No transitions recorded"
          description="State changes appear here as they are recorded by the server."
        />
      ) : (
        <ul className="grid gap-2" data-testid="transition-list">
          {historyQuery.data.map((row) => (
            <TransitionRowView key={row.id} row={row} />
          ))}
        </ul>
      )}
    </section>
  );
}
