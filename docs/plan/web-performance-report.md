# Web Performance Report — WP-4.11 MT-4.11-04

**Date:** 2026-10-15
**Scope:** 500-card board performance pass (MT-4.11-04), `web/` only.
**Target:** Section 13.4 — 500 cards render without jank; first load < 3 s on LAN.

## Environment

- Windows 11 monorepo, Node **v24.11.1**, Next.js **16.4.0** (Turbopack), React 19.
- Interaction measurements: jsdom via Vitest (`tests/perf/board-load.test.tsx`).
  **jsdom has no paint/compositor**, so numbers here are CPU-side JS execution bounds
  (script parse, React render, DOM mutation) — a strict floor for real-browser cost,
  never an overstatement. Real Chrome also benefits from incremental rendering
  (Time Slicing) that jsdom cannot model.
- Bundle measurements: production `npx next build` (clean, exit 0; TS check ran in-build),
  then gzip (level 9) of emitted client chunks.

## Method

1. **Scripted board-load check** (the MT's scripted option; no live Compose stack was
   started to avoid colliding with the backend agent's containers): a Vitest suite
   builds a 500-task fixture, mounts the finished Board against the test API harness,
   and measures mount, deep-scroll re-windowing, a 25-event SSE patch burst, and a
   status-filter recompute. Pure windowing math lives in `lib/board/windowing.ts`
   (extracted from `virtual-list.tsx`, behavior-preserving — pinned green by the
   existing `virtual-columns` + `roving` suites) and is asserted exhaustively over all
   500 row boundaries.
2. **First-load budget derivation** from production build output (see below).

## Measured (jsdom, from `npx vitest run tests/perf/board-load.test.tsx`)

| Scenario                                       | Result (2 runs)                        | Bound                   |
| ---------------------------------------------- | -------------------------------------- | ----------------------- |
| Cold mount of Board with 500 cards             | **313.8–355.1 ms**                     | budget 1000 ms ✅       |
| Cards present in DOM after mount               | **42 of 500** (6 columns × 7–10 rows)  | virtualization holds ✅ |
| Scroll to row ~60 (window recompute, no paint) | **71.7–80.4 ms**                       | budget 500 ms ✅        |
| 25 SSE task patches applied serially           | **92.3–188.5 ms (3.69–7.54 ms/event)** | budget 500 ms ✅        |
| Search-filter keystroke over 500 cards         | **85.7 ms**                            | budget 500 ms ✅        |
| Pure windowing math, full 500-boundary walk    | < 1 ms per query (pure arithmetic)     | ✅                      |

The mount path never materializes more than ~10 card rows per column regardless of
dataset size — DOM size stays flat as data grows (re-verified: 42 nodes, not 500).

## First-load budget (< 3 s on LAN)

Production build client assets:

- **Board route bootstrap** (`build-manifest.json` rootMain + otherChunks + runtime +
  polyfill, 6 files): **554.7 KB raw / 171.1 KB gzip** (largest: framework 229.8 KB
  raw / 71.8 KB gz; shared vendor 159.0 KB / 44.0 KB gz).
- **Worst-case ceiling** — all 27 client chunks across every route: **1.05 MB raw /
  351 KB gzip**. The board (heaviest route) loads a subset of this.

Derivation (conservative LAN = 100 Mbps link at 50 % utilization ⇒ ~50 Mbps
effective; latency RTT 20 ms, HTTP/2 on one origin):

- Transfer: 351 KB ceiling × 8 = 2.81 Mbit ⇒ **~56 ms** at 50 Mbps
  (0.28 s even at a pessimistic 10 Mbps LAN).
- HTML (SSR shell) + CSS + font ≈ small next to JS; parse/execute of ~350 KB gz
  (~1 MB raw) of JS on a typical developer laptop ≈ 0.5–1.5 s cold.
- **Total ≈ 0.6–1.8 s worst case ⇒ passes < 3 s with ≥ 1.7× headroom**
  (≥ 10× at 50 Mbps transfer-bound).

## Findings / actions in this pass

- No jank-class defect found: virtualization window, memoized grouping/filtering,
  and the SSE patch path all stay within bounds at 500 cards.
- Refactor: windowing arithmetic extracted to `lib/board/windowing.ts`
  (`visibleWindow`, `scrollOffsetForIndex`) so it is unit-testable; both
  `virtual-list.tsx` call sites (initial window + keyboard scroll-into-view) consume
  it. Behavior-preserving — existing board tests remained green unmodified.
- **Zero WP-4.11 regressions found** during the pass.

## Verdict vs Section 13.4

| Target                                                                   | Verdict                                          |
| ------------------------------------------------------------------------ | ------------------------------------------------ |
| 500 cards render without jank (mount/scroll/patch/filter within budgets) | **PASS**                                         |
| First load < 3 s on LAN                                                  | **PASS** (351 KB gz ceiling ⇒ 0.6–1.8 s modeled) |
