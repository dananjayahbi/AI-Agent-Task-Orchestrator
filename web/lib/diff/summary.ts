'use client';

/**
 * Backend-authoritative diff stats reader (MT-4.7-02; Section 9.7;
 * Section 20.5 — no re-derived contract).
 *
 * The only figures the viewer displays come from the Task Resolution's
 * `diff_summary` as the backend computed it from the stored patch
 * (Section 7.2). This module **reads** that JSON defensively — it
 * never computes, merges or infers numbers (the MT acceptance: "no
 * client-side recomputation"). Unknown shapes render nothing rather
 * than an invented schema (WP-4.6 precedent).
 */

export type DiffSummaryStats = {
  files: number | null;
  insertions: number | null;
  deletions: number | null;
};

/** Read `diff_summary` defensively; null when nothing renderable exists. */
export function readDiffSummary(summary: unknown): DiffSummaryStats | null {
  if (typeof summary !== 'object' || summary === null) return null;
  const record = summary as Record<string, unknown>;
  const read = (key: string): number | null => {
    const value = record[key];
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
  };
  const files = read('files');
  const insertions = read('insertions');
  const deletions = read('deletions');
  if (files === null && insertions === null && deletions === null) return null;
  return { files, insertions, deletions };
}

/** Compact human rendering of the authoritative stats ("3 files · +120 · −4"). */
export function formatDiffSummary(stats: DiffSummaryStats): string {
  const parts: string[] = [];
  if (stats.files !== null) parts.push(`${stats.files} file${stats.files === 1 ? '' : 's'}`);
  if (stats.insertions !== null) parts.push(`+${stats.insertions}`);
  if (stats.deletions !== null) parts.push(`−${stats.deletions}`);
  return parts.join(' · ');
}
