/**
 * Responsive breakpoint tokens (MT-4.11-01; NFR-13, Section 13.4
 * "responsive layouts that remain usable on a phone browser as a
 * fallback review channel").
 *
 * One source of truth for the widths the layout recipes in
 * `lib/layout/styles.ts` encode through Tailwind's `sm:` (640px) and
 * `lg:` (1024px) variants:
 *
 *  - at or below `PHONE_MAX_WIDTH` every core flow (board, task detail,
 *    review decision, audit log, settings) must be operable: controls
 *    wrap, lists stack, the board scrolls its column region — never the
 *    page (RISK-09/RISK-11 phone-fallback channel);
 *  - `DESKTOP_MIN_WIDTH` and up get the two-pane layouts (diff tree
 *    beside diff view, denser metric grids).
 */

/** Tailwind `sm` minus 1 — the largest width treated as a phone browser. */
export const PHONE_MAX_WIDTH = 640;

/** Tailwind `lg` — where two-pane layouts engage. */
export const DESKTOP_MIN_WIDTH = 1024;

/**
 * Pure predicate for tests and any future JS-side layout decisions.
 * Components stay CSS-driven; this mirrors the recipe breakpoints so a
 * test can pin the boundary without a layout engine.
 */
export function isPhoneWidth(width: number): boolean {
  return width <= PHONE_MAX_WIDTH;
}
