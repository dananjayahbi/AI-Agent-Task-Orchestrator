/**
 * Board filter model (MT-4.3-03; Section 13.1 "filters, search, archive
 * toggle"; Section 8.2 T19 archive default).
 *
 * Two strict rules shape this module:
 *
 *  1. **Only contract parameters leave the client.** `priority`, `state`
 *     and `include_archived` are the exact query parameters of
 *     `GET /projects/{pid}/tasks` as generated from schemas/openapi.yaml
 *     (NFR-11). Nothing is invented server-side.
 *  2. **Search is client-side.** The contract has no server search
 *     parameter, so the search box filters the already-loaded board set by
 *     id/title (recorded as OQ-4.3-01 in the WP changelog). Server-side
 *     search would be a backend contract change (Section 9.2), not a web
 *     silently-faked semantic.
 *
 * The server-side part of the filters participates in the react-query key
 * (a filter change refetches through the query cache, Section 13.3); the
 * client-side part is a pure predicate over whatever the cache holds.
 */
import type { PriorityEnum, Task } from '@/lib/api/generated/types.gen';
import { ALL_BOARD_STATES, BOARD_STATES, type BoardState } from '@/lib/board/states';

/** Everything the board UI can narrow by. */
export type BoardFilters = {
  /** Single-value contract filter; null = every priority. */
  priority: PriorityEnum | null;
  /** Contract `state` filter; all six (or empty) = no state filter. */
  states: BoardState[];
  /** Contract `include_archived`; default false — T19 "hidden from boards by default". */
  includeArchived: boolean;
  /** Client-side only (OQ-4.3-01): substring match on id/title. */
  search: string;
};

/** The server-addressable half — the react-query cache identity part. */
export type BoardServerFilters = Omit<BoardFilters, 'search'>;

export const DEFAULT_BOARD_FILTERS: BoardFilters = {
  priority: null,
  states: [...ALL_BOARD_STATES],
  includeArchived: false,
  search: '',
};

export function defaultServerFilters(): BoardServerFilters {
  return {
    priority: null,
    states: [...ALL_BOARD_STATES],
    includeArchived: false,
  };
}

export function serverFiltersOf(filters: BoardFilters): BoardServerFilters {
  return {
    priority: filters.priority,
    states: [...filters.states],
    includeArchived: filters.includeArchived,
  };
}

/** True when the selection covers every canonical state (no filtering). */
export function isFullStateSelection(states: readonly BoardState[]): boolean {
  return states.length === BOARD_STATES.length;
}

/**
 * Normalize a state selection to canonical order so equal selections
 * produce equal query keys regardless of the order checkboxes were used.
 */
export function normalizeStates(states: readonly BoardState[]): BoardState[] {
  return BOARD_STATES.filter((state) => states.includes(state));
}

/**
 * The generated client's query object for `GET /projects/{pid}/tasks`.
 * Absent filters are omitted (never sent as empty/defaults) — the server's
 * documented defaults then apply.
 */
export function listTasksQuery(filters: BoardServerFilters): {
  page_size: number;
  priority?: PriorityEnum;
  state?: BoardState[];
  include_archived?: boolean;
} {
  return {
    page_size: 100, // contract clamp (pagination.md)
    ...(filters.priority !== null ? { priority: filters.priority } : {}),
    ...(isFullStateSelection(filters.states) ? {} : { state: normalizeStates(filters.states) }),
    ...(filters.includeArchived ? { include_archived: true } : {}),
  };
}

/**
 * Server-filter match — also the live-patching predicate (MT-4.3-05): a
 * streamed task must satisfy exactly what the server was asked for, or it
 * does not belong in the cached list.
 */
export function matchesServerFilters(task: Task, filters: BoardServerFilters): boolean {
  if (!filters.includeArchived && task.archived_at !== null) {
    return false;
  }
  if (filters.priority !== null && task.priority !== filters.priority) {
    return false;
  }
  if (!isFullStateSelection(filters.states) && !filters.states.includes(task.state)) {
    return false;
  }
  return true;
}

/** Client-side search: case-insensitive substring over id and title. */
export function matchesSearch(task: Task, search: string): boolean {
  const needle = search.trim().toLowerCase();
  if (needle === '') {
    return true;
  }
  return task.id.toLowerCase().includes(needle) || task.title.toLowerCase().includes(needle);
}

/** Full predicate: server filters (cached set) plus client-side search. */
export function matchesFilters(task: Task, filters: BoardFilters): boolean {
  return (
    matchesServerFilters(task, serverFiltersOf(filters)) && matchesSearch(task, filters.search)
  );
}

export function isDefaultBoardFilters(filters: BoardFilters): boolean {
  return (
    filters.priority === null &&
    isFullStateSelection(filters.states) &&
    !filters.includeArchived &&
    filters.search.trim() === ''
  );
}
