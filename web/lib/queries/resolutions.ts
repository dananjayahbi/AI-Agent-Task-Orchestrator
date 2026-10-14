/**
 * Resolutions and audit-report queries (MT-4.6-03 partial; Section 9.2
 * `GET /tasks/{id}/resolutions` + `GET /tasks/{id}/audit-reports`;
 * Section 7.2 Task Resolution / Audit Report fields).
 *
 * Fetch-on-expand (Section 13.3/13.4): both queries stay disabled until
 * the section is opened, so the detail page's first load never pulls
 * attempt history it may never show (RISK-13). Audit reports pair to
 * resolutions by `resolution_id`; a resolution without a report is
 * valid (auditor-less flows, Section 8.5) and renders without one.
 *
 * The transition history has its own fetch-on-expand entry
 * (`lib/queries/transitions.ts`, MT-4.6-03) — the published
 * `GET /events` history is its source; no `GET /tasks/{id}/transitions`
 * endpoint exists in Section 9.2 or the schema.
 */
import { useQuery } from '@tanstack/react-query';

import { callApi, listAuditReports, listResolutions } from '@/lib/api';
import type { AuditReport, Resolution } from '@/lib/api/generated/types.gen';
import { queryKeys } from '@/lib/queries/keys';

const PAGE_SIZE = 25;

/** One submission attempt's resolution rows, newest attempt first. */
export function useTaskResolutionsQuery(pid: string, taskId: string, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.taskResolutions(pid, taskId),
    queryFn: async () => {
      const page = await callApi(
        listResolutions({ path: { id: taskId }, query: { page_size: PAGE_SIZE } }),
      );
      return [...page.results].sort((a, b) => b.attempt_number - a.attempt_number);
    },
    enabled: enabled && taskId.trim() !== '',
    staleTime: 30_000,
  });
}

/**
 * The task's audit reports paired to their resolution id — the review
 * panel (WP-4.8) consumes the same pairing from the backend; nothing is
 * recomputed client-side (Section 9.7 authoritative-stats rule applies
 * to the evidence it carries).
 */
export function useTaskAuditReportsQuery(pid: string, taskId: string, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.taskAuditReports(pid, taskId),
    queryFn: async () => {
      const page = await callApi(
        listAuditReports({ path: { id: taskId }, query: { page_size: PAGE_SIZE } }),
      );
      const paired: Record<string, AuditReport> = {};
      for (const report of page.results) {
        paired[report.resolution_id] = report;
      }
      return paired;
    },
    enabled: enabled && taskId.trim() !== '',
    staleTime: 30_000,
  });
}

export type { Resolution };
