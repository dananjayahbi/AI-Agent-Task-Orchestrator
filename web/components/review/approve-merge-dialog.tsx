'use client';

/**
 * Approve-and-merge confirmation (MT-4.4-03; Section 13.2 — the
 * `in_human_review` → `completed` drop "opens an approve-and-merge
 * confirmation (not a plain move)"; Section 8.2 T15; Section 11.5).
 *
 * What the operator sees before confirming:
 *  - the task id, title and escalation reason (Section 8.4 code verbatim
 *    plus a friendly label);
 *  - the resolution being approved — attempt number, branch and commit
 *    from `GET /tasks/{id}/resolutions`, newest attempt first. The
 *    submitted `resolution_id` binds to exactly that displayed row
 *    (Section 14.2 approve safety / MT-3.6-04: approving a stale binding
 *    answers VERSION_CONFLICT server-side);
 *  - honest outcome copy (Section 8.1 risk note): approval sends the
 *    task to **merge pending** — an "approved, merging" badge — never
 *    straight to a completed column.
 *
 * T15's guard ("resolution exists") is surfaced before the network: with
 * no resolution the confirm button is disabled with the reason. Failure
 * keeps the dialog open with catalog-mapped copy (Section 13.3). Radix
 * provides focus trap, Escape and focus return (Section 13.4).
 */
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ErrorState } from '@/components/errors/error-state';
import { LoadingState } from '@/components/states/loading-state';
import type { Task } from '@/lib/api/generated/types.gen';
import { resolveError } from '@/lib/errors';
import { reviewReasonLabel } from '@/lib/review/review-reasons';
import { useTaskResolutionsQuery } from '@/lib/queries/resolutions';
import type { ReviewDecisionMutation } from '@/lib/queries/review-decision';

type ApproveMergeDialogProps = {
  task: Task;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mutation: ReviewDecisionMutation;
};

export function ApproveMergeDialog({
  task,
  open,
  onOpenChange,
  mutation,
}: ApproveMergeDialogProps) {
  const resolutionsQuery = useTaskResolutionsQuery(task.project_id, task.id, open);
  const resolutions = resolutionsQuery.data ?? [];
  // Newest attempt first — bind and display the same row (MT risk note).
  const viewed = resolutions[0];
  const loading = resolutionsQuery.isPending;
  const blockedReason = loading
    ? 'Checking this task’s submissions…'
    : resolutionsQuery.isError
      ? 'The submission to approve could not be loaded — retry before approving.'
      : viewed === undefined
        ? 'This task has no resolution to approve yet (T15 requires one).'
        : null;
  const pending = mutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="approve-merge-dialog">
        <DialogHeader>
          <DialogTitle>Approve and merge {task.id}?</DialogTitle>
          <DialogDescription>
            Approval records your decision and sends the task to merge — it shows as &quot;approved,
            merging&quot; until the merge completes, and never jumps straight to Completed.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-foreground">{task.title}</span>
            <span className="font-mono text-[11px] text-muted-foreground">{task.id}</span>
          </div>
          <p className="text-xs text-muted-foreground">
            Escalation reason: {reviewReasonLabel(task.review_reason)}
            {task.review_reason !== null && (
              <span className="font-mono"> ({task.review_reason})</span>
            )}
          </p>

          {loading ? (
            <LoadingState label="Loading the submission to approve…" />
          ) : resolutionsQuery.isError ? (
            <ErrorState
              title={resolveError(resolutionsQuery.error).title}
              message={resolveError(resolutionsQuery.error).message}
              requestId={resolveError(resolutionsQuery.error).requestId}
              onRetry={() => void resolutionsQuery.refetch()}
            />
          ) : viewed !== undefined ? (
            <div
              data-testid="approve-resolution-context"
              className="grid gap-1 rounded-md border border-border bg-muted/30 p-2.5 text-xs"
            >
              <span className="font-semibold text-foreground">
                You are approving attempt {viewed.attempt_number}
              </span>
              <span className="font-mono text-muted-foreground">
                {viewed.branch_name} @ {viewed.commit_sha.slice(0, 12)}
              </span>
              <span className="text-muted-foreground">{viewed.execution_summary}</span>
            </div>
          ) : null}
        </div>

        {mutation.isError && (
          <div
            role="alert"
            data-testid="approve-error"
            className="rounded-md border border-destructive/40 bg-destructive/10 p-2.5 text-sm text-destructive"
          >
            <span className="font-semibold">{resolveError(mutation.error).title}</span>
            <p>{resolveError(mutation.error).message}</p>
          </div>
        )}

        <DialogFooter>
          <Button
            type="button"
            data-testid="approve-cancel"
            variant="outline"
            disabled={pending}
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            type="button"
            data-testid="approve-confirm"
            disabled={pending || blockedReason !== null}
            onClick={() => {
              if (viewed !== undefined) {
                mutation.mutate({
                  task,
                  decision: 'approve',
                  resolutionId: viewed.id,
                });
              }
            }}
          >
            {pending ? 'Approving…' : 'Approve & merge'}
          </Button>
        </DialogFooter>
        {blockedReason !== null && (
          <p data-testid="approve-blocked" className="text-xs text-muted-foreground">
            {blockedReason}
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}
