/**
 * MT-4.7-02 — unified/split diff views: both modes render from parsed
 * fixtures, the toggle persists (localStorage), highlighting applies
 * by extension with a plain fallback, large files collapse/expand,
 * the header stats are the backend's (never recomputed), and a
 * 5,000-line patch renders responsively (Wave 9 exit: bounded mounted
 * rows, render-shape objective per the MT risk note).
 */
import { fireEvent, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';

import { DiffView, DIFF_ROW_HEIGHT } from '@/components/diff/diff-view';
import { FALLBACK_VIEWPORT_HEIGHT } from '@/components/board/virtual-list';
import { parseUnifiedPatch } from '@/lib/diff/parse';
import type { FlaggedFiles } from '@/lib/diff/rule-flags';
import { NEW_FILE_PATCH, NO_NEWLINE_PATCH, SINGLE_FILE_PATCH, makeLargePatch } from './fixtures';

afterEach(() => {
  window.localStorage.clear();
});

const filesOf = (text: string) => parseUnifiedPatch(text).files;

function renderView(text: string, props: Partial<React.ComponentProps<typeof DiffView>> = {}) {
  const files = filesOf(text);
  render(
    <DiffView
      files={files}
      diffSummary={{ files: files.length, insertions: 12, deletions: 3 }}
      {...props}
    />,
  );
  return files;
}

describe('DiffView modes (MT-4.7-02)', () => {
  it('renders the unified view by default with both-side line numbers', () => {
    renderView(SINGLE_FILE_PATCH);
    expect(screen.getByTestId('diff-mode-unified').getAttribute('aria-pressed')).toBe('true');
    const lines = screen.getAllByTestId('diff-line-unified');
    expect(lines.length).toBeGreaterThan(0);
    expect(lines.some((line) => line.getAttribute('data-line-kind') === 'add')).toBe(true);
    expect(lines.some((line) => line.getAttribute('data-line-kind') === 'del')).toBe(true);
    // Unified rows carry the sign and the content.
    expect(document.body.textContent).toContain('return <form onSubmit={handleSubmit} />;');
  });

  it('toggles to split view and pairs deletions with additions', () => {
    renderView(SINGLE_FILE_PATCH);
    fireEvent.click(screen.getByTestId('diff-mode-split'));
    expect(screen.getByTestId('diff-mode-split').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getAllByTestId('diff-line-left').length).toBeGreaterThan(0);
    expect(screen.getAllByTestId('diff-line-right').length).toBeGreaterThan(0);
    // The del/add pair shares one row: −12 deletions appear on the left only.
    const leftKinds = screen
      .getAllByTestId('diff-line-left')
      .map((l) => l.getAttribute('data-line-kind'));
    const rightKinds = screen
      .getAllByTestId('diff-line-right')
      .map((l) => l.getAttribute('data-line-kind'));
    expect(leftKinds).toContain('del');
    expect(rightKinds).toContain('add');
    expect(rightKinds).not.toContain('del');
  });

  it('persists the toggle across remounts (localStorage)', () => {
    const { unmount } = render(<DiffView files={filesOf(SINGLE_FILE_PATCH)} diffSummary={null} />);
    fireEvent.click(screen.getByTestId('diff-mode-split'));
    expect(window.localStorage.getItem('diff-viewer:mode')).toBe('split');
    unmount();
    render(<DiffView files={filesOf(SINGLE_FILE_PATCH)} diffSummary={null} />);
    expect(screen.getByTestId('diff-mode-split').getAttribute('aria-pressed')).toBe('true');
  });
});

describe('DiffView highlighting (MT-4.7-02)', () => {
  it('applies token spans for a known extension', () => {
    renderView(NEW_FILE_PATCH); // .py
    const added = screen
      .getAllByTestId('diff-line-unified')
      .find((line) => line.getAttribute('data-line-kind') === 'add');
    // `def` is a Python keyword — tokenized, not plain.
    expect(added?.querySelector('span.font-semibold')).not.toBeNull();
    expect(added?.textContent).toContain('def helper():');
  });

  it('falls back to plain text for unknown extensions without errors', () => {
    const text = SINGLE_FILE_PATCH.replace(/web\/login\.tsx/g, 'data/thing.zzz');
    renderView(text);
    const lines = screen.getAllByTestId('diff-line-unified');
    expect(lines.length).toBeGreaterThan(0);
    // No keyword spans for an unmapped grammar — plain content only.
    expect(document.body.textContent).toContain('return <form onSubmit={handleSubmit} />;');
  });

  it('surfaces the no-newline marker on the affected line', () => {
    renderView(NO_NEWLINE_PATCH);
    expect(document.body.textContent).toContain('No newline at end of file');
  });
});

describe('DiffView collapse (MT-4.7-02)', () => {
  it('collapses a large file to its header and expands on demand', () => {
    renderView(makeLargePatch(500)); // > LARGE_FILE_LINES (200)
    // Header row visible; body hidden behind the affordance.
    expect(screen.getByTestId('diff-file-header').getAttribute('data-path')).toBe(
      'generated/big.ts',
    );
    expect(screen.getByTestId('diff-file-collapsed-generated/big.ts')).toBeTruthy();
    expect(screen.queryAllByTestId('diff-hunk-header')).toHaveLength(0);

    fireEvent.click(screen.getByTestId('diff-file-toggle-generated/big.ts'));
    expect(screen.queryByTestId('diff-file-collapsed-generated/big.ts')).toBeNull();
    expect(screen.getAllByTestId('diff-hunk-header').length).toBeGreaterThan(0);
  });

  it('a small file starts expanded and its header toggles collapse', () => {
    renderView(SINGLE_FILE_PATCH);
    expect(screen.queryByTestId('diff-file-collapsed-web/login.tsx')).toBeNull();
    fireEvent.click(screen.getByTestId('diff-file-toggle-web/login.tsx'));
    expect(screen.getByTestId('diff-file-collapsed-web/login.tsx')).toBeTruthy();
  });
});

describe('DiffView header stats (Section 9.7 authority)', () => {
  it('shows the backend diff_summary verbatim — labeled backend-computed', () => {
    render(
      <DiffView
        files={filesOf(SINGLE_FILE_PATCH)}
        diffSummary={{ files: 3, insertions: 120, deletions: 4 }}
      />,
    );
    const stats = screen.getByTestId('diff-view-stats');
    expect(stats.getAttribute('data-files')).toBe('3');
    expect(stats.textContent).toBe('3 files · +120 · −4 (backend-computed)');
  });

  it('renders no stats block for an unreadable summary shape (never invented)', () => {
    render(<DiffView files={filesOf(SINGLE_FILE_PATCH)} diffSummary={{ bogus: true }} />);
    expect(screen.queryByTestId('diff-view-stats')).toBeNull();
  });
});

describe('DiffView rule flags (MT-4.7-05 composition)', () => {
  it('marks a flagged file section with its rule ids', () => {
    const flags: FlaggedFiles = new Map([['web/login.tsx', ['R2' as const, 'R4' as const]]]);
    renderView(SINGLE_FILE_PATCH, { flags });
    expect(screen.getByTestId('diff-file-flag-R2')).toBeTruthy();
    expect(screen.getByTestId('diff-file-flag-R4')).toBeTruthy();
  });
});

describe('5,000-line responsiveness (Wave 9 exit)', () => {
  it('renders a 5,000-line patch with a bounded DOM (windowed rows)', () => {
    // 5,000 lines > collapse threshold, so the initial state is the
    // collapsed header — then expand to prove the window bounds the
    // mounted rows rather than the data set.
    renderView(makeLargePatch(5000));
    fireEvent.click(screen.getByTestId('diff-file-toggle-generated/big.ts'));
    const mountedLines = document.querySelectorAll('[data-testid^="diff-line-"]').length;
    const viewportRows = Math.ceil(FALLBACK_VIEWPORT_HEIGHT / DIFF_ROW_HEIGHT);
    // jsdom measures 0 height → fallback window + overscan; far below 5,000.
    expect(mountedLines).toBeGreaterThan(0);
    expect(mountedLines).toBeLessThan(viewportRows + 10);
    // The full data set is still represented (the list container exists).
    expect(screen.getByTestId('diff-lines')).toBeTruthy();
  });
});
