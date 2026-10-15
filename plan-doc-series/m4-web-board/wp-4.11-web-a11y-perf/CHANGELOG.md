# WP-4.11 — Responsive, accessibility and performance pass: changelog

## Unreleased

- **MT-4.11-01 — responsive layouts incl. phone-browser fallback (done).**
  One coherent layout-rule change (Section 20.3): new `web/lib/layout/`
  module — `breakpoints.ts` (pure `isPhoneWidth` + the `PHONE_MAX_WIDTH`
  640 / `DESKTOP_MIN_WIDTH` 1024 tokens mirroring Tailwind `sm`/`lg`) and
  `styles.ts` (the shared `layout` recipe map: wrapping chrome/header
  rows, the bounded snap-scroll board column strip, 1→2→3-step card and
  metric grids, the stacked-below-`lg` diff panes, the page stack, and a
  phone-safe dialog frame — viewport inset `w-[calc(100%-2rem)]`,
  `max-h-[calc(100dvh-2rem)]` with internal scroll). Core surfaces now
  consume the recipes instead of one-off class strings: app chrome
  (`app/(app)/layout.tsx`, `app-nav.tsx` — header wraps at phone widths,
  so brand/switcher/nav/session controls all stay reachable), board
  (`board.tsx`), review queue header, project list, ops metrics grid,
  diff panel panes, and the shared dialog primitive (`ui/dialog.tsx`,
  affects move/approve/request-changes/task dialogs uniformly). Task
  detail, audit log, filters, forms and review actions already used
  wrap-safe idioms and were verified unchanged — no visual redesign;
  desktop layouts render identically (recipes are the previous class
  strings plus the documented responsive additions). Dark/light themes
  ride the MT-4.1-04 token set at every viewport; recipes are pinned to
  token-only classes (no hardcoded colors) by test. Simplifications on
  small screens: none — stacking/progressive disclosure only, no control
  is hidden (fallback review channel keeps approve/request-changes/
  reassign and the diff viewer reachable at phone width). Tests:
  `web/tests/layout/responsive-layouts.test.tsx` (11 — breakpoint
  boundaries; recipe contracts incl. bounded-scroll, grid steps, dialog
  inset/height-cap, theme-token-only; AppNav, Board at a 390px-stubbed
  phone viewport, ReviewPanel actions at phone viewport, dialog frame
  classes on the rendered move dialog). Suite: 401 green (390 baseline +
  11); `tsc --noEmit`, `eslint .`, `prettier --check .` clean. jsdom has
  no layout engine, so viewport tests pin the responsive class contract
  (the mechanism that produces the reflow) rather than computed
  geometry — noted as the test strategy, not a gap.

- **MT-4.11-02 — keyboard navigation for board and dialogs (done).**
  Section 13.4 / NFR-13 (WCAG 2.1 AA) keyboard operability hardening.
  New `web/lib/a11y/` module — `roving.ts` (one pure `nextRovingIndex`
  shared by the board VirtualList and the diff file tree, replacing two
  inline handlers with identical behavior). Global `:focus-visible`
  outline added to `globals.css` base layer so every interactive element
  without a component-level ring gets a visible focus indicator
  (buttons/inputs keep their utility-layer rings — base loses to
  utilities). `ui/dialog.tsx` now captures the active element at open
  and refocuses it on close: Radix only restores focus to a
  `DialogTrigger` ref, which none of our dialogs use (openers are
  external controls — card Move button, New task, review actions), so
  the MT's "focus returns to the trigger" criterion needed this shared
  fix; focus trapping and Escape-to-close behavior unchanged. Board
  keyboard moves already route through the same `routeMove` map as drag
  (MT-4.4-02 picker) — proven here with identical contract payloads and
  rejection copy, zero network. Tests: `web/tests/a11y/` (15 —
  `roving.test.ts` 6 pure math cases; `keyboard-navigation.test.tsx` 9
  component flows: keyboard board move parity + rejection, picker focus
  trap/restore on Escape, keyboard-only create task, keyboard-only
  approve/request-changes/reassign with T15 resolution binding and T16
  note guard intact, base-CSS and rendered-control focus-visible
  contracts). Suite: 416 green (401 + 15); `tsc --noEmit`, `eslint .`,
  `prettier --check .` clean.

- **MT-4.11-03 — contrast and label findings (done).** Audit report
  published at `docs/plan/accessibility-audit.md` (Appendix A keeps
  reports in `docs/plan/`); 10 findings, all fixed, none deferred.
  Contrast fixes are token-first (Section 13.4 — both themes move
  together): light `--ring` darkened (2.59:1 → 4.73:1 focus indicator,
  WCAG 1.4.11), light `--muted-foreground` (4.34:1 → 4.84:1 on muted
  surfaces), light `--destructive` (4.17:1 → 5.48:1 on the shared
  `/10` tint) and dark `--destructive-foreground` flipped to dark text
  (~2.65:1 → ~5.4:1 on the urgent chip — mirrors the dark `--primary`
  pattern). Component-level status tones bumped one shade where they
  sat on matching tints (emerald-600→700 Pass/Yes/exit-0/ops-OK,
  amber-600/700→800 alerts/stalled/paused, red-600→700 critical
  badge); the dark-side `*-400` tones were measured and kept. Removed
  `opacity-60` from the four disabled audit-filter controls. Label
  fix: the shared `FieldRow` now emits `{id}-error`/`{id}-hint` and
  merges them into the control's `aria-describedby` (every create/
  edit/policy/task form inherits), and the markdown editor associates
  its own error with the textarea. New `web/lib/a11y/` modules:
  `contrast.ts` (pure oklch→sRGB→WCAG luminance pipeline) and
  `theme-tokens.ts` (parses the shipped `globals.css`, so tests verify
  the values that ship). Tests: `web/tests/a11y/contrast-labels.test.tsx`
  (20 — token pairs in both themes incl. composited tints, status
  shade pins, label associations, audit-filter accessible names).
  Suite: 436 green (416 + 20); `tsc --noEmit`, `eslint .`,
  `prettier --check .` clean. Accepted limitations: none — no open
  critical contrast/label findings on core flows (Section 19).

- **MT-4.11-04 — 500-card board performance pass (done).** Section
  13.4 perf targets (500 cards render without jank; first load < 3 s on
  LAN) verified with the MT's scripted board-load check (no live
  Compose stack — backend agent shares the machine; the harness drives
  the finished Board with a 500-task fixture through the existing test
  API/SSE helpers). Windowing arithmetic extracted from
  `web/components/board/virtual-list.tsx` into pure
  `web/lib/board/windowing.ts` (`visibleWindow` + `scrollOffsetForIndex`,
  consumed by both the initial window and keyboard scroll-into-view) so
  the math is unit-testable — behavior-preserving, proven green by the
  pre-existing `virtual-columns`/`roving` tests unmodified. Measured
  (jsdom, 2 runs): cold mount 313.8–355.1 ms (budget 1000), 42 card
  nodes mounted out of 500 (window holds ≤ 10 rows/column), deep-scroll
  re-window 71.7–80.4 ms (budget 500), 25 serial SSE transition patches
  92.3–188.5 ms ≈ 3.69–7.54 ms/event (budget 500), search-filter
  keystroke 85.7 ms (budget 500). jsdom has no paint, so these are
  JS-execution bounds (a floor for real Chrome). First-load budget from
  a production `next build` (Next 16.4.0 Turbopack): board-route
  bootstrap 554.7 KB raw / 171.1 KB gz, worst-case all-routes ceiling
  1.05 MB raw / 351 KB gz across 27 chunks ⇒ modeled 0.6–1.8 s worst
  case on a conservative 100 Mbps LAN ⇒ passes < 3 s with ≥ 1.7×
  headroom. Full method + numbers in `docs/plan/web-performance-report.md`.
  Zero WP-4.11 regressions found in the pass. Tests:
  `web/tests/perf/board-load.test.tsx` (6 — mount budget + bounded DOM,
  deep-scroll windowing, 25-SSE-patch batch, filter budget, exhaustive
  windowing-math walk over all 500 row boundaries, extreme clamps).
  Suite: 442 green (436 + 6); `tsc --noEmit`, `eslint .`,
  `prettier --check .` clean.
