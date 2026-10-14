/**
 * Audit-log filter controls (MT-4.10-02; Sections 13.1 "Filterable event
 * history", 19 WP-4.10's five filters, 9.2, 20.4 item 4).
 *
 * **Contract-first mapping (AC 2; the MT risk note):** the OpenAPI
 * operation for `GET /events` publishes exactly two filter parameters —
 * `project` and `task` (verified against the generated client). Those
 * two are wired 1:1. The other three Section 19 dimensions (actor, date
 * range on `created_at`, event type) render as disabled controls with a
 * visible contract-change note: they are **raised, not emulated**
 * client-side — post-filtering a capped cursor walk would silently lie
 * about completeness on a one-year retention log (Section 12.4). The
 * type select still enumerates ONLY Section 9.6 catalog values (20.4
 * item 6) so the option list is ready the moment the parameter lands.
 *
 * Chips summarize the active filters with individual clear + clear-all
 * (Section 20.3). All controls read/write the URL-synced filter object
 * the container owns — no local filter state, so refresh/share always
 * reproduces the view.
 */
'use client';

import type { ChangeEvent, KeyboardEvent } from 'react';

import { EVENT_CATALOG } from '@/lib/stream/event-catalog';
import { useProjectsQuery } from '@/lib/queries/projects';
import type { AuditLogFilters } from '@/lib/queries/audit-events';

/** Verbatim in every disabled control's note (Sections 9.2/20.4 item 4). */
export const EVENTS_FILTER_CONTRACT_NOTE =
  'Requires a GET /events contract change: Section 9.2 publishes only the `project` and `task` query parameters — raised, not emulated client-side.';

type AuditLogFiltersBarProps = {
  filters: AuditLogFilters;
  onChange: (next: AuditLogFilters) => void;
  onClearAll: () => void;
};

function Chip({ label, value, onClear }: { label: string; value: string; onClear: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
      {label}: <span className="font-mono text-foreground">{value}</span>
      <button
        type="button"
        aria-label={`Clear ${label} filter`}
        onClick={onClear}
        className="text-muted-foreground hover:text-foreground"
      >
        ×
      </button>
    </span>
  );
}

export function AuditLogFiltersBar({ filters, onChange, onClearAll }: AuditLogFiltersBarProps) {
  const projects = useProjectsQuery();
  const hasFilters = filters.project !== null || filters.task !== null;

  function commitTask(input: HTMLInputElement) {
    const value = input.value.trim();
    const next = value === '' ? null : value;
    if (next !== filters.task) {
      onChange({ ...filters, task: next });
    }
  }

  return (
    <div
      data-testid="audit-log-filters"
      className="flex flex-col gap-3 rounded-lg border border-border bg-card p-3"
    >
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Project
          <select
            aria-label="Filter by project"
            data-testid="audit-filter-project"
            value={filters.project ?? ''}
            onChange={(event: ChangeEvent<HTMLSelectElement>) => {
              const value = event.target.value;
              onChange({ ...filters, project: value === '' ? null : value });
            }}
            className="h-9 max-w-64 rounded-md border border-border bg-background px-2 text-sm text-foreground"
          >
            <option value="">All projects</option>
            {(projects.data ?? []).map((project) => (
              <option key={project.id} value={project.id}>
                {project.id} — {project.name}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Task ID
          <input
            // Keyed by the committed value: a chip/clear-all remounts the
            // uncontrolled input so its draft can never outlive the URL.
            key={filters.task ?? ''}
            data-testid="audit-filter-task"
            type="text"
            defaultValue={filters.task ?? ''}
            placeholder="Any task"
            onKeyDown={(event: KeyboardEvent<HTMLInputElement>) => {
              if (event.key === 'Enter') {
                commitTask(event.currentTarget);
              }
            }}
            onBlur={(event) => commitTask(event.currentTarget)}
            className="h-9 w-56 rounded-md border border-border bg-background px-2 font-mono text-sm text-foreground"
          />
        </label>

        <label
          className="flex flex-col gap-1 text-xs text-muted-foreground"
          title={EVENTS_FILTER_CONTRACT_NOTE}
        >
          Actor
          <select
            aria-label="Filter by actor (requires contract change)"
            data-testid="audit-filter-actor"
            disabled
            className="h-9 rounded-md border border-border bg-background px-2 text-sm text-muted-foreground opacity-60"
          >
            <option value="">All actors</option>
            <option value="owner">owner</option>
            <option value="agent">agent</option>
            <option value="system">system</option>
          </select>
        </label>

        <label
          className="flex flex-col gap-1 text-xs text-muted-foreground"
          title={EVENTS_FILTER_CONTRACT_NOTE}
        >
          From (UTC)
          <input
            aria-label="Filter from date (requires contract change)"
            data-testid="audit-filter-from"
            type="date"
            disabled
            className="h-9 rounded-md border border-border bg-background px-2 text-sm text-muted-foreground opacity-60"
          />
        </label>

        <label
          className="flex flex-col gap-1 text-xs text-muted-foreground"
          title={EVENTS_FILTER_CONTRACT_NOTE}
        >
          To (UTC)
          <input
            aria-label="Filter to date (requires contract change)"
            data-testid="audit-filter-to"
            type="date"
            disabled
            className="h-9 rounded-md border border-border bg-background px-2 text-sm text-muted-foreground opacity-60"
          />
        </label>

        <label
          className="flex flex-col gap-1 text-xs text-muted-foreground"
          title={EVENTS_FILTER_CONTRACT_NOTE}
        >
          Event type
          <select
            aria-label="Filter by event type (requires contract change)"
            data-testid="audit-filter-type"
            disabled
            className="h-9 max-w-64 rounded-md border border-border bg-background px-2 text-sm text-muted-foreground opacity-60"
          >
            <option value="">All types</option>
            {EVENT_CATALOG.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p data-testid="audit-filter-contract-note" className="text-xs text-muted-foreground">
        {EVENTS_FILTER_CONTRACT_NOTE}
      </p>

      {hasFilters && (
        <div className="flex flex-wrap items-center gap-2" data-testid="audit-filter-chips">
          {filters.project !== null && (
            <Chip
              label="Project"
              value={filters.project}
              onClear={() => onChange({ ...filters, project: null })}
            />
          )}
          {filters.task !== null && (
            <Chip
              label="Task"
              value={filters.task}
              onClear={() => onChange({ ...filters, task: null })}
            />
          )}
          <button
            type="button"
            data-testid="audit-filter-clear-all"
            onClick={onClearAll}
            className="text-xs text-primary underline-offset-2 hover:underline"
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  );
}
