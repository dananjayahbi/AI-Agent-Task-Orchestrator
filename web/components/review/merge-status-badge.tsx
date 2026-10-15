'use client';

/**
 * Merge-status badge (MT-4.8-04; Section 8.1 "approved, merging" note,
 * Section 7.2 canonical values).
 *
 * One shared badge for every surface that shows a task's merge
 * sub-status — the review panel, the queue row and the board card.
 * `none` renders nothing; destructive styling marks the failure branch
 * (`conflict` / `failed`, T18's return to human review). The canonical
 * value rides on `data-merge-status` (tests and support read the value,
 * the visible text is the label — ADR-010 keeps them separate).
 */
import { mergeStatusLabel } from '@/lib/review/merge-status';

export function MergeStatusBadge({
  status,
  testId = 'merge-status-badge',
}: {
  status: string;
  testId?: string;
}) {
  const label = mergeStatusLabel(status);
  if (label === null) {
    return null;
  }
  const destructive = status === 'conflict' || status === 'failed';
  return (
    <span
      data-testid={testId}
      data-merge-status={status}
      title={`merge_status: ${status}`}
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
        destructive
          ? 'bg-destructive/15 text-destructive'
          : 'bg-secondary text-secondary-foreground'
      }`}
    >
      {label}
    </span>
  );
}
