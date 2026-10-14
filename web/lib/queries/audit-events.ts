/**
 * Audit-log history query (MT-4.10-01; Sections 13.1 "Filterable event
 * history", 9.2 `GET /events`, 12.5 read-only, Principle P8).
 *
 * Data source: the published `GET /events` history endpoint through the
 * generated client (NFR-11) — the viewer is a pure read of the
 * append-only log; it never writes, edits or enriches rows (P10: no
 * client-side decoration of actor refs or payloads).
 *
 * Cursor discipline (AC; RISK-13): pages are collected with the shared
 * bounded helper (100-page defensive cap, repeated-cursor guard) rather
 * than an unbounded walk. The endpoint pages oldest → newest, so rows
 * are presented reverse-chronologically (newest first) — the same
 * recorded reading the MT-4.6-03 transition history made for this
 * endpoint. One cache entry per filter set (`queryKeys.auditEvents`):
 * MT-4.10-02's filter changes are a new key, so pagination state can
 * never leak across filter sets.
 */
import { useQuery } from '@tanstack/react-query';

import { apiV1EventsRetrieve, callApi } from '@/lib/api';
import type { EventEnvelope } from '@/lib/api/generated/types.gen';
import { fetchAllPages } from '@/lib/api/pagination';
import { queryKeys } from '@/lib/queries/keys';

const PAGE_SIZE = 100; // contract clamp (pagination.md)

/** The contract's filter surface for `GET /events` (Section 9.2). */
export type AuditLogFilters = {
  project: string | null;
  task: string | null;
};

export const NO_AUDIT_FILTERS: AuditLogFilters = { project: null, task: null };

/** Every event matching the filters, newest first (Section 13.1). */
export async function fetchAuditEvents(filters: AuditLogFilters): Promise<EventEnvelope[]> {
  const events = await fetchAllPages((cursor) =>
    callApi(
      apiV1EventsRetrieve({
        query: {
          ...(filters.project !== null ? { project: filters.project } : {}),
          ...(filters.task !== null ? { task: filters.task } : {}),
          page_size: PAGE_SIZE,
          ...(cursor !== undefined ? { cursor } : {}),
        },
      }),
    ),
  );
  return [...events].sort((a, b) => b.id - a.id);
}

/** Section 13.3 server-state seam for one filter set. */
export function useAuditEventsQuery(filters: AuditLogFilters) {
  return useQuery({
    queryKey: queryKeys.auditEvents(filters),
    queryFn: () => fetchAuditEvents(filters),
    staleTime: 30_000,
  });
}
