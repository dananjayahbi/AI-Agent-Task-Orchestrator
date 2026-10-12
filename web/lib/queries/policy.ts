/**
 * Project policy queries (MT-4.2-02; FR-WEB-09 — policy editor data via
 * `GET /projects/{pid}/policy`).
 */
import { useQuery } from '@tanstack/react-query';

import { callApi } from '@/lib/api';
import { retrieveProjectPolicy } from '@/lib/api/generated/sdk.gen';
import { queryKeys } from '@/lib/queries/keys';

export function usePolicyQuery(pid: string) {
  return useQuery({
    queryKey: queryKeys.projectPolicy(pid),
    queryFn: () => callApi(retrieveProjectPolicy({ path: { pid } })),
    staleTime: 30_000,
  });
}
