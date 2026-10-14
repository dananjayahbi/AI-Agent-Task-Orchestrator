/**
 * MT-4.7-03 — file tree with jump-to-file: grouping by directory,
 * status markers from the patch headers, the Section 9.7 consistency
 * guard (tree file set equals the backend's `changed_files`),
 * jump wiring + scroll → active-file sync through the DiffPanel
 * composition, Section 13.4 keyboard navigation, and the stats-only
 * degradation to a plain non-jumping list (MT-4.7-04 contract).
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { DiffPanel } from '@/components/diff/diff-panel';
import { DIFF_ROW_HEIGHT } from '@/components/diff/diff-view';
import { FALLBACK_VIEWPORT_HEIGHT } from '@/components/board/virtual-list';
import { buildTreeEntries, groupByDirectory } from '@/lib/diff/file-tree';
import { parseUnifiedPatch } from '@/lib/diff/parse';
import type { AuditReport, Resolution } from '@/lib/api/generated/types.gen';
import {
  MULTI_FILE_RENAME_PATCH,
  SINGLE_FILE_PATCH,
  makeLargePatch,
  oversizePatchPayload,
  patchBodyPayload,
  ruleRow,
} from './fixtures';
import { installApi, jsonResponse, renderWithQueryClient } from '../helpers/api';
import { makeResolution } from '../helpers/task-detail';

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

const filesOf = (text: string) => parseUnifiedPatch(text).files;

describe('tree grouping and consistency (MT-4.7-03; Section 9.7)', () => {
  it('groups entries by directory, preserving first-seen order', () => {
    const files = filesOf(MULTI_FILE_RENAME_PATCH);
    const entries = buildTreeEntries(['src/new_name.py', 'docs/readme.md'], files);
    const groups = groupByDirectory(entries);
    expect(groups.map((group) => group.directory)).toEqual(['src', 'docs']);
    expect(groups[0]?.entries[0]?.leaf).toBe('new_name.py');
    // Rename shows the patch's own header, never reconstructed.
    expect(groups[0]?.entries[0]?.oldPath).toBe('src/old_name.py');
    expect(groups[0]?.entries[0]?.status).toBe('renamed');
  });

  it('consistency guard: the tree file set equals the backend changed_files', () => {
    const files = filesOf(MULTI_FILE_RENAME_PATCH);
    const changedFiles = ['src/new_name.py', 'docs/readme.md']; // Section 7.2 authority
    const entries = buildTreeEntries(changedFiles, files);
    expect(entries.map((entry) => entry.path).sort()).toEqual([...changedFiles].sort());
  });

  it('a changed file missing from the parse degrades to unknown status, no error', () => {
    const entries = buildTreeEntries(['ghost/file.txt'], filesOf(SINGLE_FILE_PATCH));
    expect(entries[0]?.status).toBe('unknown');
    expect(entries[0]?.hasJumpTarget).toBe(false);
  });
});

/** Panel harness: mock `GET /resolutions/{id}/patch` and render. */
function panelHarness(
  patchResponse: unknown,
  resolutionOverrides: Partial<Resolution> = {},
  report?: AuditReport,
) {
  installApi([
    {
      method: 'GET',
      match: /\/api\/v1\/resolutions\/[^/]+\/patch(\?|$)/,
      respond: () => jsonResponse(patchResponse),
    },
  ]);
  const resolution = makeResolution(resolutionOverrides);
  renderWithQueryClient(<DiffPanel resolution={resolution} report={report} />);
  return resolution;
}

describe('FileTree in the panel (MT-4.7-03)', () => {
  it('renders grouped entries with status markers and jumps on select', async () => {
    panelHarness(patchBodyPayload(MULTI_FILE_RENAME_PATCH), {
      changed_files: ['src/new_name.py', 'docs/readme.md'],
    });
    await waitFor(() => expect(screen.getByTestId('diff-panel-ready')).toBeTruthy());

    const renamed = screen.getByTestId('tree-entry-src/new_name.py');
    expect(renamed.getAttribute('role')).toBe('treeitem');
    expect(within(renamed).getByText('R')).toBeTruthy(); // rename marker
    expect(within(renamed).getByText('(from old_name.py)')).toBeTruthy();

    // Jump: selecting the second file scrolls the diff to its section.
    const list = screen.getByTestId('diff-view-lines');
    const before = list.scrollTop;
    fireEvent.click(screen.getByTestId('tree-entry-docs/readme.md'));
    await waitFor(() => {
      expect(list.scrollTop).toBeGreaterThan(before);
      expect(screen.getByTestId('tree-entry-docs/readme.md').getAttribute('aria-selected')).toBe(
        'true',
      );
    });
  });

  it('scroll position updates the active file in the tree (sync)', async () => {
    // Two files: a collapsed-by-default large one, then an expanded
    // small one — scrolling into the second file's rows must move the
    // tree's active marker from file one to file two.
    const twoFilePatch = [
      'diff --git a/first/big.ts b/first/big.ts',
      '--- a/first/big.ts',
      '+++ b/first/big.ts',
      '@@ -1,2 +1,2 @@',
      ' const a = 1;',
      '-const b = 2;',
      '+const b = 3;',
      'diff --git a/second/small.ts b/second/small.ts',
      '--- a/second/small.ts',
      '+++ b/second/small.ts',
      '@@ -1,150 +1,150 @@',
      ...Array.from({ length: 150 }, (_, index) => ` export const v${index} = ${index};`),
      '',
    ].join('\n');
    panelHarness(patchBodyPayload(twoFilePatch), {
      changed_files: ['first/big.ts', 'second/small.ts'],
    });
    await waitFor(() => expect(screen.getByTestId('diff-panel-ready')).toBeTruthy());
    // Mount syncs the active file to the first row (first file).
    await waitFor(() =>
      expect(screen.getByTestId('tree-entry-first/big.ts').getAttribute('aria-selected')).toBe(
        'true',
      ),
    );
    // Scroll well into the second file's rows.
    const list = screen.getByTestId('diff-view-lines');
    fireEvent.scroll(list, { target: { scrollTop: 20 * DIFF_ROW_HEIGHT } });
    await waitFor(() =>
      expect(screen.getByTestId('tree-entry-second/small.ts').getAttribute('aria-selected')).toBe(
        'true',
      ),
    );
    expect(screen.getByTestId('tree-entry-first/big.ts').getAttribute('aria-selected')).toBe(
      'false',
    );
  });

  it('keyboard navigation moves focus per Section 13.4 (arrows, Home/End)', async () => {
    panelHarness(patchBodyPayload(MULTI_FILE_RENAME_PATCH), {
      changed_files: ['src/new_name.py', 'docs/readme.md'],
    });
    await waitFor(() => expect(screen.getByTestId('diff-panel-ready')).toBeTruthy());

    const first = screen.getByTestId('tree-entry-src/new_name.py');
    first.focus();
    fireEvent.keyDown(first, { key: 'ArrowDown' });
    expect(document.activeElement).toBe(screen.getByTestId('tree-entry-docs/readme.md'));
    fireEvent.keyDown(document.activeElement as Element, { key: 'ArrowUp' });
    expect(document.activeElement).toBe(first);
    fireEvent.keyDown(document.activeElement as Element, { key: 'End' });
    expect(document.activeElement).toBe(screen.getByTestId('tree-entry-docs/readme.md'));
    fireEvent.keyDown(document.activeElement as Element, { key: 'Home' });
    expect(document.activeElement).toBe(first);
  });

  it('activating an entry jumps (button click = Enter/Space semantics)', async () => {
    panelHarness(patchBodyPayload(MULTI_FILE_RENAME_PATCH), {
      changed_files: ['src/new_name.py', 'docs/readme.md'],
    });
    await waitFor(() => expect(screen.getByTestId('diff-panel-ready')).toBeTruthy());
    const entry = screen.getByTestId('tree-entry-docs/readme.md');
    entry.focus();
    // jsdom does not synthesize clicks from Enter on buttons; the
    // real browser does (native button semantics) — assert the
    // activation path itself jumps and selects.
    fireEvent.click(entry);
    await waitFor(() => expect(entry.getAttribute('aria-selected')).toBe('true'));
    expect(screen.getByTestId('diff-view-lines').scrollTop).toBeGreaterThan(0);
  });
});

describe('stats-only degradation (MT-4.7-03/04 contract)', () => {
  it('the tree degrades to a plain non-jumping list in the oversize state', async () => {
    panelHarness(oversizePatchPayload(), {
      changed_files: ['src/new_name.py', 'docs/readme.md'],
    });
    await waitFor(() => expect(screen.getByTestId('diff-panel-oversize')).toBeTruthy());
    const tree = screen.getByTestId('file-tree-oversize');
    // Plain list entries: no treeitems, no buttons — no jump targets.
    expect(within(tree).queryAllByRole('treeitem')).toHaveLength(0);
    expect(within(tree).queryAllByRole('button')).toHaveLength(0);
    expect(within(tree).getByTestId('tree-entry-src/new_name.py')).toBeTruthy();
    expect(within(tree).getByTestId('tree-entry-docs/readme.md')).toBeTruthy();
    // Status is unknown without a body — never invented.
    expect(within(tree).getByTestId('tree-entry-src/new_name.py').textContent).toContain('?');
  });

  it('the fallback viewport window reports the full row count implicitly (bounded DOM)', async () => {
    panelHarness(patchBodyPayload(makeLargePatch(4000)), {
      changed_files: ['generated/big.ts'],
    });
    await waitFor(() => expect(screen.getByTestId('diff-panel-ready')).toBeTruthy());
    const viewportRows = Math.ceil(FALLBACK_VIEWPORT_HEIGHT / DIFF_ROW_HEIGHT);
    // Collapsed by default (large file) → header only; no line rows mounted.
    expect(document.querySelectorAll('[data-testid^="diff-line-"]').length).toBe(0);
    expect(document.querySelectorAll('[data-testid="diff-file-header"]').length).toBe(1);
    expect(viewportRows).toBeLessThan(100);
  });
});

describe('rule-flag markers (MT-4.7-05)', () => {
  const flaggedReport = (files?: string[]) =>
    ({
      policy_rule_results: [
        ruleRow('R1', false, 'test_failure'),
        ruleRow('R2', false, 'scope_violation', files),
        ruleRow('R3', true),
        ruleRow('R4', false, 'migration_detected', files),
        ruleRow('R7', false, 'low_confidence'),
      ],
    }) as unknown as AuditReport;

  it('marks flagged tree entries with verbatim rule ids and jumps to them', async () => {
    panelHarness(
      patchBodyPayload(MULTI_FILE_RENAME_PATCH),
      {
        changed_files: ['src/new_name.py', 'docs/readme.md'],
      },
      flaggedReport(['docs/readme.md']),
    );
    await waitFor(() => expect(screen.getByTestId('diff-panel-ready')).toBeTruthy());

    const flagged = screen.getByTestId('tree-entry-docs/readme.md');
    expect(within(flagged).getByTestId('tree-flag-R2-docs/readme.md')).toBeTruthy();
    expect(within(flagged).getByTestId('tree-flag-R4-docs/readme.md')).toBeTruthy();
    // The unflagged file carries no badges.
    const clean = screen.getByTestId('tree-entry-src/new_name.py');
    expect(within(clean).queryAllByText(/^R[0-9]$/)).toHaveLength(0);

    // Jump-to-flagged rides the normal tree select path.
    fireEvent.click(flagged);
    await waitFor(() => expect(flagged.getAttribute('aria-selected')).toBe('true'));
    expect(screen.getByTestId('diff-view-lines').scrollTop).toBeGreaterThan(0);
  });

  it('non-file rules (R1, R7) never produce file markers; passing rules never flag', async () => {
    panelHarness(
      patchBodyPayload(SINGLE_FILE_PATCH),
      {
        changed_files: ['web/login.tsx'],
      },
      flaggedReport(['web/login.tsx']),
    ); // R1/R7 rows carry files but are not file-based
    await waitFor(() => expect(screen.getByTestId('diff-panel-ready')).toBeTruthy());
    const entry = screen.getByTestId('tree-entry-web/login.tsx');
    // Only the file-based failing rules (R2, R4) marked — R1/R7 ignored.
    expect(within(entry).getByTestId('tree-flag-R2-web/login.tsx')).toBeTruthy();
    expect(within(entry).getByTestId('tree-flag-R4-web/login.tsx')).toBeTruthy();
    expect(within(entry).queryByTestId('tree-flag-R1-web/login.tsx')).toBeNull();
    expect(within(entry).queryByTestId('tree-flag-R7-web/login.tsx')).toBeNull();
    expect(within(entry).queryByTestId('tree-flag-R3-web/login.tsx')).toBeNull(); // passing
  });

  it('an absent audit report produces no markers and no errors', async () => {
    panelHarness(patchBodyPayload(SINGLE_FILE_PATCH), {
      changed_files: ['web/login.tsx'],
    });
    await waitFor(() => expect(screen.getByTestId('diff-panel-ready')).toBeTruthy());
    const entry = screen.getByTestId('tree-entry-web/login.tsx');
    expect(within(entry).queryAllByText(/^R[0-9]$/)).toHaveLength(0);
  });

  it('markers remain visible in the stats-only fallback state', async () => {
    panelHarness(
      oversizePatchPayload(),
      {
        changed_files: ['docs/readme.md'],
      },
      flaggedReport(['docs/readme.md']),
    );
    await waitFor(() => expect(screen.getByTestId('diff-panel-oversize')).toBeTruthy());
    const tree = screen.getByTestId('file-tree-oversize');
    expect(within(tree).getByTestId('tree-flag-R2-docs/readme.md')).toBeTruthy();
  });

  it('multiple rules flagging one file show all rule ids', async () => {
    const report = {
      policy_rule_results: [
        ruleRow('R2', false, 'scope_violation', ['docs/readme.md']),
        ruleRow('R3', false, 'critical_path_changed', ['docs/readme.md']),
        ruleRow('R5', false, 'sensitive_config_changed', ['docs/readme.md']),
      ],
    } as unknown as AuditReport;
    panelHarness(
      patchBodyPayload(MULTI_FILE_RENAME_PATCH),
      {
        changed_files: ['src/new_name.py', 'docs/readme.md'],
      },
      report,
    );
    await waitFor(() => expect(screen.getByTestId('diff-panel-ready')).toBeTruthy());
    const flagged = screen.getByTestId('tree-entry-docs/readme.md');
    expect(within(flagged).getByTestId('tree-flag-R2-docs/readme.md')).toBeTruthy();
    expect(within(flagged).getByTestId('tree-flag-R3-docs/readme.md')).toBeTruthy();
    expect(within(flagged).getByTestId('tree-flag-R5-docs/readme.md')).toBeTruthy();
  });

  it('marks flagged file sections in the diff view too', async () => {
    panelHarness(
      patchBodyPayload(MULTI_FILE_RENAME_PATCH),
      {
        changed_files: ['src/new_name.py', 'docs/readme.md'],
      },
      flaggedReport(['docs/readme.md']),
    );
    await waitFor(() => expect(screen.getByTestId('diff-panel-ready')).toBeTruthy());
    fireEvent.click(screen.getByTestId('tree-entry-docs/readme.md'));
    await waitFor(() => expect(screen.getByTestId('diff-file-flag-R2')).toBeTruthy());
  });
});
