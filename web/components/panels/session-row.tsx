/**
 * One session row in the Agents panel (MT-4.9-01; Section 13.1 "Live
 * sessions, current leases").
 *
 * Renders the Section 9.2 AgentSession fields the Owner-facing contract
 * exposes (`agent_label`, `client_name`, `capability`, `transport`,
 * `started_at`, `last_seen_at`, `ended_at`) plus the canonical task/lease
 * join held by the session. Contract-gap honesty: `client_name`,
 * `capability` and `transport` exist only on the server AgentSession row
 * (no `GET /agent-sessions` publishes them) — until a read endpoint lands
 * they render as "–", never invented client values (recorded in the WP
 * changelog).
 */
import { LeaseCountdown } from '@/components/panels/lease-countdown';
import { StalledIndicator } from '@/components/panels/stalled-indicator';
import { STATE_LABELS } from '@/lib/board/states';
import type { AgentSessionRow } from '@/lib/queries/agent-sessions';

function formatInstant(value: string | null): string {
  return value === null ? '–' : new Date(value).toLocaleString();
}

/** Free-form string field (client_name / capability / transport). */
function TextField({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm text-card-foreground">{value ?? '–'}</dd>
    </div>
  );
}

/** Server instant field (started_at / last_seen_at / ended_at). */
function DateField({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm text-card-foreground">{formatInstant(value)}</dd>
    </div>
  );
}

export function SessionRow({
  row,
  variant,
  stalledAfterMinutes,
}: {
  row: AgentSessionRow;
  variant: 'active' | 'ended';
  /** Section 7.2 policy threshold (MT-4.9-03); view reads it live. */
  stalledAfterMinutes: number;
}) {
  const ended = variant === 'ended';
  return (
    <li
      data-testid={ended ? 'session-ended-row' : 'session-row'}
      data-session-id={row.sessionId}
      className="rounded-lg border border-border bg-card p-4"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex flex-wrap items-baseline gap-2">
          <span className="font-medium text-card-foreground">{row.agentLabel ?? '–'}</span>
          <span className="font-mono text-xs text-muted-foreground">{row.sessionId}</span>
          {ended && (
            <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
              Ended
            </span>
          )}
        </div>
        <span className="text-xs text-muted-foreground">
          Started {formatInstant(row.startedAt)}
        </span>
      </div>

      <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-4">
        <TextField label="Client" value={row.clientName} />
        <TextField label="Capability" value={row.capability} />
        <TextField label="Transport" value={row.transport} />
        <DateField label="Last seen" value={row.lastSeenAt} />
        {ended && <DateField label="Ended" value={row.endedAt} />}
      </dl>

      {row.joins.length > 0 && (
        <ul
          className="mt-3 flex flex-col gap-2 border-t border-border pt-3"
          aria-label={`Current leases for ${row.sessionId}`}
        >
          {row.joins.map((join) => (
            <li
              key={join.taskId}
              data-testid="session-lease"
              className="flex flex-wrap items-center gap-2"
            >
              <span className="font-mono text-xs text-muted-foreground">{join.taskId}</span>
              <span className="text-sm text-card-foreground">{join.taskTitle}</span>
              <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                {join.claimedRole}
              </span>
              <span className="text-xs text-muted-foreground">{STATE_LABELS[join.taskState]}</span>
              <LeaseCountdown
                acquiredAt={join.leaseAcquiredAt}
                expiresAt={join.leaseExpiresAt}
                expiring={join.leaseExpiring}
              />
              <StalledIndicator join={join} stalledAfterMinutes={stalledAfterMinutes} />
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
