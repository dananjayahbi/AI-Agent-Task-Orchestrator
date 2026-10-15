/**
 * Shared responsive layout recipes (MT-4.11-01; Section 13.4 phone-browser
 * fallback; Section 20.3 "one coherent change").
 *
 * Every core surface (board, task detail, review queue/panel, audit log,
 * settings, ops) reflows through these class recipes instead of one-off
 * per-page hacks. Each recipe is the exact class string a surface
 * already used (or a minimal, documented responsive addition) — desktop
 * visuals are unchanged; the recipes just make the phone behavior a
 * single, testable contract:
 *
 *  - wrapping rows (`flex-wrap`) so controls never leave the viewport;
 *  - bounded horizontal scroll regions (board columns) so the *page*
 *    never gains a horizontal scroll-trap;
 *  - `sm:`/`lg:` grid breakpoints so lists stack on phones and densify
 *    on desktop;
 *  - a dialog frame that insets from the viewport edges and caps its
 *    height, so confirmation dialogs stay operable on short screens.
 *
 * Tests pin these strings (`web/tests/layout/responsive-layouts.test.tsx`)
 * so a future refactor cannot silently drop a responsive rule.
 */
export const layout = {
  /** App chrome row (brand + switcher + nav + session): wraps at phone widths. */
  appHeader:
    'mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3',
  /** Cluster inside the chrome row (brand+switcher, session+theme). */
  chromeCluster: 'flex flex-wrap items-center gap-4',
  /** Primary nav row inside the header (already wrap-safe; shared for one rule set). */
  appNav: 'flex flex-wrap items-center gap-1',
  /** Standard page title + trailing-status row (board, review queue, …). */
  pageHeaderRow: 'flex flex-wrap items-center justify-between gap-3',
  /** One-column page stack used by every route body. */
  pageStack: 'flex flex-col gap-4',
  /** Board column strip: horizontal scroll + snap inside a bounded region. */
  boardColumns: 'flex snap-x gap-3 overflow-x-auto pb-2',
  /** Card grids: one column on phones, two from `sm`, three from `lg`. */
  cardGrid: 'grid gap-3 sm:grid-cols-2 lg:grid-cols-3',
  /** Ops metric list: one column on phones, two from `sm`, three from `lg`. */
  metricsGrid: 'mt-2 grid gap-x-6 gap-y-2 sm:grid-cols-2 lg:grid-cols-3',
  /** Diff tree + diff view: stacked on phones, two panes from `lg`. */
  diffPanes: 'grid gap-3 lg:grid-cols-[16rem_minmax(0,1fr)]',
  /**
   * Dialog frame: inset from viewport edges, capped to the viewport
   * height with internal scroll. `w-full max-w-lg` at desktop widths is
   * unchanged (the calc inset is smaller than the max there); on phones
   * the dialog keeps a 1rem gutter and scrolls instead of pushing its
   * actions off-screen.
   */
  dialogFrame:
    'fixed top-1/2 left-1/2 z-50 grid max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 overflow-y-auto rounded-lg border border-border bg-card p-6 shadow-lg',
} as const;
