/**
 * Sessions list body of the Agents panel (MT-4.9-01; Section 13.1).
 *
 * Composition: the query hook derives rows from canonical task/lease
 * state plus `GET /events` history (see `lib/queries/agent-sessions`),
 * and the live hook keeps them current **over the SSE stream** — no
 * polling (the MT's "live" caveat: updates arrive as events, and a
 * partially-described claim schedules one single-task refetch).
 *
 * The two sections implement AC 1: active (`ended_at === null`) and
 * recently ended, each with its own empty state (Section 20.3 keeps the
 * states separated). The ended list is capped (RISK-13) rather than
 * growing without bound.
 */
'use client';

import { StreamStatusIndicator } from '@/components/board/stream-status';
import { ErrorState } from '@/components/errors/error-state';
import { SessionRow } from '@/components/panels/session-row';
import { EmptyState } from '@/components/states/empty-state';
import { LoadingState } from '@/components/states/loading-state';
import { resolveError } from '@/lib/errors';
import { DEFAULT_STALLED_AFTER_MINUTES } from '@/lib/board/stalled';
import { useAgentSessionsLive, useAgentSessionsQuery } from '@/lib/queries/agent-sessions';
import { usePolicyQuery } from '@/lib/queries/policy';

/** Newest-ended cap for the list (RISK-13: bounded, not unbounded growth). */
const ENDED_DISPLAY_LIMIT = 50;

export function SessionsView({ pid }: { pid: string }) {
  const sessions = useAgentSessionsQuery(pid);
  const { status } = useAgentSessionsLive(pid);
  // Section 7.2 threshold, re-read through the policy cache (MT-4.9-03
  // risk note: a mid-view policy change must reach the indicator). A
  // policy load failure falls back to the documented default — it never
  // takes the sessions panel down with it.
  const policy = usePolicyQuery(pid);
  const stalledAfterMinutes = policy.data?.stalled_after_minutes ?? DEFAULT_STALLED_AFTER_MINUTES;

  if (sessions.isPending) {
    return <LoadingState label="Loading sessions…" />;
  }

  if (sessions.isError) {
    const friendly = resolveError(sessions.error);
    return (
      <ErrorState
        title={friendly.title}
        message={friendly.message}
        requestId={friendly.requestId}
        onRetry={() => void sessions.refetch()}
      />
    );
  }

  const active = sessions.data.filter((row) => row.endedAt === null);
  const ended = sessions.data.filter((row) => row.endedAt !== null).slice(0, ENDED_DISPLAY_LIMIT);

  return (
    <div data-testid="agents-panel" className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <StreamStatusIndicator status={status} />
        <span className="text-xs text-muted-foreground">
          Session updates arrive over the live event stream — this panel does not poll.
        </span>
      </div>

      <section aria-labelledby="active-sessions-heading">
        <h2 id="active-sessions-heading" className="text-base font-semibold text-foreground">
          Active sessions{' '}
          <span className="font-normal text-muted-foreground">({active.length})</span>
        </h2>
        {active.length === 0 ? (
          <div className="mt-3">
            <EmptyState
              title="No active sessions"
              description="Agents appear here while they hold a lease on an in-progress or audit task."
            />
          </div>
        ) : (
          <ul className="mt-3 flex flex-col gap-3">
            {active.map((row) => (
              <SessionRow
                key={row.sessionId}
                row={row}
                variant="active"
                stalledAfterMinutes={stalledAfterMinutes}
              />
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="ended-sessions-heading">
        <h2 id="ended-sessions-heading" className="text-base font-semibold text-foreground">
          Recently ended <span className="font-normal text-muted-foreground">({ended.length})</span>
        </h2>
        {ended.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">No recently ended sessions.</p>
        ) : (
          <ul className="mt-3 flex flex-col gap-3">
            {ended.map((row) => (
              <SessionRow
                key={row.sessionId}
                row={row}
                variant="ended"
                stalledAfterMinutes={stalledAfterMinutes}
              />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
