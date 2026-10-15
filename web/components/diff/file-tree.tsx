'use client';

/**
 * File tree with jump-to-file (MT-4.7-03; Section 13.2 "file tree ...
 * jump to files flagged by rule results"; Section 13.4 keyboard nav).
 *
 * The entry list is built over the **backend's** `changed_files`
 * (Section 9.7/7.2 contract of record) joined with the parsed patch's
 * per-file status/rename headers — the tree never invents a file the
 * backend did not author, and renames display the patch's own headers
 * (MT-4.7-03 risk note). Directory groups collapse by default on
 * large trees is *not* done here — flat groups with sticky headers
 * keep jump targets visible (Section 13.4: keyboard users must reach
 * every file); deep-tree collapse is a WP-4.11 polish item.
 *
 * Keyboard (Section 13.4): the list is a `role="tree"` with roving
 * tabindex — ArrowUp/ArrowDown move, Home/End jump, Enter/Space
 * selects (jump). Only catalog error codes exist in this area — the
 * tree itself has no error state (it renders data it was given).
 *
 * Stats-only degradation (Section 9.7 oversize; MT-4.7-04): when the
 * patch has no body there is nothing to scroll to, so entries render
 * as a plain non-interactive list (`jumpEnabled=false`) — no buttons,
 * no focus traps, no errors. Rule-flag badges (MT-4.7-05) still mark
 * entries in this mode: flags come from the audit report, not the
 * patch body.
 */
import { useRef } from 'react';

import { nextRovingIndex } from '@/lib/a11y/roving';
import type { TreeEntry } from '@/lib/diff/file-tree';
import { STATUS_LABELS, STATUS_MARKERS } from '@/lib/diff/file-tree';
import type { FlaggedFiles } from '@/lib/diff/rule-flags';
import { rulesForPath } from '@/lib/diff/rule-flags';
import { RULE_LABELS } from '@/lib/diff/rules';
import { cn } from 'cn';

type FileTreeProps = {
  entries: readonly TreeEntry[];
  /** Directory groups (from `groupByDirectory`), in first-seen order. */
  groups: ReadonlyArray<{ directory: string; entries: readonly TreeEntry[] }>;
  /** Flagged files by rule id (MT-4.7-05). */
  flags?: FlaggedFiles;
  /** Currently active file (scroll-sync highlight). */
  activePath?: string | null;
  /** False in the stats-only fallback — entries render as a plain list. */
  jumpEnabled: boolean;
  /** Jump request (path chosen — from click, Enter, or a flag badge). */
  onSelect: (path: string) => void;
  testId?: string;
};

function TreeRow({
  entry,
  rules,
  active,
  jumpEnabled,
  onSelect,
}: {
  entry: TreeEntry;
  rules: readonly string[];
  active: boolean;
  jumpEnabled: boolean;
  onSelect: (path: string) => void;
}) {
  const marker = STATUS_MARKERS[entry.status];
  const label = STATUS_LABELS[entry.status];
  const content = (
    <>
      <span
        aria-hidden="true"
        title={label}
        className={cn(
          'w-4 shrink-0 text-center font-mono text-[10px] font-semibold',
          entry.status === 'added' && 'text-emerald-700 dark:text-emerald-300',
          entry.status === 'deleted' && 'text-destructive',
          entry.status === 'renamed' && 'text-sky-700 dark:text-sky-300',
          (entry.status === 'binary' || entry.status === 'unknown') && 'text-muted-foreground',
          entry.status === 'modified' && 'text-foreground',
        )}
      >
        {marker}
      </span>
      <span className="sr-only">{label}: </span>
      <span className="truncate font-mono text-[11px]" title={entry.path}>
        {entry.leaf}
      </span>
      {entry.oldPath !== null && (
        <span className="truncate font-mono text-[10px] text-muted-foreground">
          (from {entry.oldPath.split('/').pop()})
        </span>
      )}
      {rules.map((rule) => (
        <span
          key={rule}
          data-testid={`tree-flag-${rule}-${entry.path}`}
          title={`Flagged by rule ${rule} (${RULE_LABELS[rule as keyof typeof RULE_LABELS] ?? 'unknown rule'})`}
          className="shrink-0 rounded-full border border-destructive/50 bg-destructive/10 px-1 text-[10px] font-semibold text-destructive"
        >
          {rule}
        </span>
      ))}
    </>
  );

  if (!jumpEnabled || !entry.hasJumpTarget) {
    return (
      <div
        data-testid={`tree-entry-${entry.path}`}
        data-path={entry.path}
        className="flex items-center gap-1.5 rounded px-1.5 py-0.5 text-muted-foreground"
      >
        {content}
      </div>
    );
  }

  return (
    <button
      type="button"
      role="treeitem"
      aria-selected={active}
      data-testid={`tree-entry-${entry.path}`}
      data-path={entry.path}
      tabIndex={active ? 0 : -1}
      onClick={() => onSelect(entry.path)}
      className={cn(
        'flex w-full items-center gap-1.5 rounded px-1.5 py-0.5 text-left outline-none',
        'hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring',
        active && 'bg-muted font-semibold',
      )}
    >
      {content}
    </button>
  );
}

export function FileTree({
  entries,
  groups,
  flags,
  activePath,
  jumpEnabled,
  onSelect,
  testId,
}: FileTreeProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Roving focus (Section 13.4): arrows move between treeitems, the
  // focused row scrolls into view before focusing.
  const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const container = containerRef.current;
    if (container === null) return;
    const items = Array.from(container.querySelectorAll<HTMLElement>('[role="treeitem"]'));
    // MT-4.11-02: shared roving math (lib/a11y/roving). `currentIndex` is
    // -1 when nothing is focused — ArrowDown then lands on the first row
    // and ArrowUp clamps to it, matching the pre-shared behavior.
    const currentIndex = items.findIndex((item) => item === document.activeElement);
    const nextIndex = nextRovingIndex(event.key, currentIndex, items.length);
    if (nextIndex === null) return;
    event.preventDefault();
    const next = items[nextIndex];
    // Optional call: environments without layout (jsdom) may not
    // implement scrollIntoView; focus must not depend on it.
    next?.scrollIntoView?.({ block: 'nearest' });
    next?.focus();
  };

  return (
    <div
      ref={containerRef}
      data-testid={testId ?? 'file-tree'}
      role="tree"
      aria-label="Changed files"
      onKeyDown={onKeyDown}
      className="grid gap-2 self-start overflow-y-auto rounded-md border border-border p-2"
    >
      {entries.length === 0 ? (
        <p data-testid="file-tree-empty" className="text-xs text-muted-foreground">
          No changed files.
        </p>
      ) : (
        groups.map((group) => (
          <div key={group.directory || '(root)'} className="grid gap-0.5">
            <p
              className="truncate font-mono text-[10px] text-muted-foreground"
              data-testid="tree-group"
            >
              {group.directory === '' ? '(repository root)' : `${group.directory}/`}
            </p>
            {group.entries.map((entry) => (
              <TreeRow
                key={entry.path}
                entry={entry}
                rules={rulesForPath(flags ?? new Map(), entry.path)}
                active={activePath === entry.path}
                jumpEnabled={jumpEnabled}
                onSelect={onSelect}
              />
            ))}
          </div>
        ))
      )}
    </div>
  );
}
