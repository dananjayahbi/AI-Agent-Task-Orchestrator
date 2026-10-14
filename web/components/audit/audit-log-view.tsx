/**
 * Audit log viewer (MT-4.10-01; Sections 13.1 "Filterable event
 * history", 12.5 read-only).
 *
 * A pure read of the append-only event log: REST fetch through the
 * generated client, no SSE subscription (stream-down cannot affect a
 * history view), no mutation affordances anywhere. The filter set is a
 * prop — MT-4.10-02 wires the controls and URL state; the default is the
 * full visible history. Loading / empty / error are separated per
 * Section 20.3 and error copy comes only from the catalog (20.4 item 5).
 */
'use client';

import { AuditEventEntry } from '@/components/audit/audit-event-entry';
import { ErrorState } from '@/components/errors/error-state';
import { EmptyState } from '@/components/states/empty-state';
import { LoadingState } from '@/components/states/loading-state';
import { Button } from '@/components/ui/button';
import { resolveError } from '@/lib/errors';
import {
  NO_AUDIT_FILTERS,
  useAuditEventsQuery,
  type AuditLogFilters,
} from '@/lib/queries/audit-events';

export function AuditLogView({
  filters = NO_AUDIT_FILTERS,
  onClearFilters,
}: {
  filters?: AuditLogFilters;
  /** MT-4.10-02: lets the filtered-empty state offer a reset. */
  onClearFilters?: () => void;
}) {
  const events = useAuditEventsQuery(filters);

  if (events.isPending) {
    return <LoadingState label="Loading events…" />;
  }

  if (events.isError) {
    const friendly = resolveError(events.error);
    return (
      <ErrorState
        title={friendly.title}
        message={friendly.message}
        requestId={friendly.requestId}
        onRetry={() => void events.refetch()}
      />
    );
  }

  if (events.data.length === 0) {
    // Section 20.3: "no results for these filters" is not "the log is
    // empty" — the filtered state offers the reset (MT-4.10-02).
    const filtersActive = filters.project !== null || filters.task !== null;
    if (filtersActive) {
      return (
        <EmptyState
          title="No events match these filters"
          description="Try a different project or task — or clear the filters to see the full history."
          action={
            onClearFilters !== undefined ? (
              <Button variant="outline" size="sm" onClick={onClearFilters}>
                Clear filters
              </Button>
            ) : undefined
          }
        />
      );
    }
    return (
      <EmptyState
        title="No events yet"
        description="State changes, review decisions and policy edits appear here as they are recorded."
      />
    );
  }

  return (
    <ul data-testid="audit-log-list" className="flex flex-col gap-2">
      {events.data.map((event) => (
        <AuditEventEntry key={event.id} event={event} />
      ))}
    </ul>
  );
}
