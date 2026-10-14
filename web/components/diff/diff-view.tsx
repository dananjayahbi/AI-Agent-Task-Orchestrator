'use client';

/**
 * Diff view (MT-4.7-02; Section 13.2 "unified/split toggle, syntax
 * highlighting, collapse large files"; Wave 9 exit: a 5,000-line patch
 * renders responsively).
 *
 * Renders the parsed patch through the board's windowing primitive
 * (`VirtualList`, MT-4.3-06) — the DOM stays bounded by the viewport,
 * not the patch size, which is what makes the 5,000-line acceptance
 * hold without a streaming design the plan never asked for. Rows are
 * uniform-height so one fixed-height window covers file headers, hunk
 * headers and lines alike.
 *
 * Stats discipline (Section 9.7; Section 20.5): the header displays
 * the **backend's** authoritative `diff_summary` (read defensively,
 * never recomputed). Per-file headers show identity, status and rule
 * flags — the backend publishes no per-file +/- counts (Section 7.2
 * `diff_summary` is resolution-scoped), and inventing them here would
 * be a client-rederived contract; the reading is recorded in the WP
 * changelog.
 *
 * Collapse (MT-4.7-02): files whose body exceeds `LARGE_FILE_LINES`
 * start collapsed to a header row with an expand affordance; any file
 * header toggles its section.
 *
 * The toggle persists per user session via `localStorage` (a view
 * preference, no backend field exists); unknown extensions fall back
 * to plain monospace through the highlighter's grammar table.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { VirtualList, type VirtualListHandle } from '@/components/board/virtual-list';
import { grammarForPath, tokenizeLine } from '@/lib/diff/highlight';
import type { FlaggedFiles } from '@/lib/diff/rule-flags';
import { rulesForPath } from '@/lib/diff/rule-flags';
import { RULE_LABELS } from '@/lib/diff/rules';
import type { PatchFile, PatchLine } from '@/lib/diff/parse';
import {
  buildDiffRows,
  defaultCollapsedPaths,
  filePathOfRow,
  fileStartIndex,
  rowKey,
  type DiffRow,
} from '@/lib/diff/rows';
import { formatDiffSummary, readDiffSummary } from '@/lib/diff/summary';
import { cn } from 'cn';

/** Fixed row height in px — one uniform window height for every row kind. */
export const DIFF_ROW_HEIGHT = 24;
const MODE_STORAGE_KEY = 'diff-viewer:mode';

export type DiffMode = 'unified' | 'split';

type DiffViewProps = {
  files: readonly PatchFile[];
  /** The resolution's `diff_summary` (Section 9.7 authoritative). */
  diffSummary: unknown;
  /** Flagged files by rule id (MT-4.7-05); empty map when none. */
  flags?: FlaggedFiles;
  /** Jump request from the tree; `nonce` increments per jump. */
  jumpRequest?: { path: string; nonce: number } | null;
  /** Scroll → active-file sync (tree highlight). */
  onActiveFileChange?: (path: string) => void;
  /** A manual toggle of the jumped file re-takes control from the jump expansion. */
  onJumpClear?: () => void;
  testId?: string;
};

function readStoredMode(): DiffMode {
  if (typeof window === 'undefined') return 'unified';
  try {
    return window.localStorage.getItem(MODE_STORAGE_KEY) === 'split' ? 'split' : 'unified';
  } catch {
    return 'unified';
  }
}

function LineContent({
  line,
  grammar,
}: {
  line: PatchLine;
  grammar: ReturnType<typeof grammarForPath>;
}) {
  const tokens = tokenizeLine(line.content, grammar);
  return (
    <span className="whitespace-pre">
      {tokens.map((token, index) => (
        <span
          key={index}
          className={cn(
            token.kind === 'keyword' && 'font-semibold text-primary',
            token.kind === 'string' && 'text-emerald-700 dark:text-emerald-300',
            token.kind === 'comment' && 'text-muted-foreground italic',
            token.kind === 'number' && 'text-sky-700 dark:text-sky-300',
          )}
        >
          {token.text}
        </span>
      ))}
      {line.noNewline && (
        <span className="ml-2 text-[10px] text-muted-foreground italic">
          {'\\ No newline at end of file'}
        </span>
      )}
    </span>
  );
}

function FlagBadges({ rules }: { rules: readonly string[] }) {
  if (rules.length === 0) return null;
  return (
    <span className="flex gap-1" data-testid="diff-file-flags">
      {rules.map((rule) => (
        <span
          key={rule}
          data-testid={`diff-file-flag-${rule}`}
          title={`Flagged by rule ${rule} (${RULE_LABELS[rule as keyof typeof RULE_LABELS] ?? 'unknown rule'})`}
          className="rounded-full border border-destructive/50 bg-destructive/10 px-1.5 text-[10px] font-semibold text-destructive"
        >
          {rule}
        </span>
      ))}
    </span>
  );
}

/** One uniform row: file header, hunk header, opaque text, or a diff line. */
function DiffRowView({
  row,
  files,
  flags,
  onToggleCollapse,
}: {
  row: DiffRow;
  files: readonly PatchFile[];
  flags: FlaggedFiles;
  onToggleCollapse: (path: string) => void;
}) {
  const file = files[row.fileIndex];

  if (row.kind === 'file') {
    if (file === undefined) return null;
    const rules = rulesForPath(flags, file.path);
    return (
      <div
        className="flex items-center gap-2 px-2"
        data-testid="diff-file-header"
        data-path={file.path}
      >
        <button
          type="button"
          data-testid={`diff-file-toggle-${file.path}`}
          aria-expanded={!row.collapsed}
          onClick={() => onToggleCollapse(file.path)}
          className="rounded px-1 text-muted-foreground hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span aria-hidden="true">{row.collapsed ? '▸' : '▾'}</span>
          <span className="sr-only">
            {row.collapsed ? `Expand ${file.path}` : `Collapse ${file.path}`}
          </span>
        </button>
        <span
          data-testid={`diff-file-status-${file.path}`}
          className={cn(
            'w-4 text-center font-mono text-[10px] font-semibold',
            file.status === 'added' && 'text-emerald-700 dark:text-emerald-300',
            file.status === 'deleted' && 'text-destructive',
            file.status === 'renamed' && 'text-sky-700 dark:text-sky-300',
            file.status === 'binary' && 'text-muted-foreground',
            file.status === 'modified' && 'text-foreground',
          )}
        >
          {file.status === 'added'
            ? 'A'
            : file.status === 'deleted'
              ? 'D'
              : file.status === 'renamed'
                ? 'R'
                : file.status === 'binary'
                  ? 'B'
                  : 'M'}
        </span>
        <span className="truncate font-mono text-[11px] text-foreground" title={file.path}>
          {file.path}
        </span>
        {file.oldPath !== null && (
          <span className="truncate font-mono text-[10px] text-muted-foreground">
            (from {file.oldPath})
          </span>
        )}
        <FlagBadges rules={rules} />
        {row.collapsed && (
          <span
            data-testid={`diff-file-collapsed-${file.path}`}
            className="text-[10px] text-muted-foreground"
          >
            {row.hiddenLines} lines hidden — expand to view
          </span>
        )}
        {file.isBinary && (
          <span className="text-[10px] text-muted-foreground">Binary file (no text diff)</span>
        )}
      </div>
    );
  }

  if (row.kind === 'hunk') {
    return (
      <div
        data-testid="diff-hunk-header"
        className="truncate px-8 font-mono text-[10px] text-muted-foreground"
      >
        {row.hunk.header}
      </div>
    );
  }

  if (row.kind === 'opaque') {
    return (
      <div
        data-testid="diff-opaque-line"
        className="truncate px-8 font-mono text-[11px] text-muted-foreground"
      >
        {row.text}
      </div>
    );
  }

  if (file === undefined) return null;
  const grammar = grammarForPath(file.path);

  // Unified: one pane. Split: left = old side, right = new side.
  const renderPane = (line: PatchLine | null, side: 'unified' | 'left' | 'right') => {
    if (line === null) {
      return <span className="block h-full w-full" data-testid={`diff-line-empty-${side}`} />;
    }
    const sign = line.kind === 'add' ? '+' : line.kind === 'del' ? '−' : ' ';
    return (
      <span
        data-testid={`diff-line-${side}`}
        data-line-kind={line.kind}
        className={cn(
          'flex h-full items-center gap-1 px-1',
          line.kind === 'add' && 'bg-emerald-500/10',
          line.kind === 'del' && 'bg-red-500/10',
        )}
      >
        <span className="w-10 shrink-0 text-right font-mono text-[10px] text-muted-foreground">
          {side === 'right' ? (line.newLine ?? '') : (line.oldLine ?? '')}
        </span>
        <span
          aria-hidden="true"
          className={cn(
            'w-3 shrink-0 text-center font-mono text-[11px]',
            line.kind === 'add' && 'text-emerald-700 dark:text-emerald-300',
            line.kind === 'del' && 'text-destructive',
          )}
        >
          {sign}
        </span>
        <span className="min-w-0 font-mono text-[11px]">
          <LineContent line={line} grammar={grammar} />
        </span>
      </span>
    );
  };

  if (row.left === row.right) {
    // Unified (or a context line in split): one full-width pane.
    return <div className="flex h-full">{renderPane(row.left, 'unified')}</div>;
  }
  return (
    <div className="grid h-full grid-cols-2 divide-x divide-border">
      {renderPane(row.left, 'left')}
      {renderPane(row.right, 'right')}
    </div>
  );
}

export function DiffView({
  files,
  diffSummary,
  flags,
  jumpRequest,
  onActiveFileChange,
  onJumpClear,
  testId,
}: DiffViewProps) {
  const [mode, setMode] = useState<DiffMode>(readStoredMode);
  const [collapsed, setCollapsed] = useState<Set<string>>(() => defaultCollapsedPaths(files));
  const listRef = useRef<VirtualListHandle>(null);

  // Jump-to-file (MT-4.7-03): the jump expands its target by pure
  // derivation rather than a setState-in-effect — the expansion lives
  // only while the jump is current; a manual toggle of the jumped
  // file clears the jump (event handler) and the user's collapse wins.
  const effectiveCollapsed = useMemo(() => {
    if (jumpRequest === null || jumpRequest === undefined) return collapsed;
    const next = new Set(collapsed);
    next.delete(jumpRequest.path);
    return next;
  }, [collapsed, jumpRequest]);

  const rows = useMemo(
    () => buildDiffRows(files, effectiveCollapsed, mode),
    [files, effectiveCollapsed, mode],
  );
  const stats = useMemo(() => readDiffSummary(diffSummary), [diffSummary]);

  const onToggleCollapse = useCallback(
    (path: string) => {
      if (path === jumpRequest?.path) onJumpClear?.();
      setCollapsed((current) => {
        const next = new Set(current);
        if (next.has(path)) next.delete(path);
        else next.add(path);
        return next;
      });
    },
    [jumpRequest, onJumpClear],
  );

  const changeMode = useCallback((next: DiffMode) => {
    setMode(next);
    try {
      window.localStorage.setItem(MODE_STORAGE_KEY, next);
    } catch {
      // Preference persistence is best-effort; the toggle still works.
    }
  }, []);

  // Scroll to the jumped file's header row — once per jump request
  // (the header row exists in every state, so the index is stable
  // across the expand rebuild; scrolling is a DOM-side effect, never
  // a state update).
  const scrolledJumpRef = useRef<typeof jumpRequest>(null);
  useEffect(() => {
    if (jumpRequest === null || jumpRequest === undefined) return;
    if (scrolledJumpRef.current === jumpRequest) return;
    scrolledJumpRef.current = jumpRequest;
    const index = fileStartIndex(rows, jumpRequest.path);
    if (index >= 0) listRef.current?.scrollToIndex(index);
  }, [jumpRequest, rows]);

  // Scroll → active-file sync, throttled by row-boundary changes
  // (VirtualList notifies once per window change, never per pixel).
  const lastActiveRef = useRef<string | null>(null);
  const handleVisibleRange = useCallback(
    (startIndex: number) => {
      const path = filePathOfRow(rows[startIndex], files);
      if (path !== null && path !== lastActiveRef.current) {
        lastActiveRef.current = path;
        onActiveFileChange?.(path);
      }
    },
    [rows, files, onActiveFileChange],
  );

  return (
    <div data-testid={testId ?? 'diff-view'} className="grid gap-1">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {stats !== null ? (
          <span
            data-testid="diff-view-stats"
            data-files={stats.files ?? ''}
            className="font-mono text-[11px] text-muted-foreground"
          >
            {formatDiffSummary(stats)} (backend-computed)
          </span>
        ) : (
          <span />
        )}
        <div
          role="group"
          aria-label="Diff view mode"
          className="flex overflow-hidden rounded-md border border-border"
        >
          <button
            type="button"
            data-testid="diff-mode-unified"
            aria-pressed={mode === 'unified'}
            onClick={() => changeMode('unified')}
            className={cn(
              'px-2 py-0.5 text-[11px]',
              mode === 'unified' ? 'bg-primary text-primary-foreground' : 'bg-card text-foreground',
            )}
          >
            Unified
          </button>
          <button
            type="button"
            data-testid="diff-mode-split"
            aria-pressed={mode === 'split'}
            onClick={() => changeMode('split')}
            className={cn(
              'px-2 py-0.5 text-[11px]',
              mode === 'split' ? 'bg-primary text-primary-foreground' : 'bg-card text-foreground',
            )}
          >
            Split
          </button>
        </div>
      </div>
      <div className="overflow-x-auto rounded-md border border-border">
        <VirtualList<DiffRow>
          ref={listRef}
          items={rows}
          itemKey={(row) => rowKey(row, files[row.fileIndex] ?? { path: 'unknown' })}
          itemHeight={DIFF_ROW_HEIGHT}
          label="Diff lines"
          testId={testId === undefined ? 'diff-lines' : `${testId}-lines`}
          className="text-foreground"
          onVisibleRangeChange={handleVisibleRange}
          renderItem={(row) => (
            <DiffRowView
              row={row}
              files={files}
              flags={flags ?? new Map()}
              onToggleCollapse={onToggleCollapse}
            />
          )}
        />
      </div>
    </div>
  );
}
