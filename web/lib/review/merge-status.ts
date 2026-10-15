/**
 * Merge-status presentation (MT-4.8-04; Section 8.1 sub-status cycle,
 * Section 7.2 canonical values, ADR-010 value/label separation).
 *
 * The canonical `merge_status` values (none | pending | merging | merged
 * | conflict | failed) are the contract; these labels are presentation
 * only. The only plan-specified wording is Section 8.1's "approved,
 * merging" — kept verbatim for the `merging` phase. The other labels
 * track the canonical names (MT-4.8-04 risk note: avoid display drift);
 * `pending` reads "approved, waiting" per the MT's scope wording — the
 * Section 8.1 badge note covers the whole pending→merging wait, so the
 * two are reconciled here and recorded in the WP changelog. Unknown or
 * future values degrade to the raw code (Section 20.5 — never invented).
 */

/** Canonical Section 7.2 merge_status values the UI knows. */
export const MERGE_STATUSES = [
  'none',
  'pending',
  'merging',
  'merged',
  'conflict',
  'failed',
] as const;

const MERGE_STATUS_LABELS: Record<string, string> = {
  pending: 'approved, waiting',
  merging: 'approved, merging',
  merged: 'merged',
  conflict: 'merge conflict',
  failed: 'merge failed',
};

/** Badge label for a merge_status; null when nothing should render. */
export function mergeStatusLabel(status: string): string | null {
  if (status === 'none' || status === '') {
    return null; // the default — no badge
  }
  return MERGE_STATUS_LABELS[status] ?? status;
}
