# MT-6.3-03 — Apply Tuning Changes (Indexes, Pooling) for Any Missed Targets

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.3-03 |
| Title | Apply tuning changes (indexes, pooling) for any missed targets |
| Parent WP | WP-6.3 — Performance and load tests (Milestone M6) |
| Requirements | NFR-02, NFR-03, NFR-09 |
| Priority | M |
| Dependencies | MT-6.3-01 (scenarios), MT-6.3-02 (results and classified miss list) |
| Parent sections | 5.2 (NFR-02, NFR-03, NFR-09), 16.1 (Compose services), 18 (Performance row), 19 (WP-6.3 deliverable: tuning changes; acceptance), 20.3 (split rules), 20.4 (items 1, 2, 4), 20.5 |

## Context
Section 19 (WP-6.3) deliverables list "tuning changes (indexes, pooling)" — the
remediation half of the performance program. The acceptance bar is the same as
MT-6.3-02's: "targets met with 20 simulated agents and 10,000 tasks." If the capture
run already met every target, this task is a verification and a "no tuning required"
record — the slice still closes explicitly rather than disappearing. If targets
missed, this task applies the bounded fixes the plan names (indexes, pooling),
re-runs the scenarios, and repeats until the verdict is green or the miss needs
beyond-plan work (which becomes a risk escalation, not a silent gap).

## Inputs / Prerequisites
* MT-6.3-02 — performance report with percentile tables, verdicts and the
  classified miss list (the input this task consumes; empty list ⇒ no-op path).
* MT-6.3-01 — scenarios to re-run for before/after evidence.
* Parent plan Section 5.2 — the targets to re-judge against.
* Backend structure: Django models/queries (WP-1.x), Celery worker (WP-1.7),
  connection handling in the Section 16.1 services — tuning touches these seams.
* Section 20.4 item 4 — schema changes require the schema-diff check; a new index
  is a migration and gets the migration discipline (Section 20.3: never combined
  with unrelated logic).

## Scope (in)
* **No-op path:** if MT-6.3-02 recorded all targets met, write the "no tuning
  required" record into the performance report (with the run reference) and close —
  no speculative optimization.
* **Tuning path (only for classified misses):**
  * Database-side: add indexes for the identified slow queries (claim/lease
    lookups, event listing, board queries) as a dedicated migration — reversible
    where practical per Section 16.5; schema-diff check updated (Section 20.4 item
    4).
  * Pooling/connection-side: adjust database/Redis connection pooling and worker
    concurrency configuration within the Section 16.1 service definitions —
    configuration values documented, not magic numbers.
  * Query-side micro-fixes only where a miss classification names a specific query;
    anything structural (caching layers, denormalization) exceeds the plan's named
    tuning vocabulary — raise it as a follow-up/risk instead of expanding scope
    (NFR-09 says scale without architectural change).
* Re-run MT-6.3-01 scenarios after each change batch and record before/after
  percentiles in the performance report until every target passes, or the
  remaining misses are escalated in the report and changelog.
* Changelog note (Section 20.4 item 7).

## Out of scope
* Writing/altering the scenarios or thresholds — MT-6.3-01 (thresholds are plan
  values; never moved to make a run pass).
* Application feature changes, refactors, or "while I'm here" cleanups — Section
  20.3 split rule.
* Architecture changes (new services, caches as infrastructure, queue redesign) —
  contradicts NFR-09's premise; escalate instead.
* Web/browser tuning — MT-4.11-04's domain.
* Hardware/infra scaling (bigger VPS) — a capacity decision for the plan owner, not
  a tuning change (note it if that is what the evidence shows).

## Target paths
* `backend/` — index migration(s) and query adjustments (miss-driven only)
* `infra/compose/` — pooling/worker configuration values (documented defaults)
* `docs/plan/performance-report.md` — before/after tables, no-op record or final
  escalation
* WP changelog entry (changes applied, final verdict)

## Acceptance criteria
- [ ] Either a documented "no tuning required" record with MT-6.3-02's run reference,
  or applied tuning changes each traceable to a classified miss (Section 19 WP-6.3
  deliverable; Section 20.5).
- [ ] After tuning, re-run scenarios show every NFR-02/03 target met at the
  Section 18 scenario shape (20 agents, 10,000 tasks) — Section 19 WP-6.3
  acceptance — or the remaining miss is escalated in the report with evidence
  (Section 20.4 item 1).
- [ ] Any index change ships as its own reversible migration with the schema-diff
  check green (Section 20.4 item 4; Section 16.5).
- [ ] Configuration changes (pooling, worker concurrency) are documented with their
  rationale and defaults (Section 16.1/16.2 discipline).
- [ ] Tests/lint green in CI after changes (Section 20.4 item 2); changelog note
  added (item 7).

## Test command
Re-run the MT-6.3-01 scenario suite against local Compose and confirm the report's
verdict lines now pass for NFR-02 and NFR-03 at 20 agents / 10,000 tasks; then run
`pytest backend/tests/ -k "lease or claim or events"` plus the migration check
(no unapplied model changes — Section 18 quality gates) to prove tuning did not
regress correctness.

## Attachments
* [NFR-02, NFR-03, NFR-09 — Latency and scalability requirements](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.3 deliverables and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing strategy (Performance row)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Tuning on a noisy local machine can "fix" variance — only accept a change as
  effective if the before/after runs were comparable (same seed, same machine
  state); otherwise re-run (MT-6.3-02's run-count discipline).
* Indexes have write costs — the claim/checkpoint path is write-heavy
  (FR-LEA-01 row locking); verify NFR-02 still passes after every index added, and
  watch claim-conflict behavior (Section 17 metric) for regressions.
* If every plausible bounded fix is applied and a target still misses, the honest
  outcome is a documented escalation (risk note + changelog), not threshold edits —
  the plan's NFR values are not this task's to change.
