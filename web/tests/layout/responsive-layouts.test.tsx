/**
 * MT-4.11-01 — responsive layouts incl. phone-browser fallback
 * (Section 13.4; NFR-13; RISK-09/RISK-11).
 *
 * jsdom has no layout engine, so these tests pin the *responsive
 contract* instead of computed geometry:
 *
 *  1. the shared breakpoint helpers (`isPhoneWidth`) at their boundaries;
 *  2. every shared recipe in `lib/layout/styles.ts` carries the rule it
 *     exists for (wrapping rows, bounded horizontal scroll, `sm:`/`lg:`
 *     grid steps, the phone-safe dialog frame, theme-token-only colors);
 *  3. the core surfaces consume those recipes — the board's column strip
 *     is a bounded scroll region, the header wraps, the dialog frame
 *     insets from the viewport, review actions render and stay operable
 *     at a phone-width viewport (the RISK-09/RISK-11 fallback channel).
 */
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import { AppNav } from '@/components/layout/app-nav';
import { ReviewPanel } from '@/components/review/review-panel';
import {
  installApi,
  installBoardApi,
  jsonResponse,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
} from '../helpers/api';

import { DESKTOP_MIN_WIDTH, isPhoneWidth, PHONE_MAX_WIDTH } from '@/lib/layout/breakpoints';
import { layout } from '@/lib/layout/styles';

vi.mock('next/navigation', () => ({
  usePathname: () => '/review',
}));

afterEach(() => {
  vi.unstubAllGlobals();
});

/** Simulate a phone browser viewport (Section 13.4 fallback channel). */
function assumePhoneViewport() {
  vi.stubGlobal('innerWidth', 390);
  window.dispatchEvent(new Event('resize'));
}

describe('Breakpoint helpers (MT-4.11-01)', () => {
  it('treats everything at or below the sm boundary as a phone browser', () => {
    expect(isPhoneWidth(0)).toBe(true);
    expect(isPhoneWidth(390)).toBe(true);
    expect(isPhoneWidth(PHONE_MAX_WIDTH)).toBe(true);
    expect(isPhoneWidth(PHONE_MAX_WIDTH + 1)).toBe(false);
    expect(isPhoneWidth(DESKTOP_MIN_WIDTH)).toBe(false);
    expect(PHONE_MAX_WIDTH).toBeLessThan(DESKTOP_MIN_WIDTH);
  });
});

describe('Shared layout recipes (MT-4.11-01)', () => {
  it('chrome and page header rows wrap instead of overflowing on phones', () => {
    for (const recipe of [
      layout.appHeader,
      layout.appNav,
      layout.chromeCluster,
      layout.pageHeaderRow,
    ]) {
      expect(recipe).toContain('flex-wrap');
    }
  });

  it('the board column strip is a bounded snap-scroll region, never a page-level trap', () => {
    expect(layout.boardColumns).toContain('overflow-x-auto');
    expect(layout.boardColumns).toContain('snap-x');
    // The recipe is applied to the strip only — no page body scrolls sideways.
    expect(layout.pageStack).not.toContain('overflow-x');
  });

  it('card and metric grids step 1 → 2 → 3 columns through sm/lg', () => {
    for (const recipe of [layout.cardGrid, layout.metricsGrid]) {
      expect(recipe).toContain('sm:grid-cols-2');
      expect(recipe).toContain('lg:grid-cols-3');
      // Phones get the single-column stack — no fixed desktop grid.
      expect(recipe).not.toMatch(/(^|\s)grid-cols-[23]/);
    }
  });

  it('the diff panes stack on phones and split from lg', () => {
    expect(layout.diffPanes).toContain('lg:grid-cols-[');
    expect(layout.diffPanes).not.toMatch(/(^|\s)grid-cols-\[[^\]]*\]/);
  });

  it('the dialog frame insets from the viewport and caps its height', () => {
    expect(layout.dialogFrame).toContain('w-[calc(100%-2rem)]');
    expect(layout.dialogFrame).toContain('max-h-[calc(100dvh-2rem)]');
    expect(layout.dialogFrame).toContain('overflow-y-auto');
  });

  it('recipes use theme-token classes only, so dark and light both render (Section 13.4)', () => {
    // No hardcoded colors may sneak into the shared rules — the MT-4.1-04
    // token set must keep driving both themes at every viewport.
    const all = Object.values(layout).join(' ');
    expect(all).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(all).not.toMatch(/\b(?:bg|text|border)-(?:black|white|red|blue|green|gray)\b/);
    expect(all).not.toContain('rgb(');
  });
});

describe('Core surfaces consume the shared rules (MT-4.11-01)', () => {
  it('app navigation renders through the shared wrapping recipe', () => {
    const { container } = renderWithQueryClient(<AppNav />);
    const nav = container.querySelector('nav[aria-label="Primary"]');
    expect(nav).not.toBeNull();
    expect(nav?.className).toContain('flex-wrap');
  });

  it('the board column strip uses the bounded scroll recipe at a phone viewport', async () => {
    assumePhoneViewport();
    const sse = sseConnection();
    installBoardApi({
      tasks: [
        makeTask({ id: 'PID00001-T001', state: 'draft' }),
        makeTask({ id: 'PID00001-T005', state: 'in_human_review' }),
      ],
      sse: () => sse.response,
    });

    const { container } = renderWithQueryClient(<Board pid="PID00001" />);
    await waitFor(() => expect(screen.getByTestId('board-column-draft')).toBeTruthy());

    const strip = container.querySelector('[data-testid="board-columns"]');
    expect(strip).not.toBeNull();
    expect(strip?.className).toContain('overflow-x-auto');
    expect(strip?.className).toContain('snap-x');
    // Core-flow controls stay rendered at phone width — nothing is hidden
    // behind a viewport condition (Section 13.4: stacking over removal).
    expect(screen.getByTestId('board-new-task')).toBeTruthy();
    expect(screen.getByTestId('board-column-in_human_review')).toBeTruthy();
  });

  it('review actions render and remain operable at a phone viewport (fallback channel)', async () => {
    assumePhoneViewport();
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/resolutions(\?|$)/,
        respond: () => jsonResponse(pageOf([])),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/audit-reports(\?|$)/,
        respond: () => jsonResponse(pageOf([])),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/attachments(\?|$)/,
        respond: () => jsonResponse(pageOf([])),
      },
    ]);

    renderWithQueryClient(
      <ReviewPanel
        pid="PID00001"
        taskId="PID00001-T005"
        task={makeTask({ state: 'in_human_review', review_reason: 'test_failure' })}
        streamStatus="open"
      />,
    );

    await waitFor(() => expect(screen.getByTestId('review-panel-actions')).toBeTruthy());
    // The three Section 13.2 decisions are present (not viewport-hidden) and
    // the action row wraps rather than pushing buttons off-screen.
    expect(screen.getByTestId('review-approve-open')).toBeTruthy();
    expect(screen.getByTestId('review-request-changes-open')).toBeTruthy();
    expect(screen.getByTestId('review-reassign-open')).toBeTruthy();
    const actionRow = screen.getByTestId('review-panel-actions').querySelector('.flex');
    expect(actionRow?.className).toContain('flex-wrap');
  });

  it('dialogs use the shared phone-safe frame (inset + height cap)', async () => {
    assumePhoneViewport();
    const sse = sseConnection();
    installBoardApi({
      tasks: [makeTask({ id: 'PID00001-T005', state: 'in_human_review' })],
      sse: () => sse.response,
    });

    renderWithQueryClient(<Board pid="PID00001" />);
    const moveButton = await screen.findByTestId('task-card-move');
    fireEvent.click(moveButton);

    const dialog = await screen.findByTestId('move-destination-dialog');
    expect(dialog.className).toContain('w-[calc(100%-2rem)]');
    expect(dialog.className).toContain('max-h-[calc(100dvh-2rem)]');
    expect(dialog.className).toContain('overflow-y-auto');
  });
});
