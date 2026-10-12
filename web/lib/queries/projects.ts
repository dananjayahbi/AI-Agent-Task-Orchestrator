/**
 * Project queries (MT-4.2-01; Section 13.3 — server state through a query
 * library; every request goes through the generated client, NFR-11).
 */
import { useQuery } from '@tanstack/react-query';

import { callApi } from '@/lib/api';
import { fetchAllPages } from '@/lib/api/pagination';
import { listProjects, retrieveProject } from '@/lib/api/generated/sdk.gen';
import type { Project, ProjectListEnvelope } from '@/lib/api/generated/types.gen';
import { queryKeys } from '@/lib/queries/keys';

/** One page of `GET /projects` through the generated client (Section 9.2). */
function fetchProjectsPage(cursor: string | undefined): Promise<ProjectListEnvelope> {
  return callApi(listProjects({ query: { cursor, page_size: 100 } }));
}

/** All projects, following the cursor to the last page (Section 9.2). */
export function fetchAllProjects(): Promise<Project[]> {
  return fetchAllPages(fetchProjectsPage);
}

/**
 * All projects with cached instant switching (MT-4.2-01 scope: "query
 * caching … switching back is instant and a refresh invalidates correctly").
 * Stale time keeps a route change from refetching; `invalidateQueries` after
 * creates/edits refetches the fresh list.
 */
export function useProjectsQuery() {
  return useQuery({
    queryKey: queryKeys.projects,
    queryFn: fetchAllProjects,
    staleTime: 30_000,
  });
}

/** One project (`GET /projects/{pid}`) — settings and detail surfaces. */
export function useProjectQuery(pid: string | undefined) {
  return useQuery({
    queryKey: queryKeys.project(pid ?? 'unknown'),
    queryFn: () => callApi(retrieveProject({ path: { pid: pid ?? '' } })),
    enabled: pid !== undefined && pid !== '',
    staleTime: 30_000,
  });
}
