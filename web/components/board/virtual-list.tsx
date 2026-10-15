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
  useImperativeHandle,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
  type Ref,
  type UIEvent,
} from 'react';

import { nextRovingIndex } from '@/lib/a11y/roving';
import { scrollOffsetForIndex, visibleWindow } from '@/lib/board/windowing';
import { cn } from 'cn';

/** Fallback viewport when the container is unmeasured (SSR / jsdom). */
export const FALLBACK_VIEWPORT_HEIGHT = 480;
/** Fixed row height in px — must fit a TaskCard without clipping. */
export const CARD_ROW_HEIGHT = 132;

/** Imperative scroll API (MT-4.7-03 jump-to-file; optional, board-agnostic). */
export type VirtualListHandle = {
  scrollToIndex: (index: number) => void;
};

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
  /** Optional imperative scroll (diff jump-to-file); the board passes none. */
  ref?: Ref<VirtualListHandle>;
  /**
   * Fires when the mounted window's start row changes (scroll →
   * active-row sync). Naturally throttled: one call per row boundary
   * crossed, never per scroll pixel.
   */
  onVisibleRangeChange?: (startIndex: number, endIndex: number) => void;
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
  ref,
  onVisibleRangeChange,
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
      // MT-4.11-02: shared roving math (lib/a11y/roving) — Arrow/Home/End
      // only; every other key (Tab, Enter, …) passes through untouched.
      const next = nextRovingIndex(event.key, focusedIndex, items.length);
      if (next === null) return;
      event.preventDefault();
      setFocusedIndex(next);
      // Bring the target into the window before the focus effect runs
      // (MT-4.11-04: shared clamp math in lib/board/windowing).
      const container = containerRef.current;
      if (container !== null) {
        const targetScrollTop = scrollOffsetForIndex(
          next,
          itemHeight,
          resolvedHeight,
          items.length,
          container.scrollTop,
        );
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

  // MT-4.11-04: window bounds come from the pure helper in
  // lib/board/windowing — the tested math and the rendered window are
  // the same code path.
  const { startIndex, endIndex } = visibleWindow(
    scrollTop,
    itemHeight,
    resolvedHeight,
    items.length,
    overscan,
  );

  // Imperative scroll (MT-4.7-03 jump-to-file): clamp, align the
  // target row to the top, and keep the window state in sync so the
  // target mounts before any follow-up focus work.
  useImperativeHandle(
    ref,
    () => ({
      scrollToIndex: (index: number) => {
        const container = containerRef.current;
        if (container === null) return;
        const clamped = Math.min(Math.max(index, 0), Math.max(items.length - 1, 0));
        const target = clamped * itemHeight;
        container.scrollTop = target;
        setScrollTop(target);
      },
    }),
    [itemHeight, items.length],
  );

  // Scroll → caller notification (active-row sync), once per window change.
  const notifyRef = useRef(onVisibleRangeChange);
  useEffect(() => {
    notifyRef.current = onVisibleRangeChange;
  }, [onVisibleRangeChange]);
  const lastRangeRef = useRef('');
  useEffect(() => {
    const key = `${startIndex}:${endIndex}`;
    if (key === lastRangeRef.current) return;
    lastRangeRef.current = key;
    notifyRef.current?.(startIndex, endIndex);
  }, [startIndex, endIndex]);

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
