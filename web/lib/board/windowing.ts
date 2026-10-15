/**
 * Virtual-list windowing math (MT-4.3-06 mechanism, extracted for the
 * MT-4.11-04 performance pass; Section 13.4 "Board with 500 cards stays
 * responsive (virtualized columns)").
 *
 * One pure function decides which rows are mounted for a given scroll
 * offset: the visible slice plus a small overscan, clamped to the item
 * range. No DOM, no state — the board's repeatable load check pins the
 * bounded-mount guarantee here, and `VirtualList` consumes it so the
 * tested math and the rendered window can never drift.
 */

export type WindowRange = {
  /** First mounted row index (inclusive), clamped to `[0, count]`. */
  startIndex: number;
  /** End row index (exclusive), clamped to `startIndex` and `count`. */
  endIndex: number;
};

/**
 * Rows to mount for `scrollTop` over a fixed-row-height list.
 *
 * @param scrollTop current scroll offset in px (negative values clamp to 0)
 * @param itemHeight fixed row height in px (> 0)
 * @param viewportHeight visible height in px (<= 0 falls back to one row)
 * @param count total item count
 * @param overscan extra rows mounted above/below the viewport
 */
export function visibleWindow(
  scrollTop: number,
  itemHeight: number,
  viewportHeight: number,
  count: number,
  overscan: number,
): WindowRange {
  if (count <= 0) return { startIndex: 0, endIndex: 0 };
  const top = Math.max(0, scrollTop);
  const height = viewportHeight > 0 ? viewportHeight : itemHeight;
  const first = Math.floor(top / itemHeight) - overscan;
  const end = Math.ceil((top + height) / itemHeight) + overscan;
  const startIndex = Math.min(Math.max(0, first), count);
  const endIndex = Math.min(Math.max(startIndex, end), count);
  return { startIndex, endIndex };
}

/**
 * Scroll offset that brings row `index` fully into view, aligned to the
 * top when scrolling down and to the bottom edge when scrolling up
 * (keyboard roving — MT-4.11-02 shares the same clamp rules).
 */
export function scrollOffsetForIndex(
  index: number,
  itemHeight: number,
  viewportHeight: number,
  count: number,
  currentScrollTop: number,
): number {
  if (count <= 0) return 0;
  const clamped = Math.min(Math.max(index, 0), count - 1);
  const top = clamped * itemHeight;
  const bottom = top + itemHeight;
  const height = viewportHeight > 0 ? viewportHeight : itemHeight;
  if (top < currentScrollTop) return top;
  if (bottom > currentScrollTop + height) return bottom - height;
  return currentScrollTop;
}
