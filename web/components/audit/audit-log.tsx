/**
 * Audit-log container (MT-4.10-02; Section 13.1 "Filterable event
 * history" — filters, URL state, and the viewer composition).
 *
 * **URL is the filter state** (the web convention the MT records): the
 * container derives the filter set from `location.search` through
 * `useSyncExternalStore` (server snapshot empty → no hydration
 * mismatch), and writes changes back with `history.replaceState` plus a
 * local notify (replaceState fires no `popstate`). Share/refresh always
 * reproduces the view; a filter change is a new query key, so the
 * cursor walk restarts from page one (pagination reset — AC). Only the
 * contract's parameters are written: `project` and `task`.
 */
'use client';

import { useCallback, useSyncExternalStore } from 'react';

import { AuditLogFiltersBar } from '@/components/audit/audit-log-filters';
import { AuditLogView } from '@/components/audit/audit-log-view';
import { NO_AUDIT_FILTERS, type AuditLogFilters } from '@/lib/queries/audit-events';

const searchListeners = new Set<() => void>();

function notifySearchChange(): void {
  for (const listener of searchListeners) {
    listener();
  }
}

function subscribeSearch(onChange: () => void): () => void {
  searchListeners.add(onChange);
  window.addEventListener('popstate', onChange);
  return () => {
    searchListeners.delete(onChange);
    window.removeEventListener('popstate', onChange);
  };
}

function readSearch(): string {
  return typeof window === 'undefined' ? '' : window.location.search;
}

/** Only the documented `GET /events` filter parameters (Section 9.2). */
export function filtersFromSearch(search: string): AuditLogFilters {
  const params = new URLSearchParams(search);
  const project = params.get('project');
  const task = params.get('task');
  return {
    project: project !== null && project !== '' ? project : null,
    task: task !== null && task !== '' ? task : null,
  };
}

function writeFiltersToUrl(filters: AuditLogFilters): void {
  const params = new URLSearchParams(window.location.search);
  if (filters.project === null) {
    params.delete('project');
  } else {
    params.set('project', filters.project);
  }
  if (filters.task === null) {
    params.delete('task');
  } else {
    params.set('task', filters.task);
  }
  const query = params.toString();
  const next = `${window.location.pathname}${query !== '' ? `?${query}` : ''}${window.location.hash}`;
  window.history.replaceState(window.history.state, '', next);
  notifySearchChange();
}

export function AuditLog() {
  const search = useSyncExternalStore(subscribeSearch, readSearch, () => '');
  const filters = filtersFromSearch(search);

  const update = useCallback((next: AuditLogFilters) => {
    writeFiltersToUrl(next);
  }, []);
  const clearAll = useCallback(() => {
    writeFiltersToUrl(NO_AUDIT_FILTERS);
  }, []);

  return (
    <div data-testid="audit-log" className="flex flex-col gap-4">
      <AuditLogFiltersBar filters={filters} onChange={update} onClearAll={clearAll} />
      <AuditLogView filters={filters} onClearFilters={clearAll} />
    </div>
  );
}
