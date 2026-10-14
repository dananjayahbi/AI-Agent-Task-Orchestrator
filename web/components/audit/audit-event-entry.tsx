/**
 * One audit-log entry (MT-4.10-01; Sections 12.5, 7.2, ADR-010).
 *
 * Read-only by construction (Section 12.5 / Principle P8): the only
 * interactive control is the payload expander — nothing here can edit or
 * delete a row. Each entry shows the canonical event type **and** its
 * friendly label (labels never replace canonical values — ADR-010), the
 * server UTC instant verbatim (Section 0.4), the actor
 * (`actor_type` · `actor_ref`, rendered as text — never enriched, per
 * the P10-adjacent risk note), project/task links when the envelope
 * carries them, and the monotonic event id.
 *
 * **Recorded contract gap:** Section 12.5 mentions a correlation id, but
 * the Section 9.6 wire envelope has no correlation-id field — the
 * viewer therefore displays the event's monotonic `id` (the log's own
 * key) rather than inventing one (noted in the WP changelog).
 *
 * Payloads (Section 7.2 `data`) are collapsed by default and rendered
 * only when expanded (RISK-13: arbitrary JSON size must not burden the
 * default render). Unknown/forward types render raw without crashing.
 */
import Link from 'next/link';
import { useState } from 'react';

import { eventLabel } from '@/lib/audit/event-labels';
import type { EventEnvelope } from '@/lib/api/generated/types.gen';

function LinkCell({ href, value }: { href: string; value: string }) {
  return (
    <Link href={href} className="font-mono text-xs text-primary underline-offset-2 hover:underline">
      {value}
    </Link>
  );
}

export function AuditEventEntry({ event }: { event: EventEnvelope }) {
  const [payloadOpen, setPayloadOpen] = useState(false);
  const label = eventLabel(event.type);
  const projectId =
    typeof event.project_id === 'string' && event.project_id !== '' ? event.project_id : null;
  const taskId = typeof event.task_id === 'string' && event.task_id !== '' ? event.task_id : null;

  return (
    <li
      data-testid="audit-event-entry"
      data-event-type={event.type}
      className="rounded-lg border border-border bg-card p-3"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex flex-wrap items-baseline gap-2">
          {label !== null && (
            <span className="text-sm font-medium text-card-foreground">{label}</span>
          )}
          <code className="text-xs text-muted-foreground">{event.type}</code>
        </div>
        <time dateTime={event.occurred_at} className="font-mono text-xs text-muted-foreground">
          {event.occurred_at}
        </time>
      </div>

      <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-4">
        <div>
          <dt className="text-xs text-muted-foreground">Actor</dt>
          <dd className="break-all text-sm text-card-foreground">
            {event.actor.type}
            {event.actor.ref !== '' ? ` · ${event.actor.ref}` : ''}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Project</dt>
          <dd className="text-sm text-card-foreground">
            {projectId !== null ? (
              <LinkCell href={`/projects/${projectId}`} value={projectId} />
            ) : (
              '–'
            )}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Task</dt>
          <dd className="text-sm text-card-foreground">
            {projectId !== null && taskId !== null ? (
              <LinkCell href={`/projects/${projectId}/tasks/${taskId}`} value={taskId} />
            ) : (
              '–'
            )}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Event ID</dt>
          <dd className="font-mono text-sm text-card-foreground">#{event.id}</dd>
        </div>
      </dl>

      <button
        type="button"
        aria-expanded={payloadOpen}
        onClick={() => setPayloadOpen((open) => !open)}
        className="mt-2 text-xs text-primary underline-offset-2 hover:underline"
      >
        {payloadOpen ? 'Hide payload' : 'Show payload'}
      </button>
      {payloadOpen && (
        <pre
          data-testid="audit-event-payload"
          className="mt-2 max-h-64 overflow-auto rounded bg-muted p-2 text-xs text-card-foreground"
        >
          {JSON.stringify(event.data, null, 2)}
        </pre>
      )}
    </li>
  );
}
