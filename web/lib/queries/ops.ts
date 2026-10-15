/**
 * Operations snapshot query (MT-6.4-03; Section 17 Dashboards row; NFR-10).
 *
 * One `GET /api/v1/ops/overview` cache entry: MT-6.4-01's metrics + MT-6.4-02's
 * alert states + the Health row, assembled server-side (the endpoint embeds
 * the same `collect()` the `/metrics` root route serves — the view never
 * computes its own numbers).
 *
 * Update mode: **polling** (the MT's "polling-vs-SSE choice", recorded here
 * and in the view). The snapshot is a pull-based scrape by design — the alert
 * evaluation and the DB gauges are computed at request time, so an SSE patch
 * would carry stale-until-recomputed data anyway; the events stream is also
 * project-scoped while this view is cross-project. Freshness is displayed:
 * the payload's `generated_at` is rendered as "as of …" so a frozen view is
 * recognizable (MT-6.4-03 risk note).
 */
import { useQuery } from '@tanstack/react-query';

import { callApi, retrieveOpsOverview } from '@/lib/api';
import type { OpsOverview } from '@/lib/api/generated/types.gen';
import { queryKeys } from '@/lib/queries/keys';

/** One snapshot fetch — the generated operation, through the transport seam. */
export function fetchOpsOverview(): Promise<OpsOverview> {
  return callApi(retrieveOpsOverview());
}

/** Poll cadence: 30 s — between the 60 s sweeper cadence's beats and the
 *  5-minute tunnel staleness bound; cheap (one cache + count scrape). */
export const OPS_OVERVIEW_POLL_MS = 30_000;

export function useOpsOverviewQuery() {
  return useQuery({
    queryKey: queryKeys.opsOverview,
    queryFn: fetchOpsOverview,
    refetchInterval: OPS_OVERVIEW_POLL_MS,
    staleTime: 10_000,
  });
}
