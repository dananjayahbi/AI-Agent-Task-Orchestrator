# MT-6.3-02 — Capture Performance Results Against the Latency Targets

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.3-02 |
| Title | Capture performance results against the latency targets |
| Parent WP | WP-6.3 — Performance and load tests (Milestone M6) |
| Requirements | NFR-02, NFR-03, NFR-09 |
| Priority | M |
| Dependencies | MT-6.3-01 (scenarios, seed and thresholds defined) |
| Parent sections | 5.2 (NFR-02, NFR-03, NFR-09), 16.1 (topology), 18 (Performance row), 19 (WP-6.3 second slice and acceptance), 20.4 (item 1), 20.5 |

## Context
Section 19 (WP-6.3) acceptance: "targets met with 20 simulated agents and 10,000
tasks", deliverables "load scenarios, results, tuning changes". This second slice
produces the **results**: run the MT-6.3-01 scenarios against the local
production-topology stack, capture every percentile, and judge it against the three
NFRs — NFR-02 claim/checkpoint p95 < 300 ms locally; NFR-03 event delivery p95 < 2 s
and push dispatch within 10 s; NFR-09 the scale envelope. Section 20.4 item 1 is the
discipline: acceptance demonstrably met by the named test command, with the numbers
recorded. Missed targets become inputs to MT-6.3-03, not silent passes.

## Inputs / Prerequisites
* MT-6.3-01 — runnable scenarios with thresholds and a reproducible seed.
* Local Compose stack in production topology (Section 16.1), freshly migrated,
  nothing else competing for the machine (measurement hygiene).
* Parent plan Section 5.2 — the exact NFR wording to judge against.
* MT-4.11-04's web board performance report (if landed) — cross-reference for the
  board-load story rather than duplicating browser-side numbers.
* FCM sender configured (MT-5.4-01) for whatever push-dispatch leg the scenario
  measures (see scope).

## Scope (in)
* Run every MT-6.3-01 scenario on the local stack and capture results:
  * Claim and checkpoint p50/p95/p99 under the 20-agent/10k-task load — verdict
    against NFR-02's 300 ms p95.
  * SSE fan-out publish-to-receipt percentiles — verdict against NFR-03's 2 s p95.
  * Push dispatch: backend-trigger-to-sender-dispatch timing against NFR-03's 10 s
    budget, with the method stated (and the device-delivery leg explicitly
    cross-referenced to WP-5.4/MT-5.10-05, not claimed here).
  * Scale observations against NFR-09's envelope (10 projects, 20 sessions, 10,000
    tasks) — the run shape itself; attachment-volume behavior noted from the
    scenario (see risk notes for the 50 GB item).
  * Board-load API results, cross-referenced with MT-4.11-04's browser numbers.
* Publish the performance report (`docs/plan/performance-report.md` — WP-6.3
  deliverable "results"): environment/hardware, versions, seed, per-scenario
  percentiles, pass/fail per NFR, and an explicit list of missed targets.
* Repeat each scenario enough to distinguish signal from noise (document the run
  count); record variance alongside percentiles.
* Classify every miss for MT-6.3-03 (suspected index, pooling, query, or config
  cause) so tuning has a bounded target list.
* Changelog note (Section 20.4 item 7).

## Out of scope
* Writing the scenarios — MT-6.3-01.
* Applying fixes — MT-6.3-03 (this task only classifies misses).
* Web/browser rendering numbers — MT-4.11-04 (WP-4.11).
* Real-device push delivery — WP-5.4 acceptance and MT-5.10-05.
* Achieving NFR-01 concurrency claims (duplicate-claim correctness) — owned by the
  M1 concurrency tests; this is latency/scale measurement.

## Target paths
* `docs/plan/performance-report.md` (WP-6.3 deliverable: results, verdicts, miss
  list)
* `e2e/` — result artifacts/outputs from the runs (if the suite persists them in
  tree; otherwise attach to the report)
* WP changelog entry (run counts, environment, headline numbers)

## Acceptance criteria
- [ ] All Section 18 Performance-row scenarios executed against the local
  production-topology stack with recorded percentiles (Section 20.4 item 1).
- [ ] A verdict recorded for NFR-02 (claim/checkpoint p95 < 300 ms), NFR-03 (event
  p95 < 2 s; push dispatch < 10 s with method stated) and NFR-09 (run shape = 10
  projects, 20 sessions, 10,000 tasks) (Section 5.2).
- [ ] The report states "targets met with 20 simulated agents and 10,000 tasks" or
  lists each miss with a classification for tuning — Section 19 WP-6.3 acceptance
  handled honestly.
- [ ] Environment, seed, versions and run counts recorded so the numbers reproduce
  (Section 20.4 item 1).
- [ ] The 50 GB attachment half of NFR-09 is either exercised or explicitly
  documented as a design-envelope item with its verification method stated (Section
  5.2; see risk notes).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Execute the MT-6.3-01 scenario suite per its documented entry points against local
Compose, then verify `docs/plan/performance-report.md` contains percentile tables
with a pass/fail per NFR and, where any target missed, a classified miss list ready
for MT-6.3-03.

## Attachments
* [NFR-02, NFR-03, NFR-09 — Latency and scalability requirements](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing strategy (Performance row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.3 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Local hardware variance moves p95 numbers — record the machine and what else ran
  on it; the plan says "locally" for NFR-02, so keep the same discipline as
  MT-1.10-06 (documented assumptions, no cross-machine claims).
* The 10 s push budget measured without a device only proves the backend→sender
  leg — label it precisely in the report; an unlabeled "push: pass" would
  over-claim NFR-03.
* NFR-09's 50 GB attachments cannot be practically seeded in a local run — stating
  a documented design-envelope verification (storage abstraction behavior, size-cap
  rules from RISK-13 mitigations) is the honest path; inventing a partial number
  (e.g. "tested with 2 GB, extrapolated") without labeling the method is not.
