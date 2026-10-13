'use client';

/**
 * Shared client clock (MT-4.3-02 risk note: "drive ticking from a shared
 * timer … so re-renders stay bounded").
 *
 * One module-level interval serves every subscriber — the lease countdown
 * and the stalled marker across a 500-card board tick from one timer, not
 * one `setInterval` per card. The interval starts with the first
 * subscriber and stops with the last, so an unmounted board leaves no
 * timers behind.
 */
import { useEffect, useReducer } from 'react';

type Listener = () => void;

const listeners = new Set<Listener>();
let timer: ReturnType<typeof setInterval> | null = null;
let currentNowMs: number = Date.now();

function tick() {
  currentNowMs = Date.now();
  for (const listener of listeners) {
    listener();
  }
}

/** The latest clock reading (server-authoritative deadlines, client display only). */
export function useNow(intervalMs = 1000): number {
  const [, forceRender] = useReducer((count: number) => count + 1, 0);

  useEffect(() => {
    const listener = () => forceRender();
    listeners.add(listener);
    if (timer === null) {
      currentNowMs = Date.now();
      timer = setInterval(tick, intervalMs);
    }
    return () => {
      listeners.delete(listener);
      if (listeners.size === 0 && timer !== null) {
        clearInterval(timer);
        timer = null;
      }
    };
  }, [intervalMs]);

  return currentNowMs;
}
