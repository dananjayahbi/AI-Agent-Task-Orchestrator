/**
 * Agent-token queries (MT-4.2-04; Section 9.2 — `GET /tokens` filtered to
 * this project's agent tokens; metadata only, the response carries no secret
 * by contract (FR-SEC-04)).
 */
import { useQuery } from '@tanstack/react-query';

import { apiV1TokensRetrieve, callApi } from '@/lib/api';
import type { TokenListEnvelope, TokenSummary } from '@/lib/api/generated/types.gen';
import { fetchAllPages } from '@/lib/api/pagination';
import { queryKeys } from '@/lib/queries/keys';

function fetchTokensPage(pid: string, cursor: string | undefined): Promise<TokenListEnvelope> {
  return callApi(
    apiV1TokensRetrieve({ query: { cursor, kind: 'agent', project_id: pid, page_size: 100 } }),
  );
}

export function fetchAgentTokens(pid: string): Promise<TokenSummary[]> {
  return fetchAllPages((cursor) => fetchTokensPage(pid, cursor));
}

export function useAgentTokensQuery(pid: string) {
  return useQuery({
    queryKey: queryKeys.projectTokens(pid),
    queryFn: () => fetchAgentTokens(pid),
    staleTime: 30_000,
  });
}
