'use client';

/**
 * Row flattening for the virtualized diff view (MT-4.7-02; Section
 * 13.2 "collapse large files"; Section 13.4 / Wave 9: a 5,000-line
 * patch renders responsively).
 *
 * The parsed files → hunks → lines tree is flattened into a single
 * list of uniform rows so the board's windowing primitive
 * (`VirtualList`, MT-4.3-06) can render the diff with a bounded DOM
 * regardless of patch size — the same dependency-free fixed-row-height
 * approach the board columns use, reused rather than reinvented.
 *
 * Collapse model (MT-4.7-02 "collapse large files"): files whose
 * body exceeds `LARGE_FILE_LINES` start collapsed to just their file
 * header row plus an expand affordance; the user expands on demand.
 * The threshold is a rendering choice, not a contract — Section 9.7's
 * 5 MB cap bounds the worst case.
 *
 * Split mode pairs deletions/additions per hunk into side-by-side
 * rows. Pairing is greedy within a run of consecutive +/- lines
 * (the standard reading): the i-th deletion pairs with the i-th
 * addition; a shorter side pads with nulls. Context lines pair with
 * themselves.
 */
import type { PatchFile, PatchHunk, PatchLine } from '@/lib/diff/parse';

/** Files with more hunk-body lines than this start collapsed. */
export const LARGE_FILE_LINES = 200;

/** One uniform row the virtualized view renders. */
export type DiffRow =
  | { kind: 'file'; fileIndex: number; file: PatchFile; collapsed: boolean; hiddenLines: number }
  | { kind: 'hunk'; fileIndex: number; hunk: PatchHunk }
  | { kind: 'opaque'; fileIndex: number; text: string }
  | {
      kind: 'line';
      fileIndex: number;
      /** Unified: the line itself. Split: `left`/`right` pair (null = pad). */
      left: PatchLine | null;
      right: PatchLine | null;
    };

/** Stable identity key for window reconciliation (MT-4.3-06 convention). */
export function rowKey(row: DiffRow, file: Pick<PatchFile, 'path'>): string {
  switch (row.kind) {
    case 'file':
      return `file:${file.path}`;
    case 'hunk':
      return `hunk:${file.path}:${row.hunk.oldStart}:${row.hunk.newStart}`;
    case 'opaque':
      return `opaque:${file.path}:${row.text}`;
    case 'line': {
      const leftId = row.left === null ? 'x' : `${row.left.oldLine ?? 'n'}:${row.left.kind}`;
      const rightId = row.right === null ? 'x' : `${row.right.newLine ?? 'n'}:${row.right.kind}`;
      return `line:${file.path}:${leftId}:${rightId}`;
    }
  }
}

/** Greedy +/- pairing within one hunk (split mode). */
export function pairHunkLines(
  hunk: PatchHunk,
): Array<{ left: PatchLine | null; right: PatchLine | null }> {
  const pairs: Array<{ left: PatchLine | null; right: PatchLine | null }> = [];
  let run: PatchLine[] = [];
  const flushRun = () => {
    if (run.length === 0) return;
    const dels = run.filter((line) => line.kind === 'del');
    const adds = run.filter((line) => line.kind === 'add');
    const length = Math.max(dels.length, adds.length);
    for (let index = 0; index < length; index += 1) {
      pairs.push({ left: dels[index] ?? null, right: adds[index] ?? null });
    }
    run = [];
  };
  for (const line of hunk.lines) {
    if (line.kind === 'context') {
      flushRun();
      pairs.push({ left: line, right: line });
    } else {
      run.push(line);
    }
  }
  flushRun();
  return pairs;
}

/**
 * Flatten the parsed files into uniform rows. `collapsed` selects
 * which file paths render as header-only rows; `mode` selects
 * unified (one row per line) or split (one row per +/- pair).
 */
export function buildDiffRows(
  files: readonly PatchFile[],
  collapsed: ReadonlySet<string>,
  mode: 'unified' | 'split',
): DiffRow[] {
  const rows: DiffRow[] = [];
  files.forEach((file, fileIndex) => {
    const isCollapsed = collapsed.has(file.path);
    let hiddenLines = 0;
    for (const hunk of file.hunks) hiddenLines += hunk.lines.length;
    rows.push({ kind: 'file', fileIndex, file, collapsed: isCollapsed, hiddenLines });
    if (isCollapsed) return;
    for (const line of file.opaque) {
      rows.push({ kind: 'opaque', fileIndex, text: line });
    }
    for (const hunk of file.hunks) {
      rows.push({ kind: 'hunk', fileIndex, hunk });
      if (mode === 'unified') {
        for (const line of hunk.lines) {
          rows.push({ kind: 'line', fileIndex, left: line, right: line });
        }
      } else {
        for (const pair of pairHunkLines(hunk)) {
          rows.push({ kind: 'line', fileIndex, left: pair.left, right: pair.right });
        }
      }
    }
  });
  return rows;
}

/** The default collapsed set for a patch: only the large files. */
export function defaultCollapsedPaths(files: readonly PatchFile[]): Set<string> {
  const collapsed = new Set<string>();
  for (const file of files) {
    let lines = file.opaque.length;
    for (const hunk of file.hunks) lines += hunk.lines.length;
    if (lines > LARGE_FILE_LINES) collapsed.add(file.path);
  }
  return collapsed;
}

/** The first row index belonging to one file (for jump-to-file). */
export function fileStartIndex(rows: readonly DiffRow[], path: string): number {
  for (let index = 0; index < rows.length; index += 1) {
    const row = rows[index];
    if (row !== undefined && row.kind === 'file' && row.file.path === path) return index;
  }
  return -1;
}

/** The file path a row belongs to (for scroll → active-file sync). */
export function filePathOfRow(
  row: DiffRow | undefined,
  files: readonly PatchFile[],
): string | null {
  if (row === undefined) return null;
  return files[row.fileIndex]?.path ?? null;
}
