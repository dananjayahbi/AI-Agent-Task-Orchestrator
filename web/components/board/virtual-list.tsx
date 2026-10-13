'use client';

/**
 * Windowed list (MT-4.3-06; Section 13.4 "Board with 500 cards stays
 * responsive (virtualized columns)").
 *
 * Deliberately dependency-free (MT-4.3-06: "no new heavy dependency
 * without recording the choice"): a fixed-row-height window over an
 * absolutely positioned spacer. Only the visible slice plus a small
 * overscan is mounted, so live SSE patches (MT-4.3-05) re-render a bounded
 * node set no matter how large the column grows.
 *
 * Identity and reconciliation:
 *  - items are keyed by `itemKey` (task id on the board) — a live patch
 *    updates a card in place without remounting the column or resetting
 *    `scrollTop`;
 *  - keyboard navigation must not dead-end off-window cards (Section
 *    13.4): Arrow/Home/End move a roving focus target and scroll it into
 *    the window before focusing.
 *
 * Height model (documented v1 trade-off): rows are fixed-height
 * estimates; the container measures its own height when laid out and falls
 * back to a constant in unmeasured environments (SSR, jsdom). Variable row
 * heights are a WP-4.11 polish item, not a plan requirement.
 */
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
  type UIEvent,
} from 'react';

import { cn } from 'cn';

/** Fallback viewport when the container is unmeasured (SSR / jsdom). */
export const FALLBACK_VIEWPORT_HEIGHT = 480;
/** Fixed row height in px — must fit a TaskCard without clipping. */
export const CARD_ROW_HEIGHT = 132;

type VirtualListProps<T> = {
  items: readonly T[];
  /** Stable identity — scroll position and focus survive live patches. */
  itemKey: (item: T) => string;
  renderItem: (item: T, index: number) => ReactNode;
  itemHeight?: number;
  /** Explicit viewport height (tests, fixed layouts); else self-measured. */
  viewportHeight?: number;
  overscan?: number;
  label: string;
  testId?: string;
  className?: string;
};

export function VirtualList<T>({
  items,
  itemKey,
  renderItem,
  itemHeight = CARD_ROW_HEIGHT,
  viewportHeight,
  overscan = 3,
  label,
  testId,
  className,
}: VirtualListProps<T>) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [measuredHeight, setMeasuredHeight] = useState(0);
  const [focusedIndex, setFocusedIndex] = useState<number | null>(null);

  const resolvedHeight =
    viewportHeight ?? (measuredHeight > 0 ? measuredHeight : FALLBACK_VIEWPORT_HEIGHT);

  // Measure asynchronously (rAF) so no state write happens synchronously
  // in the effect body; resize keeps the window honest.
  useEffect(() => {
    const element = containerRef.current;
    if (element === null) return;
    const measure = () => setMeasuredHeight(element.clientHeight);
    const frame = requestAnimationFrame(measure);
    window.addEventListener('resize', measure);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('resize', measure);
    };
  }, []);

  const onScroll = useCallback((event: UIEvent<HTMLDivElement>) => {
    setScrollTop(event.currentTarget.scrollTop);
  }, []);

  const onKeyDown = useCallback(
    (event: KeyboardEvent<HTMLDivElement>) => {
      const count = items.length;
      if (count === 0) return;
      let next: number | null = null;
      if (event.key === 'ArrowDown') next = Math.min((focusedIndex ?? -1) + 1, count - 1);
      else if (event.key === 'ArrowUp') next = Math.max((focusedIndex ?? count) - 1, 0);
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = count - 1;
      if (next === null) return;
      event.preventDefault();
      setFocusedIndex(next);
      // Bring the target into the window before the focus effect runs.
      const container = containerRef.current;
      if (container !== null) {
        const top = next * itemHeight;
        const bottom = top + itemHeight;
        let targetScrollTop = container.scrollTop;
        if (top < targetScrollTop) targetScrollTop = top;
        else if (bottom > targetScrollTop + resolvedHeight) {
          targetScrollTop = bottom - resolvedHeight;
        }
        if (targetScrollTop !== container.scrollTop) {
          container.scrollTop = targetScrollTop;
          setScrollTop(targetScrollTop);
        }
      }
    },
    [focusedIndex, items.length, itemHeight, resolvedHeight],
  );

  // Roving focus: runs after the window has reconciled with the target
  // index, so off-screen cards are reachable (Section 13.4 keyboard rule).
  useEffect(() => {
    if (focusedIndex === null) return;
    const container = containerRef.current;
    if (container === null) return;
    const clamped = Math.min(focusedIndex, Math.max(items.length - 1, 0));
    container.querySelector<HTMLElement>(`[data-index="${clamped}"]`)?.focus();
  }, [focusedIndex, items.length]);

  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const endIndex = Math.min(
    items.length,
    Math.ceil((scrollTop + resolvedHeight) / itemHeight) + overscan,
  );
  const visible: Array<{ item: T; index: number }> = [];
  for (let index = startIndex; index < endIndex; index += 1) {
    const item = items[index];
    if (item !== undefined) visible.push({ item, index });
  }

  return (
    <div
      ref={containerRef}
      data-testid={testId}
      role="list"
      aria-label={label}
      className={cn('overflow-y-auto overscroll-contain', className)}
      style={{ height: resolvedHeight }}
      onScroll={onScroll}
      onKeyDown={onKeyDown}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setFocusedIndex(null);
        }
      }}
    >
      <div className="relative" style={{ height: items.length * itemHeight }}>
        {visible.map(({ item, index }) => (
          <div
            key={itemKey(item)}
            role="listitem"
            data-index={index}
            tabIndex={0}
            className="absolute inset-x-0 box-border pb-1.5 pr-1.5 outline-none focus-visible:ring-2 focus-visible:ring-ring"
            style={{ top: index * itemHeight, height: itemHeight }}
          >
            <div className="h-full">{renderItem(item, index)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
