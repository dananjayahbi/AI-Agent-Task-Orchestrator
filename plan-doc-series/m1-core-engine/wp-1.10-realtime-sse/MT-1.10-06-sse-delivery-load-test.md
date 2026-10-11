# MT-1.10-06 — Write the SSE Delivery Load Test (p95 Under 2 s Locally)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.10-06 |
| Title | Write the SSE delivery load test (p95 under 2 s locally) |
| Parent WP | WP-1.10 — Realtime gateway (SSE) (Milestone M1) |
| Requirements | NFR-03, FR-WEB-05 |
| Priority | M |
| Dependencies | MT-1.10-04 (heartbeat), MT-1.10-05 (authorization filtering) |
| Parent sections | 19.1 (WP-1.10), 18, 9.6, 20.4, 20.5 |

## Context
Section 19 (WP-1.10) acceptance: "p95 delivery under 2 s locally." NFR-03: real-time
event delivery to web/mobile p95 under 2 s. Section 20.4 item 1 requires acceptance
criteria to be demonstrably met by the named test command. This closing task
quantifies delivery latency from post-commit publish to receipt on a connected
client, under a realistic local connection count, and records the result.

## Inputs / Prerequisites
* All preceding MT-1.10-0x — endpoint, fan-out, resume, heartbeat, authorization.
* MT-1.9-03 — publish point where the latency clock starts.
* Local Compose stack (WP-0.2) running backend, Redis and database as in production
  topology (Section 16.1).
* Parent plan Section 18 — testing strategy layers (this is the WP-local load check,
  distinct from the full WP-6.3 suite).

## Scope (in)
* A load test that opens multiple concurrent SSE connections (with mixed
  `project`/`task` filters), triggers committed events, and measures per-event
  delivery latency from publish to client receipt.
* Assertion that p95 latency is under 2 s in the local environment (NFR-03).
* Coverage of at least one resume-during-load case: a reconnecting client catches up
  and continues within the same latency budget.
* Runnable result output (percentiles) persisted with the run so CI/review can read
  the measured p95, plus a pass/fail threshold.

## Out of scope
* The full performance program (scenarios, tuning, indexes, pooling) — WP-6.3.
* Tunnel-path latency — WP-5.1 verification (MT-5.1-04).
* Mobile push latency (10 s dispatch budget in NFR-03) — WP-5.4.
* Fixing performance regressions found here — raise them; the fix is a follow-up task.

## Target paths
* `backend/tests/perf/test_sse_delivery_load.py`
* WP changelog entry

## Acceptance criteria
- [ ] The test measures publish-to-receipt latency for concurrent filtered
  connections and asserts p95 < 2 s locally (Section 19 WP-1.10 acceptance,
  NFR-03).
- [ ] A resume-during-load scenario passes within the same budget.
- [ ] The measured percentile values are printed/persisted with the run, not only the
  boolean result.
- [ ] The test is deterministic enough to run in CI: fixed connection/event counts,
  documented thresholds (Section 20.4 item 1).
- [ ] Lint, type check and tests green (item 2); changelog note added (item 7).

## Test command
`pytest backend/tests/perf/test_sse_delivery_load.py -v` — prints p50/p95/p99 and
fails if p95 ≥ 2 s in the local Compose environment.

## Attachments
* [Section 19.1 — WP-1.10 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and quality strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [NFR-03 — Latency requirement](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Local-machine variance can flake a hard 2 s assertion — pick thresholds and
  connection counts that reflect the plan's "locally" wording; record hardware
  assumptions in the changelog note.
* Measuring "publish to receipt" requires a shared clock or server-side timestamps in
  the envelope (`occurred_at`); be explicit about which point starts the clock —
  publish time, not commit time — so the number matches the WP acceptance.
