/**
 * Manifest query (MT-4.2-03; FR-PRJ-03; Section 10.3). The endpoint serves
 * `orchestrator.json` as JSON — the client requests `parseAs: 'text'` so the
 * exact response bytes reach the UI: download and clipboard both use the
 * server's text verbatim (no client-side field assembly, no re-serialization
 * — the server owns the manifest shape).
 */
import { useQuery } from '@tanstack/react-query';

import { callApi } from '@/lib/api';
import { retrieveProjectManifest } from '@/lib/api/generated/sdk.gen';
import type { OrchestratorManifest } from '@/lib/api/generated/types.gen';
import { queryKeys } from '@/lib/queries/keys';

export async function fetchManifestText(pid: string): Promise<string> {
  // Typed as OrchestratorManifest by the contract, but deliberately consumed
  // as the raw response text (parseAs above) — cast documents that intent.
  const raw = await callApi<OrchestratorManifest>(
    retrieveProjectManifest({ path: { pid }, parseAs: 'text' }),
  );
  return raw as unknown as string;
}

export function useManifestQuery(pid: string) {
  return useQuery({
    queryKey: queryKeys.projectManifest(pid),
    queryFn: () => fetchManifestText(pid),
    // Freshness matters: project fields change the rendered manifest, so it
    // is refetched whenever the settings section mounts.
    staleTime: 0,
  });
}
