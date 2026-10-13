'use client';

/**
 * Board toolbar (MT-4.3-03; Section 13.1 "filters, search, archive
 * toggle").
 *
 * Binding discipline: the priority select, the state checkboxes and the
 * archive toggle map 1:1 onto `GET /projects/{pid}/tasks` query parameters
 * as exposed by the generated client (NFR-11) — nothing is invented
 * server-side. The search input is explicitly client-side over the loaded
 * board set (the contract has no server search; OQ-4.3-01), labelled as
 * such so the behaviour is never mistaken for a server query.
 *
 * State composition: every control writes one `BoardFilters` value the
 * board feeds into the query key (server half) and the render predicate
 * (client half); "Clear" restores the documented defaults, archive
 * included (Section 8.2 T19: hidden by default).
 */
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { PriorityEnum } from '@/lib/api/generated/types.gen';
import {
  DEFAULT_BOARD_FILTERS,
  isDefaultBoardFilters,
  type BoardFilters,
} from '@/lib/board/filters';
import { BOARD_STATES, STATE_LABELS } from '@/lib/board/states';

const PRIORITY_OPTIONS: ReadonlyArray<{ value: PriorityEnum; label: string }> = [
  { value: 'urgent', label: 'Urgent' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

type BoardFiltersProps = {
  filters: BoardFilters;
  onChange: (filters: BoardFilters) => void;
};

export function BoardFiltersBar({ filters, onChange }: BoardFiltersProps) {
  const toggleState = (state: (typeof BOARD_STATES)[number], checked: boolean) => {
    const states = checked
      ? [...filters.states, state]
      : filters.states.filter((candidate) => candidate !== state);
    onChange({ ...filters, states });
  };

  return (
    <div
      data-testid="board-filters"
      className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-card p-3"
    >
      <label className="flex min-w-48 flex-1 flex-col gap-1 text-xs font-medium text-muted-foreground">
        Search loaded tasks
        <Input
          data-testid="board-search"
          type="search"
          value={filters.search}
          placeholder="Id or title substring"
          title="Client-side search over the loaded board set — the API contract has no server search (OQ-4.3-01)"
          onChange={(event) => onChange({ ...filters, search: event.target.value })}
        />
      </label>

      <label className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
        Priority
        <select
          data-testid="board-priority-filter"
          value={filters.priority ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              priority: event.target.value === '' ? null : (event.target.value as PriorityEnum),
            })
          }
          className="h-9 rounded-md border border-input bg-transparent px-2 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          <option value="">All priorities</option>
          {PRIORITY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <fieldset className="flex flex-col gap-1">
        <legend className="text-xs font-medium text-muted-foreground">States</legend>
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          {BOARD_STATES.map((state) => (
            <label
              key={state}
              className="flex items-center gap-1 text-xs text-foreground"
              data-testid={`board-state-filter-label-${state}`}
            >
              <input
                type="checkbox"
                data-testid={`board-state-filter-${state}`}
                checked={filters.states.includes(state)}
                onChange={(event) => toggleState(state, event.target.checked)}
              />
              {STATE_LABELS[state]}
            </label>
          ))}
        </div>
      </fieldset>

      <label
        className="flex items-center gap-2 pb-2 text-xs font-medium text-foreground"
        data-testid="board-archive-toggle-label"
      >
        <input
          type="checkbox"
          data-testid="board-archive-toggle"
          checked={filters.includeArchived}
          onChange={(event) => onChange({ ...filters, includeArchived: event.target.checked })}
        />
        Show archived
      </label>

      <Button
        data-testid="board-clear-filters"
        variant="outline"
        size="sm"
        disabled={isDefaultBoardFilters(filters)}
        onClick={() =>
          onChange({ ...DEFAULT_BOARD_FILTERS, states: [...DEFAULT_BOARD_FILTERS.states] })
        }
      >
        Clear filters
      </Button>

      <p className="basis-full text-[11px] text-muted-foreground">
        Filters and the archive toggle are server-side (tasks API contract); search filters the
        loaded board set client-side (OQ-4.3-01).
      </p>
    </div>
  );
}
