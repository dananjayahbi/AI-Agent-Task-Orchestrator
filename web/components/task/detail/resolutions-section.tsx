'use client';

/**
 * Resolutions section (MT-4.6-03, available part; Section 9.2
 * `GET /tasks/{id}/resolutions` + `GET /tasks/{id}/audit-reports`;
 * Section 7.2 Task Resolution / Audit Report fields).
 *
 * One entry per submission attempt (`attempt_number` ordered, newest
 * first), showing branch, commit sha, execution summary, the backend's
 * authoritative diff stats (Section 9.7 — never recomputed in the
 * client), `requires_human_attention` and `risk_justification`, plus the
 * resolution's audit report summary when one exists (verdict,
 * confidence, auditor notes, policy decision — auditor-less flows render
 * without one, Section 8.5). Fetch-on-expand keeps the first load light
 * (Section 13.3/13.4).
 *
 * Deferred (see WP changelog): the transitions-history rows — Section
 * 9.2 exposes no `GET /tasks/{id}/transitions`, so the region renders
 * an explicit notice instead of inventing an endpoint; and
 * `latest_feedback` propagation from WP-3.6 (Wave 8) — the block renders
 * the Task field as-is today and gains review-context copy when the
 * backend starts populating it.
 */
import { useState } from 'react';

import { DiffPanel } from '@/components/diff/diff-panel';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/errors/error-state';
import { EmptyState } from '@/components/states/empty-state';
import { LoadingState } from '@/components/states/loading-state';
import type { AuditReport, Resolution } from '@/lib/api/generated/types.gen';
import { resolveError } from '@/lib/errors';
import { useTaskAuditReportsQuery, useTaskResolutionsQuery } from '@/lib/queries/resolutions';
import { cn } from 'cn';

/**
 * Section 9.7 stats as stored by the backend — an object with numeric
 * `files` / `insertions` / `deletions`, or nothing renderable (the
 * column is free JSON; unknown shapes degrade to a raw collapsed view
 * rather than an invented schema — MT-4.6-03 risk note).
 */
function DiffStats({ summary }: { summary: unknown }) {
  if (typeof summary !== 'object' || summary === null) return null;
  const stats = summary as Record<string, unknown>;
  const read = (key: string): number | null =>
    typeof stats[key] === 'number' && Number.isFinite(stats[key]) ? (stats[key] as number) : null;
  const files = read('files');
  const insertions = read('insertions');
  const deletions = read('deletions');
  if (files === null && insertions === null && deletions === null) return null;
  return (
    <span
      data-testid="resolution-diff-stats"
      data-files={files ?? ''}
      className="font-mono text-[11px] text-muted-foreground"
    >
      {[
        files !== null ? `${files} file${files === 1 ? '' : 's'}` : null,
        insertions !== null ? `+${insertions}` : null,
        deletions !== null ? `−${deletions}` : null,
      ]
        .filter((part) => part !== null)
        .join(' · ')}
    </span>
  );
}

const VERDICT_LABELS: Record<string, string> = {
  pass: 'Pass',
  flag_risk: 'Flagged risk',
  fail: 'Fail',
};

const POLICY_LABELS: Record<string, string> = {
  approve: 'Approved by policy',
  escalate: 'Escalated to review',
};

/** The audit summary paired to one resolution (Section 7.2). */
export function AuditReportSummary({ report }: { report: AuditReport }) {
  return (
    <div
      data-testid="resolution-audit-report"
      className="grid gap-1 rounded-md border border-border bg-muted/30 p-2.5"
    >
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span
          data-testid="audit-verdict"
          className={cn(
            'rounded-full px-2 py-0.5 font-semibold',
            report.proposed_verdict === 'pass'
              ? 'bg-primary text-primary-foreground'
              : report.proposed_verdict === 'fail'
                ? 'bg-destructive text-destructive-foreground'
                : 'bg-secondary text-secondary-foreground',
          )}
        >
          {VERDICT_LABELS[report.proposed_verdict] ?? report.proposed_verdict}
        </span>
        <span data-testid="audit-confidence" className="text-muted-foreground">
          Confidence {report.confidence}/5
        </span>
        {report.policy_decision !== null && (
          <span data-testid="audit-policy-decision" className="text-muted-foreground">
            {POLICY_LABELS[report.policy_decision] ?? report.policy_decision}
          </span>
        )}
      </div>
      {report.auditor_notes !== '' && (
        <p data-testid="audit-notes" className="text-sm break-words text-foreground">
          {report.auditor_notes}
        </p>
      )}
    </div>
  );
}

function ResolutionEntry({
  resolution,
  report,
}: {
  resolution: Resolution;
  report: AuditReport | undefined;
}) {
  // Diff viewer (WP-4.7): mount-on-open, same fetch-on-expand
  // discipline as the section itself (Section 13.3/13.4, RISK-13).
  const [diffOpen, setDiffOpen] = useState(false);
  return (
    <li
      data-testid="resolution-entry"
      data-attempt={resolution.attempt_number}
      className="grid gap-2 rounded-md border border-border bg-card p-3 text-card-foreground"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold">Attempt {resolution.attempt_number}</span>
        <time dateTime={resolution.submitted_at} className="text-[11px] text-muted-foreground">
          {new Date(resolution.submitted_at).toLocaleString()}
        </time>
      </div>
      <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] text-muted-foreground">
        <span data-testid="resolution-branch">{resolution.branch_name}</span>
        <span data-testid="resolution-commit" title={resolution.commit_sha}>
          {resolution.commit_sha.slice(0, 12)}
        </span>
        <DiffStats summary={resolution.diff_summary} />
      </div>
      <p data-testid="resolution-summary" className="text-sm break-words">
        {resolution.execution_summary}
      </p>
      {resolution.requires_human_attention && (
        <div className="flex flex-col gap-1 rounded-md border border-destructive/40 bg-destructive/10 p-2">
          <span className="text-xs font-semibold text-destructive">
            Coder flagged for human attention
          </span>
          {resolution.risk_justification !== '' && (
            <p data-testid="resolution-risk" className="text-xs break-words">
              {resolution.risk_justification}
            </p>
          )}
        </div>
      )}
      {report !== undefined ? (
        <AuditReportSummary report={report} />
      ) : (
        <p className="text-xs text-muted-foreground">No audit report for this attempt.</p>
      )}
      <div>
        <Button
          size="sm"
          variant="ghost"
          data-testid={`resolution-diff-toggle-${resolution.id}`}
          aria-expanded={diffOpen}
          onClick={() => setDiffOpen((open) => !open)}
        >
          {diffOpen ? 'Hide diff' : 'View diff'}
        </Button>
      </div>
      {diffOpen && (
        <DiffPanel
          resolution={resolution}
          report={report}
          testId={`resolution-diff-${resolution.id}`}
        />
      )}
    </li>
  );
}

type ResolutionsSectionProps = {
  pid: string;
  taskId: string;
};

export function ResolutionsSection({ pid, taskId }: ResolutionsSectionProps) {
  const [expanded, setExpanded] = useState(false);
  const resolutionsQuery = useTaskResolutionsQuery(pid, taskId, expanded);
  const reportsQuery = useTaskAuditReportsQuery(pid, taskId, expanded);

  return (
    <section
      data-testid="task-detail-section-resolutions"
      aria-label="Resolutions"
      className="grid gap-2"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">Resolutions</h2>
        <Button
          size="sm"
          variant="outline"
          data-testid="resolutions-toggle"
          aria-expanded={expanded}
          onClick={() => setExpanded((open) => !open)}
        >
          {expanded ? 'Hide' : 'Show'}
        </Button>
      </div>

      {!expanded ? (
        <p className="text-xs text-muted-foreground">
          Collapsed — open to load submission attempts and audit reports.
        </p>
      ) : resolutionsQuery.isPending ? (
        <LoadingState label="Loading resolutions…" />
      ) : resolutionsQuery.isError ? (
        <ErrorState
          title={resolveError(resolutionsQuery.error).title}
          message={resolveError(resolutionsQuery.error).message}
          requestId={resolveError(resolutionsQuery.error).requestId}
          onRetry={() => void resolutionsQuery.refetch()}
        />
      ) : resolutionsQuery.data.length === 0 ? (
        <EmptyState
          title="No submissions yet"
          description="Resolution attempts appear here after an agent submits work."
        />
      ) : (
        <ul className="grid gap-3">
          {resolutionsQuery.data.map((resolution) => (
            <ResolutionEntry
              key={resolution.id}
              resolution={resolution}
              report={reportsQuery.data?.[resolution.id]}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

/**
 * Transition history region (deferred — MT-4.6-03; see WP changelog).
 * Section 9.2 lists no transitions endpoint, so the block renders an
 * explicit notice instead of inventing one (WP-4.4 precedent: never a
 * silent no-op, never a fabricated contract).
 */
export function TransitionsHistorySection() {
  return (
    <section
      data-testid="task-detail-section-transitions"
      aria-label="Transition history"
      className="grid gap-2"
    >
      <h2 className="text-sm font-semibold text-foreground">Transition history</h2>
      <p className="rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground">
        Transition history needs a task-transitions endpoint that is not part of the published API
        yet. It will appear here once the backend exposes it.
      </p>
    </section>
  );
}
