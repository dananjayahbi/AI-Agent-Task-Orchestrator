/**
 * MT-4.7-04 — the large-diff fallback: a stats-only/oversize payload
 * renders Section 9.7's verbatim "diff too large" marker plus the
 * authoritative stats and the file list; normal payloads never show
 * the marker; an empty diff is distinguishable from the oversize
 * state; and no diff content is ever fabricated client-side
 * (Section 9.7 authority rule). The marker phrase is shared with
 * WP-5.8 through `DIFF_TOO_LARGE_MARKER` — one constant asserted here.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { DiffPanel } from '@/components/diff/diff-panel';
import { DiffTooLarge } from '@/components/diff/diff-too-large';
import { DIFF_TOO_LARGE_MARKER } from '@/lib/diff/parse';
import type { AuditReport } from '@/lib/api/generated/types.gen';
import { SINGLE_FILE_PATCH, oversizePatchPayload, patchBodyPayload, ruleRow } from './fixtures';
import { errorResponse, installApi, jsonResponse, renderWithQueryClient } from '../helpers/api';
import { makeResolution } from '../helpers/task-detail';

afterEach(() => {
  vi.unstubAllGlobals();
});

function harness(
  patchResponse: unknown,
  overrides: Partial<Record<string, unknown>> = {},
  report?: AuditReport,
) {
  installApi([
    {
      method: 'GET',
      match: /\/api\/v1\/resolutions\/[^/]+\/patch(\?|$)/,
      respond: () => jsonResponse(patchResponse),
    },
  ]);
  const resolution = makeResolution(overrides);
  renderWithQueryClient(<DiffPanel resolution={resolution} report={report} />);
  return resolution;
}

describe('DiffTooLarge marker (MT-4.7-04; Section 9.7)', () => {
  it('renders the verbatim Section 9.7 phrase — the mobile-shared constant', () => {
    render(<DiffTooLarge marker={DIFF_TOO_LARGE_MARKER} diffSummary={null} />);
    expect(screen.getByTestId('diff-too-large-marker').textContent).toBe('diff too large');
  });

  it('uses the server marker when provided and the constant as fallback', () => {
    const { unmount } = render(<DiffTooLarge marker="custom oversized" diffSummary={null} />);
    expect(screen.getByTestId('diff-too-large-marker').textContent).toBe('custom oversized');
    unmount();
    render(<DiffTooLarge marker={null} diffSummary={{ files: 2, insertions: 9, deletions: 1 }} />);
    expect(screen.getByTestId('diff-too-large-marker').textContent).toBe('diff too large');
    expect(screen.getByTestId('diff-too-large-stats').textContent).toBe('2 files · +9 · −1');
  });
});

describe('oversize payload through the panel (MT-4.7-04)', () => {
  it('renders marker + authoritative stats + the changed-file list', async () => {
    const resolution = harness(oversizePatchPayload(), {
      changed_files: ['a/one.py', 'b/two.py'],
      diff_summary: { files: 2, insertions: 40, deletions: 6 },
    });
    await waitFor(() => expect(screen.getByTestId('diff-panel-oversize')).toBeTruthy());
    expect(screen.getByTestId('diff-too-large-marker').textContent).toBe('diff too large');
    // Authoritative stats from the resolution row (Section 7.2), not invented.
    expect(screen.getByTestId('diff-too-large-stats').textContent).toBe('2 files · +40 · −6');
    // The file list stays usable (MT-4.7-03 plain-list contract).
    const tree = screen.getByTestId('file-tree-oversize');
    expect(within(tree).getByTestId('tree-entry-a/one.py')).toBeTruthy();
    expect(within(tree).getByTestId('tree-entry-b/two.py')).toBeTruthy();
    // No diff body was fabricated: no diff view, no line rows.
    expect(screen.queryByTestId('diff-view')).toBeNull();
    expect(document.querySelectorAll('[data-testid^="diff-line-"]').length).toBe(0);
    // The resolution identity is still on screen for the reviewer.
    expect(resolution.branch_name).toBe('feat/login');
  });

  it('a normal payload never shows the marker', async () => {
    harness(patchBodyPayload(SINGLE_FILE_PATCH), { changed_files: ['web/login.tsx'] });
    await waitFor(() => expect(screen.getByTestId('diff-panel-ready')).toBeTruthy());
    expect(screen.queryByTestId('diff-too-large')).toBeNull();
    expect(document.body.textContent).not.toContain('diff too large');
  });

  it('an empty diff is distinguishable from the oversize state', async () => {
    harness(patchBodyPayload(''), { changed_files: [] });
    await waitFor(() => expect(screen.getByTestId('diff-panel-empty')).toBeTruthy());
    expect(screen.queryByTestId('diff-too-large')).toBeNull();
    expect(screen.getByText('No changes in this patch')).toBeTruthy();
  });

  it('a decode anomaly (missing body field) renders the marker, not a broken viewer', async () => {
    // A payload the client cannot use as a body — the MT's client-side
    // guard: marker + stored list, never fabricated content.
    harness({ resolution_id: 'res-0002', kind: 'patch', sha256: '0'.repeat(64), size_bytes: 0 });
    await waitFor(() => expect(screen.getByTestId('diff-panel-oversize')).toBeTruthy());
    expect(screen.getByTestId('diff-too-large-marker').textContent).toBe('diff too large');
    expect(document.querySelectorAll('[data-testid^="diff-line-"]').length).toBe(0);
  });

  it('a catalog fetch error maps to catalog copy, not the marker', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/resolutions\/[^/]+\/patch(\?|$)/,
        respond: () => errorResponse('AUTH_FORBIDDEN_PROJECT', 403, 'not your project'),
      },
    ]);
    renderWithQueryClient(<DiffPanel resolution={makeResolution()} />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toContain("don't have access");
    expect(alert.textContent).not.toContain('not your project');
    expect(screen.queryByTestId('diff-too-large')).toBeNull();
  });

  it('rule flags ride the oversize state (MT-4.7-05 composition)', async () => {
    const report = {
      policy_rule_results: [ruleRow('R4', false, 'migration_detected', ['b/two.py'])],
    } as unknown as AuditReport;
    harness(oversizePatchPayload(), { changed_files: ['a/one.py', 'b/two.py'] }, report);
    await waitFor(() => expect(screen.getByTestId('diff-panel-oversize')).toBeTruthy());
    const tree = screen.getByTestId('file-tree-oversize');
    expect(within(tree).getByTestId('tree-flag-R4-b/two.py')).toBeTruthy();
    expect(within(tree).queryByTestId('tree-flag-R4-a/one.py')).toBeNull();
  });
});
