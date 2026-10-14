'use client';

/**
 * Resolution patch query (MT-4.7-02/04; Section 9.2
 * `GET /resolutions/{id}/patch`; Section 9.7 both paths).
 *
 * Fetch-on-open like the rest of the task detail (Section 13.3/13.4):
 * the entry is created only when the viewer opens for a resolution,
 * so a first load never pulls patch bodies it may never show
 * (RISK-13). Both Section 9.7 paths share one response shape —
 * `diff_too_large: true` with a null body is a degraded success, not
 * an error (the viewer renders the marker through
 * `interpretPatchPayload`).
 */
import { useQuery } from '@tanstack/react-query';

import { callApi, getResolutionPatch } from '@/lib/api';
import { queryKeys } from '@/lib/queries/keys';

export function useResolutionPatchQuery(resolutionId: string, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.resolutionPatch(resolutionId),
    queryFn: () => callApi(getResolutionPatch({ path: { id: resolutionId } })),
    enabled: enabled && resolutionId.trim() !== '',
    staleTime: 60_000, // stored artifacts are immutable (Section 7.2 sha256)
  });
}
