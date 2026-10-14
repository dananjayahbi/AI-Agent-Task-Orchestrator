'use client';

/**
 * File-tree grouping (MT-4.7-03; Section 13.2 "file tree ... jump to
 * files"; Section 9.7 authority note).
 *
 * Pure helpers: group a flat changed-file list into directory groups
 * (tree presentation), and derive status/renames purely from the
 * parsed patch headers — never reconstructed client-side (MT-4.7-03
 * risk note: renames use the patch's own headers).
 *
 * The **contract of record** for the file set is the backend's
 * `changed_files` (Section 9.7/7.2), which the tests assert equals
 * the parsed set; the tree renders parsed status markers joined onto
 * that authoritative list.
 */
import type { PatchFile, PatchFileStatus } from '@/lib/diff/parse';

export type TreeEntry = {
  /** Full repo-relative path (the join key to `changed_files`). */
  path: string;
  /** Path without the directory prefix (the leaf shown in the tree row). */
  leaf: string;
  /** Directory prefix ('' for repo-root files). */
  directory: string;
  status: PatchFileStatus | 'unknown';
  /** Rename source, from the patch header (never reconstructed). */
  oldPath: string | null;
  /** True when the entry has a diff section to jump to. */
  hasJumpTarget: boolean;
};

export type TreeGroup = {
  directory: string;
  entries: TreeEntry[];
};

/**
 * Build the tree entries for one patch, ordered as the backend lists
 * `changed_files` (first-seen patch order — Section 7.2). Files in
 * `changedFiles` but absent from the parse (should not happen for a
 * well-formed patch; defensive) degrade to `status: 'unknown'` with
 * no jump target — never an error, never a fabricated status.
 */
export function buildTreeEntries(
  changedFiles: readonly string[],
  parsedFiles: readonly PatchFile[],
): TreeEntry[] {
  const byPath = new Map(parsedFiles.map((file) => [file.path, file]));
  return changedFiles.map((path) => {
    const slash = path.lastIndexOf('/');
    const parsed = byPath.get(path);
    return {
      path,
      leaf: slash >= 0 ? path.slice(slash + 1) : path,
      directory: slash >= 0 ? path.slice(0, slash) : '',
      status: parsed?.status ?? 'unknown',
      oldPath: parsed?.oldPath ?? null,
      hasJumpTarget: parsed !== undefined && (parsed.hunks.length > 0 || parsed.isBinary),
    };
  });
}

/** Group entries by directory prefix, preserving first-seen order. */
export function groupByDirectory(entries: readonly TreeEntry[]): TreeGroup[] {
  const groups: TreeGroup[] = [];
  const byDirectory = new Map<string, TreeGroup>();
  for (const entry of entries) {
    let group = byDirectory.get(entry.directory);
    if (group === undefined) {
      group = { directory: entry.directory, entries: [] };
      byDirectory.set(entry.directory, group);
      groups.push(group);
    }
    group.entries.push(entry);
  }
  return groups;
}

/** The status marker text for a tree row (paired with color, never color alone). */
export const STATUS_MARKERS: Record<PatchFileStatus | 'unknown', string> = {
  modified: 'M',
  added: 'A',
  deleted: 'D',
  renamed: 'R',
  binary: 'B',
  unknown: '?',
};

/** The status marker's accessible description. */
export const STATUS_LABELS: Record<PatchFileStatus | 'unknown', string> = {
  modified: 'Modified',
  added: 'Added',
  deleted: 'Deleted',
  renamed: 'Renamed',
  binary: 'Binary',
  unknown: 'Status unknown',
};
