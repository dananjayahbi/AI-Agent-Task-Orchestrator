'use client';

/**
 * Server-clock alignment (MT-4.9-02; Principle P7 — "the server clock is
 * authoritative; the display derives remaining time from server-issued
 * timestamps, never from client-supplied times").
 *
 * The panel has no server "now" endpoint — the available server signal is
 * a Section 9.6 envelope's `occurred_at`, stamped on the server when the
 * event fired. Anchoring = `occurred_at` minus the local receive time;
 * the most recent envelope re-anchors (the risk note's "re-anchor on each
 * update"). Between anchors the display ticks on the shared client timer,
 * shifted by the offset. Two recorded consequences:
 *
 *  - network latency biases the server slightly "behind" (the countdown
 *    can over-count by at most the one-way delay — never negative/wild);
 *  - before the first live envelope the offset is 0 (plain client tick
 *    against server-issued `lease_expires_at`); history envelopes are
 *    deliberately NOT used as anchors — their age would masquerade as
 *    clock skew.
 *
 * Subscribers (the countdown component) observe offset changes through
 * `useServerClockOffset`, so a fresh anchor repaints immediately instead
 * of waiting for the next tick.
 */
import { useSyncExternalStore } from 'react';

let offsetMs = 0;
const listeners = new Set<() => void>();

/** Anchor the offset to one server-stamped envelope (P7). */
export function noteServerTime(serverIso: string, clientMs: number = Date.now()): void {
  const parsed = Date.parse(serverIso);
  if (Number.isNaN(parsed)) {
    return; // never let a malformed stamp corrupt the anchor
  }
  const next = parsed - clientMs;
  if (next === offsetMs) {
    return;
  }
  offsetMs = next;
  for (const listener of listeners) {
    listener();
  }
}

/** Server view of "now" for a given client reading (P7-aligned). */
export function serverNowMs(clientMs: number = Date.now()): number {
  return clientMs + offsetMs;
}

/** Current anchor, in milliseconds (diagnostics/tests). */
export function serverClockOffsetMs(): number {
  return offsetMs;
}

/** Test isolation — back to "no anchors observed". */
export function resetServerClock(): void {
  if (offsetMs !== 0) {
    offsetMs = 0;
    for (const listener of listeners) {
      listener();
    }
  }
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Re-render on anchor changes (the tick supplies the seconds cadence). */
export function useServerClockOffset(): number {
  return useSyncExternalStore(subscribe, serverClockOffsetMs, () => 0);
}
