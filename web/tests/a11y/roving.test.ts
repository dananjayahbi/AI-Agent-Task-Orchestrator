/**
 * MT-4.11-02 — shared roving-focus math (lib/a11y/roving.ts).
 *
 * Pure-function coverage for the keyboard index arithmetic the board's
 * VirtualList and the diff file tree share: Arrow/Home/End move focus,
 * clamped to the list; every other key returns null so the caller never
 * hijacks Tab, Enter or letter keys (Section 13.4; NFR-13).
 */
import { describe, expect, it } from 'vitest';

import { isRovingKey, nextRovingIndex, ROVING_KEYS } from '@/lib/a11y/roving';

describe('nextRovingIndex (MT-4.11-02)', () => {
  it('covers exactly the four roving keys', () => {
    expect([...ROVING_KEYS]).toEqual(['ArrowDown', 'ArrowUp', 'Home', 'End']);
    for (const key of ROVING_KEYS) expect(isRovingKey(key)).toBe(true);
    for (const key of ['Tab', 'Enter', ' ', 'a', 'Escape', 'PageDown']) {
      expect(isRovingKey(key)).toBe(false);
      expect(nextRovingIndex(key, 0, 10)).toBeNull();
    }
  });

  it('returns null for an empty list — the caller never steals the key', () => {
    for (const key of ROVING_KEYS) expect(nextRovingIndex(key, null, 0)).toBeNull();
    expect(nextRovingIndex('ArrowDown', 0, 0)).toBeNull();
  });

  it('ArrowDown walks forward and clamps at the last item', () => {
    expect(nextRovingIndex('ArrowDown', null, 5)).toBe(0); // unset → first
    expect(nextRovingIndex('ArrowDown', 0, 5)).toBe(1);
    expect(nextRovingIndex('ArrowDown', 3, 5)).toBe(4);
    expect(nextRovingIndex('ArrowDown', 4, 5)).toBe(4); // clamp, no wrap
  });

  it('ArrowUp walks backward and clamps at the first item', () => {
    expect(nextRovingIndex('ArrowUp', null, 5)).toBe(4); // unset → last
    expect(nextRovingIndex('ArrowUp', 4, 5)).toBe(3);
    expect(nextRovingIndex('ArrowUp', 1, 5)).toBe(0);
    expect(nextRovingIndex('ArrowUp', 0, 5)).toBe(0); // clamp, no wrap
  });

  it('Home and End jump to the edges regardless of direction', () => {
    expect(nextRovingIndex('Home', 4, 5)).toBe(0);
    expect(nextRovingIndex('Home', null, 5)).toBe(0);
    expect(nextRovingIndex('End', 0, 5)).toBe(4);
    expect(nextRovingIndex('End', null, 5)).toBe(4);
  });

  it('single-item lists always resolve to index 0', () => {
    expect(nextRovingIndex('ArrowDown', 0, 1)).toBe(0);
    expect(nextRovingIndex('ArrowUp', 0, 1)).toBe(0);
    expect(nextRovingIndex('Home', 0, 1)).toBe(0);
    expect(nextRovingIndex('End', 0, 1)).toBe(0);
  });
});
