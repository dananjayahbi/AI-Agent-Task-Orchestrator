'use client';

/**
 * Resolution diff panel (MT-4.7-01…05 composition; Sections 9.2, 9.7,
 * 13.2). The hosted entry point the task detail's resolutions section
 * (and later the review panel, WP-4.8) mounts for one resolution:
 *
 *  - fetches the stored patch through the generated client
 *    (NFR-11) with distinct loading / error states and catalog-only
 *    error copy (Section 20.4 item 5);
 *  - interprets both Section 9.7 paths explicitly — a body parses to
 *    files/hunks/lines, an oversize/stats-only payload renders the
 *    "diff too large" marker (never an empty diff masquerade);
 *  - composes the file tree (MT-4.7-03) beside the unified/split
 *    view (MT-4.7-02), with rule-flag markers (MT-4.7-05) riding on
 *    both and jump-to-file wiring them together;
 *  - degrades honestly: stats-only payloads keep the tree as a
 *    plain non-jumping list; an empty diff (zero changed files) is a
 *    distinct state from "diff too large".
 *
 * The authoritative `diff_summary` / `changed_files` come from the
 * Task Resolution row (Section 7.2) the caller passes in — the patch
 * payload only supplies structure and the server's marker.
 */
import { useCallback, useMemo, useState } from 'react';

import { DiffTooLarge } from '@/components/diff/diff-too-large';
import { DiffView } from '@/components/diff/diff-view';
import { FileTree } from '@/components/diff/file-tree';
import { ErrorState } from '@/components/errors/error-state';
import { EmptyState } from '@/components/states/empty-state';
import { LoadingState } from '@/components/states/loading-state';
import type { AuditReport, Resolution } from '@/lib/api/generated/types.gen';
import { buildTreeEntries, groupByDirectory } from '@/lib/diff/file-tree';
import { interpretPatchPayload } from '@/lib/diff/parse';
import { extractFlaggedFiles } from '@/lib/diff/rule-flags';
import { resolveError } from '@/lib/errors';
import { layout } from '@/lib/layout/styles';
import { useResolutionPatchQuery } from '@/lib/queries/resolution-patch';

type DiffPanelProps = {
  /** The Section 7.2 resolution row — authoritative stats + file list. */
  resolution: Resolution;
  /** The paired audit report (Section 7.2) — rule flags source; optional. */
  report?: AuditReport;
  testId?: string;
};

export function DiffPanel({ resolution, report, testId }: DiffPanelProps) {
  const patchQuery = useResolutionPatchQuery(resolution.id, true);
  const [jump, setJump] = useState<{ path: string; nonce: number } | null>(null);
  const [activePath, setActivePath] = useState<string | null>(null);

  const flags = useMemo(
    () => extractFlaggedFiles(report?.policy_rule_results ?? null),
    [report?.policy_rule_results],
  );

  const onSelect = useCallback((path: string) => {
    setActivePath(path);
    setJump((current) => ({ path, nonce: (current?.nonce ?? 0) + 1 }));
  }, []);

  let body: React.ReactNode;
  if (patchQuery.isPending) {
    body = <LoadingState label="Loading diff…" />;
  } else if (patchQuery.isError) {
    const error = resolveError(patchQuery.error);
    body = (
      <ErrorState
        title={error.title}
        message={error.message}
        requestId={error.requestId}
        onRetry={() => void patchQuery.refetch()}
      />
    );
  } else {
    const result = interpretPatchPayload(patchQuery.data);
    // The backend's file list is the contract of record (Section 9.7):
    // the tree renders it regardless of which path the payload took.
    const entries = buildTreeEntries(
      resolution.changed_files,
      result.kind === 'parsed' ? result.patch.files : [],
    );
    const groups = groupByDirectory(entries);

    if (result.kind === 'no-body') {
      body = (
        <div className="grid gap-3" data-testid="diff-panel-oversize">
          <DiffTooLarge marker={result.marker} diffSummary={resolution.diff_summary} />
          <FileTree
            entries={entries}
            groups={groups}
            flags={flags}
            jumpEnabled={false}
            onSelect={onSelect}
            testId="file-tree-oversize"
          />
        </div>
      );
    } else if (result.patch.files.length === 0) {
      body = (
        <div className="grid gap-3" data-testid="diff-panel-empty">
          <EmptyState
            title="No changes in this patch"
            description="The stored patch parsed to zero changed files — distinct from a patch that was too large to store."
          />
          <FileTree
            entries={entries}
            groups={groups}
            flags={flags}
            jumpEnabled={false}
            onSelect={onSelect}
            testId="file-tree-empty-patch"
          />
        </div>
      );
    } else {
      body = (
        <div className={layout.diffPanes} data-testid="diff-panel-ready">
          <FileTree
            entries={entries}
            groups={groups}
            flags={flags}
            activePath={activePath}
            jumpEnabled
            onSelect={onSelect}
          />
          <DiffView
            files={result.patch.files}
            diffSummary={resolution.diff_summary}
            flags={flags}
            jumpRequest={jump}
            onActiveFileChange={setActivePath}
            onJumpClear={() => setJump(null)}
            testId={testId === undefined ? 'diff-view' : `${testId}-view`}
          />
        </div>
      );
    }
  }

  return (
    <section
      data-testid={testId ?? 'diff-panel'}
      aria-label={`Diff for attempt ${resolution.attempt_number}`}
      className="grid gap-2"
    >
      <h3 className="text-xs font-semibold text-foreground">
        Diff — {resolution.branch_name} @{' '}
        <code className="font-mono">{resolution.commit_sha.slice(0, 12)}</code>
      </h3>
      {body}
    </section>
  );
}
