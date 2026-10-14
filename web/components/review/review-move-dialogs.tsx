'use client';

/**
 * Review-move dialog controller (MT-4.4-03; Section 13.2 — the `dialog`
 * verdicts from the MT-4.4-01 map; MT-4.4-02's `onDialog` seam).
 *
 * Mounted by the board while a `dialog` verdict is pending. Hosts the
 * one shared review-decision mutation (optimistic patch → POST
 * `/tasks/{id}/review` → settle / rollback) so both dialog flavors
 * announce through the same board `role="status"` region and close only
 * on success — endpoint failures keep the dialog open for retry
 * (Section 13.3).
 */
import { ApproveMergeDialog } from '@/components/review/approve-merge-dialog';
import { RequestChangesDialog } from '@/components/review/request-changes-dialog';
import type { Task } from '@/lib/api/generated/types.gen';
import type { BoardFilters } from '@/lib/board/filters';
import type { MoveDialog } from '@/lib/board/move-map';
import { useReviewDecision, type ReviewNotice } from '@/lib/queries/review-decision';

type ReviewMoveDialogsProps = {
  task: Task;
  dialog: MoveDialog;
  pid: string;
  filters: BoardFilters;
  onNotice: (notice: ReviewNotice) => void;
  /** Clears the board's active dialog state (success or dismissal). */
  onClose: () => void;
};

export function ReviewMoveDialogs({
  task,
  dialog,
  pid,
  filters,
  onNotice,
  onClose,
}: ReviewMoveDialogsProps) {
  const mutation = useReviewDecision({
    pid,
    filters,
    onNotice,
    onSuccess: onClose,
  });

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      mutation.reset();
      onClose();
    }
  };

  return dialog === 'approve_merge' ? (
    <ApproveMergeDialog task={task} open onOpenChange={handleOpenChange} mutation={mutation} />
  ) : (
    <RequestChangesDialog task={task} open onOpenChange={handleOpenChange} mutation={mutation} />
  );
}
