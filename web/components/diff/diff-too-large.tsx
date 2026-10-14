'use client';

/**
 * Large-diff fallback (MT-4.7-04; Section 9.7: "oversize patches
 * store stats and file list only, with a 'diff too large' marker in
 * the viewers").
 *
 * The marker phrase is Section 9.7's verbatim text and is shared with
 * the mobile renderer (WP-5.8, Section 14.2) through
 * `DIFF_TOO_LARGE_MARKER` in `lib/diff/parse` — one constant, two
 * viewers, no wording drift. The panel never fabricates diff content
 * (Section 9.7 authority rule): it explains what happened, shows the
 * backend's authoritative stats, and points at the resolution's
 * summary and file list as the full context that *was* stored.
 *
 * This component renders the marker **and** the authoritative stats;
 * the file list is rendered by the caller through the same FileTree
 * in its non-jumping mode (MT-4.7-03 degradation contract), so the
 * reviewer keeps the whole stored picture in one place.
 */
import { DIFF_TOO_LARGE_MARKER } from '@/lib/diff/parse';
import { formatDiffSummary, readDiffSummary } from '@/lib/diff/summary';

type DiffTooLargeProps = {
  /** The server's marker phrase (Section 9.7: `marker` on the payload). */
  marker?: string | null;
  /** The resolution's authoritative `diff_summary` (Section 7.2). */
  diffSummary: unknown;
  testId?: string;
};

export function DiffTooLarge({ marker, diffSummary, testId }: DiffTooLargeProps) {
  const phrase =
    typeof marker === 'string' && marker.trim() !== '' ? marker : DIFF_TOO_LARGE_MARKER;
  const stats = readDiffSummary(diffSummary);
  return (
    <div
      data-testid={testId ?? 'diff-too-large'}
      role="status"
      className="grid gap-1 rounded-md border border-dashed border-border bg-muted/30 p-4 text-center"
    >
      <p data-testid="diff-too-large-marker" className="text-sm font-semibold text-foreground">
        {phrase}
      </p>
      <p className="text-xs text-muted-foreground">
        The patch body exceeded the storage size cap, so only the statistics and the changed-file
        list were kept (Section 9.7). The full context lives in the resolution summary and the file
        list below — no diff content can be shown here.
      </p>
      {stats !== null && (
        <p
          data-testid="diff-too-large-stats"
          className="font-mono text-[11px] text-muted-foreground"
        >
          {formatDiffSummary(stats)}
        </p>
      )}
    </div>
  );
}
