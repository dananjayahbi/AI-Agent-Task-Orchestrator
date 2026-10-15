'use client';

/**
 * Review panel (MT-4.8-02; Section 13.2 review-panel composition,
 * Section 11.5 human-review workflow, Sections 8.4/9.4/10.5).
 *
 * The in-page surface the task detail mounts while the task sits in
 * `in_human_review`. Composition, in Section 13.2 order:
 *
 *  - escalation reason (Section 8.4 — friendly label **and** verbatim
 *    code, Section 20.5) driven by the task row;
 *  - execution summary of the latest submission attempt (Section 9.2
 *    resolution row — authoritative diff stats, nothing recomputed);
 *  - audit report: auditor notes + confidence + verdict, the Section 9.4
 *    rule table (persisted `policy_rule_results` verbatim) and the
 *    Section 10.5 evidence commands with exit codes;
 *  - the WP-4.7 diff and WP-4.6 attachments embedded as hosted
 *    components — never re-implemented here;
 *  - a docked actions region (MT-4.8-03) wiring the three Section 11.5
 *    actions onto the **existing** approve-merge and request-changes /
 *    reassign dialogs plus the shared `useReviewDecision` mutation —
 *    the panel hosts, it never rebuilds them. Approve binds the
 *    resolution the panel displayed (T15 guard: disabled without one),
 *    request changes keeps the dialog's mandatory-note guard, both
 *    conflicts (VERSION_CONFLICT / TASK_STATE_CONFLICT) announce
 *    catalog copy and refresh the row to server truth, and success
 *    shows the recorded decision with its `decided_via` channel
 *    (Section 7.2) — never a "completed" claim for approve
 *    (Section 8.1 / ADR-008).
 *
 * Distinct states (Section 20.3/20.4): loading, catalog-only error,
 * no-submission and no-audit-report (Section 8.5 path) are all explicit —
 * a pre-audit escalation degrades to reason + summary and **never**
 * renders an empty "all pass" rule table (MT risk note). The panel's
 * data comes only from existing endpoints (Section 9.2 resolutions /
 * audit reports); no rule or evidence value is computed client-side.
 */
import { useState } from 'react';

import { StreamStatusIndicator } from '@/components/board/stream-status';
import { Button } from '@/components/ui/button';
import { ApproveMergeDialog } from '@/components/review/approve-merge-dialog';
import { MergeStatusBadge } from '@/components/review/merge-status-badge';
import { RequestChangesDialog } from '@/components/review/request-changes-dialog';
import { EvidenceBlock } from '@/components/review/evidence-block';
import { RuleTable } from '@/components/review/rule-table';
import { ErrorState } from '@/components/errors/error-state';
import { LoadingState } from '@/components/states/loading-state';
import { AttachmentViewer } from '@/components/task/detail/attachment-viewer';
import { DiffPanel } from '@/components/diff/diff-panel';
import { DEFAULT_BOARD_FILTERS } from '@/lib/board/filters';
import type { Task } from '@/lib/api/generated/types.gen';
import { resolveError } from '@/lib/errors';
import { useReviewDecision, type ReviewNotice } from '@/lib/queries/review-decision';
import { useTaskAuditReportsQuery, useTaskResolutionsQuery } from '@/lib/queries/resolutions';
import { reviewReasonLabel } from '@/lib/review/review-reasons';
import { parseRuleResults } from '@/lib/review/rule-results';
import type { StreamStatus } from '@/lib/stream/use-event-stream';

type ReviewPanelProps = {
  pid: string;
  taskId: string;
  /** The task row as the detail page holds it (reason, version, state). */
  task: Task;
  /** The detail page's single SSE sink status (Section 13.3). */
  streamStatus: StreamStatus;
};

/** Section 9.7 diff stats from the resolution row — null when unrecorded. */
function diffStats(diffSummary: unknown): string | null {
  if (typeof diffSummary !== 'object' || diffSummary === null) {
    return null;
  }
  const stats = diffSummary as Record<string, unknown>;
  const files = typeof stats['files'] === 'number' ? stats['files'] : null;
  const insertions = typeof stats['insertions'] === 'number' ? stats['insertions'] : null;
  const deletions = typeof stats['deletions'] === 'number' ? stats['deletions'] : null;
  if (files === null && insertions === null && deletions === null) {
    return null;
  }
  const parts: string[] = [];
  if (files !== null) parts.push(`${files} file${files === 1 ? '' : 's'} changed`);
  if (insertions !== null) parts.push(`+${insertions}`);
  if (deletions !== null) parts.push(`−${deletions}`);
  return parts.join(' · ');
}

export function ReviewPanel({ pid, taskId, task, streamStatus }: ReviewPanelProps) {
  const resolutionsQuery = useTaskResolutionsQuery(pid, taskId, true);
  const reportsQuery = useTaskAuditReportsQuery(pid, taskId, true);
  const [diffOpen, setDiffOpen] = useState(false);
  const [dialog, setDialog] = useState<'approve_merge' | 'request_changes' | null>(null);
  const [notice, setNotice] = useState<ReviewNotice | null>(null);

  const mutation = useReviewDecision({
    pid,
    // Board-cache patches are best-effort from here (the panel may be
    // opened without a board entry); the detail row moves via the same
    // mutation, and SSE refetches confirm either way.
    filters: DEFAULT_BOARD_FILTERS,
    onNotice: setNotice,
    onSuccess: () => setDialog(null),
  });

  const handleDialogChange = (open: boolean) => {
    if (!open) {
      mutation.reset();
      setDialog(null);
    }
  };

  const openDialog = (next: 'approve_merge' | 'request_changes') => {
    setNotice(null);
    setDialog(next);
  };

  const resolutions = resolutionsQuery.data ?? [];
  const latest = resolutions[0];
  // T15's guard surfaced on the panel control itself: approve needs a
  // resolution to exist (the dialog re-checks and binds the exact row).
  const canApprove = latest !== undefined;
  const report = latest !== undefined ? reportsQuery.data?.[latest.id] : undefined;
  const ruleRows = parseRuleResults(report?.policy_rule_results ?? null);
  const stats = latest === undefined ? null : diffStats(latest.diff_summary);

  let body: React.ReactNode;
  if (resolutionsQuery.isPending || reportsQuery.isPending) {
    body = <LoadingState label="Loading the submission under review…" />;
  } else if (resolutionsQuery.isError) {
    const friendly = resolveError(resolutionsQuery.error);
    body = (
      <ErrorState
        title={friendly.title}
        message={friendly.message}
        requestId={friendly.requestId}
        onRetry={() => void resolutionsQuery.refetch()}
      />
    );
  } else if (latest === undefined) {
    // Pre-audit escalation with nothing submitted (T9-style) or an
    // auditor-less flow — reason + summary degrade, never an empty table.
    body = (
      <div data-testid="review-no-submission" className="rounded-md border border-border p-3">
        <p className="text-sm font-semibold text-foreground">No submission yet</p>
        <p className="mt-1 text-xs text-muted-foreground">
          This task was escalated before a submission landed. The escalation reason above is what a
          reviewer can act on right now.
        </p>
      </div>
    );
  } else {
    body = (
      <>
        <section
          aria-label="Submission summary"
          className="grid gap-2"
          data-testid="review-summary"
        >
          <h3 className="text-sm font-semibold text-foreground">Submission summary</h3>
          <div className="rounded-md border border-border bg-muted/30 p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span className="font-semibold text-foreground">Attempt {latest.attempt_number}</span>
              <span className="font-mono">
                {latest.branch_name} @ {latest.commit_sha.slice(0, 12)}
              </span>
              <span>{latest.submitted_at}</span>
            </div>
            <p className="mt-1.5 text-sm break-words text-muted-foreground">
              {latest.execution_summary}
            </p>
            {stats !== null && (
              <p data-testid="review-summary-diff" className="mt-1.5 font-mono text-[11px]">
                {stats}
              </p>
            )}
            <p
              data-testid="review-summary-files"
              className="mt-1.5 font-mono text-[11px] text-muted-foreground"
            >
              {latest.changed_files.length} changed file
              {latest.changed_files.length === 1 ? '' : 's'}
            </p>
          </div>
        </section>

        <section aria-label="Audit report" className="grid gap-3" data-testid="review-audit">
          <h3 className="text-sm font-semibold text-foreground">Audit report</h3>
          {reportsQuery.isError ? (
            <ErrorState
              title={resolveError(reportsQuery.error).title}
              message={resolveError(reportsQuery.error).message}
              requestId={resolveError(reportsQuery.error).requestId}
              onRetry={() => void reportsQuery.refetch()}
            />
          ) : report === undefined ? (
            // Section 8.5 path: a valid submission without an auditor
            // report — summary + reason are all there is to show.
            <p
              data-testid="review-no-report"
              className="rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground"
            >
              No audit report recorded for this submission. Review the execution summary, diff and
              attachments below — there is no rule outcome to read yet.
            </p>
          ) : (
            <>
              <div
                data-testid="review-audit-meta"
                className="flex flex-wrap gap-x-4 gap-y-1 text-xs"
              >
                <span>
                  <span className="text-muted-foreground">Verdict:</span>{' '}
                  <span className="font-semibold" data-testid="review-audit-verdict">
                    {report.proposed_verdict}
                  </span>
                </span>
                <span>
                  <span className="text-muted-foreground">Confidence:</span>{' '}
                  <span className="font-semibold" data-testid="review-audit-confidence">
                    {report.confidence}/5
                  </span>
                </span>
                <span>
                  <span className="text-muted-foreground">Policy decision:</span>{' '}
                  <span className="font-semibold" data-testid="review-audit-policy">
                    {report.policy_decision ?? 'pending'}
                  </span>
                </span>
              </div>
              <p
                data-testid="review-audit-notes"
                className="rounded-md border border-border bg-muted/30 p-3 text-sm break-words text-foreground"
              >
                {report.auditor_notes}
              </p>
              <RuleTable rows={ruleRows} />
              {ruleRows.length === 0 && (
                <p data-testid="review-no-rule-results" className="text-xs text-muted-foreground">
                  No rule outcomes persisted for this report — the engine records each rule result
                  when it runs; there is nothing to read here yet.
                </p>
              )}
              <EvidenceBlock evidence={report.evidence} />
            </>
          )}
        </section>
      </>
    );
  }

  return (
    <section
      id="review-panel"
      data-testid="review-panel"
      aria-label="Review panel"
      className="grid gap-4 rounded-lg border border-border bg-card p-4 text-card-foreground"
    >
      <header
        className="flex flex-wrap items-center justify-between gap-2"
        data-testid="review-panel-header"
      >
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-base font-semibold text-foreground">Human review</h2>
          <StreamStatusIndicator status={streamStatus} />
          <MergeStatusBadge status={task.merge_status} testId="review-merge-badge" />
        </div>
        <span className="font-mono text-[11px] text-muted-foreground">{task.id}</span>
      </header>

      <section aria-label="Escalation reason" className="grid gap-1.5" data-testid="review-reasons">
        <h3 className="text-sm font-semibold text-foreground">Escalation reason</h3>
        <ul data-testid="review-reason-list" className="grid gap-1 text-sm">
          <li data-testid="review-reason-item">
            <span className="text-foreground">{reviewReasonLabel(task.review_reason)}</span>
            {task.review_reason !== null && (
              <span className="font-mono text-xs text-muted-foreground">
                {' '}
                ({task.review_reason})
              </span>
            )}
          </li>
        </ul>
      </section>

      {body}

      {latest !== undefined && (
        <section aria-label="Diff" className="grid gap-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-foreground">Diff</h3>
            <Button
              type="button"
              size="sm"
              variant="outline"
              data-testid="review-diff-toggle"
              aria-expanded={diffOpen}
              onClick={() => setDiffOpen((open) => !open)}
            >
              {diffOpen ? 'Hide diff' : 'View diff'}
            </Button>
          </div>
          {diffOpen && <DiffPanel resolution={latest} report={report} testId="review-diff" />}
        </section>
      )}

      <section
        aria-label="Attachments as evidence"
        className="grid gap-2"
        data-testid="review-attachments"
      >
        <h3 className="text-sm font-semibold text-foreground">Attachments</h3>
        <AttachmentViewer pid={pid} taskId={taskId} />
      </section>

      <section
        aria-label="Review actions"
        className="grid gap-2"
        data-testid="review-panel-actions"
      >
        <h3 className="text-sm font-semibold text-foreground">Review actions</h3>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            data-testid="review-approve-open"
            disabled={!canApprove || mutation.isPending}
            onClick={() => openDialog('approve_merge')}
          >
            Approve &amp; merge
          </Button>
          <Button
            type="button"
            data-testid="review-request-changes-open"
            variant="secondary"
            disabled={mutation.isPending}
            onClick={() => openDialog('request_changes')}
          >
            Request changes
          </Button>
          <Button
            type="button"
            data-testid="review-reassign-open"
            variant="outline"
            disabled={mutation.isPending}
            onClick={() => openDialog('request_changes')}
          >
            Reassign
          </Button>
        </div>
        {!canApprove && !resolutionsQuery.isPending && (
          <p data-testid="review-approve-blocked" className="text-xs text-muted-foreground">
            Approve needs a submitted resolution (T15) — there is nothing to approve yet.
          </p>
        )}

        {mutation.data !== undefined && (
          <p
            data-testid="review-decision-record"
            className="rounded-md border border-border bg-muted/30 p-2 text-xs text-muted-foreground"
          >
            Decision recorded:{' '}
            <span className="font-semibold text-foreground">{mutation.data.decision.decision}</span>{' '}
            via <span className="font-mono">{mutation.data.decision.decided_via}</span> at{' '}
            <span className="font-mono">{mutation.data.decision.decided_at}</span>
          </p>
        )}

        {notice !== null && (
          <p
            role="status"
            data-testid="review-notice"
            className={`text-xs ${notice.rejected ? 'text-destructive' : 'text-muted-foreground'}`}
          >
            {notice.message}
          </p>
        )}
      </section>

      <ApproveMergeDialog
        task={task}
        open={dialog === 'approve_merge'}
        onOpenChange={handleDialogChange}
        mutation={mutation}
      />
      <RequestChangesDialog
        task={task}
        open={dialog === 'request_changes'}
        onOpenChange={handleDialogChange}
        mutation={mutation}
      />
    </section>
  );
}
