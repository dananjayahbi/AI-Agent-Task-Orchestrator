/**
 * Roving-focus keyboard math (MT-4.11-02; Section 13.4 "keyboard
 * navigation for the board and dialogs"; NFR-13 / WCAG 2.1 AA).
 *
 * One pure function shared by every roving list in the app — the board's
 * windowed columns (VirtualList) and the diff viewer's file tree both
 * answer the same question: given the key, the current focus index and
 * the item count, which index receives focus next?
 *
 * Convention: `from` is the index to move *from*; pass `null` when
 * nothing is focused yet. From the unset state ArrowDown lands on the
 * first item and ArrowUp lands on the last item — the board
 * VirtualList convention; the diff file tree resolves its own active
 * index and passes `null` only when no row is focused.
 *
 * Keys outside the roving set (Tab, Enter, letters…) return `null` so
 * the caller never hijacks them. `count === 0` also returns `null`.
 */
export const ROVING_KEYS = ['ArrowDown', 'ArrowUp', 'Home', 'End'] as const;

export type RovingKey = (typeof ROVING_KEYS)[number];

export function isRovingKey(key: string): key is RovingKey {
  return (ROVING_KEYS as readonly string[]).includes(key);
}

/**
 * Next focus index for a roving keypress, or `null` when the key is not
 * a roving key or the list is empty.
 */
export function nextRovingIndex(key: string, from: number | null, count: number): number | null {
  if (count === 0 || !isRovingKey(key)) return null;
  if (key === 'Home') return 0;
  if (key === 'End') return count - 1;
  if (key === 'ArrowDown') return Math.min((from ?? -1) + 1, count - 1);
  return Math.max((from ?? count) - 1, 0);
}
