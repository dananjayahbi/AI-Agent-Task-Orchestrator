# MT-3.9-03 — Write escalation tests covering each review reason

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.9-03 |
| Title | Write escalation tests covering each review reason |
| Parent WP | WP-3.9 — Escalation notifications hook (Milestone M3) |
| Requirements | FR-MOB-04 |
| Priority | M |
| Dependencies | MT-3.9-01, MT-3.9-02 (payload and emission), WP-3.4 (T14 rule failures), WP-1.7 (T9 sweeper), WP-3.7 (T18 conflict reporting) |
| Parent sections | 8.4, 9.4, 9.6, 19 (WP-3.9), 18, 20.4, 20.5 |

## Context
WP-3.9's acceptance: "each review reason yields one event with rule details."
Section 8.4's canonical enum has exactly 12 values: `self_flagged`,
`scope_violation`, `test_failure`, `migration_detected`, `sensitive_config_changed`,
`critical_path_changed`, `diff_over_threshold`, `low_confidence`, `retry_exhausted`,
`merge_conflict`, `auditor_flagged`, `policy_forced_review`. Section 9.4 maps R1–R9
failures to reasons; Section 8.2 maps the entering transitions (T8, T9, T14, T18).
Section 18's unit row requires table-driven tests for every transition. This task
proves full reason coverage — the property M5's push mapper and the review UI rely
on.

## Inputs / Prerequisites
* MT-3.9-01 (payload), MT-3.9-02 (emission hook).
* Parent plan Sections 8.4 (enum), 9.4 (rule → reason map), 8.2 (entering
  transitions) — the coverage table, verbatim.
* WP-3.4 — Policy Engine to drive T14 rule failures; WP-1.7 — sweeper for T9;
  WP-3.7 — executor for T18 (dependency at test-wiring level; skip-gate if not yet
  built and record it).
* Section 18 — table-driven testing discipline.

## Scope (in)
* A table-driven suite with one row per canonical review reason, each row driving
  the transition that produces it:
  * T8: `self_flagged` (self-flagged submit), `scope_violation` (changed files
    outside `target_scope`);
  * T9: `retry_exhausted` (`failure_retry_count` ≥ `max_retries`);
  * T14 via Section 9.4 rules: `test_failure` (R1), `scope_violation` (R2),
    `critical_path_changed` (R3), `migration_detected` (R4),
    `sensitive_config_changed` (R5), `diff_over_threshold` (R6), `low_confidence`
    (R7), `auditor_flagged` (R8), `policy_forced_review` (R9);
  * T18: `merge_conflict`.
* Per-row assertions: exactly one `review.requested` event; canonical `review_reason`
  matches the row; envelope fields correct (`type`, `project_id`, `task_id`,
  `occurred_at`, `actor`, `task_version`); rule details present for T14 rows (the
  failed rule and its outcome) per MT-3.9-01's contract.
* Negative controls: non-entry transitions (claim, submit → `to_be_audited`,
  completion) emit no `review.requested`.
* Coverage assertion: the suite fails if Section 8.4's enum contains a reason no row
  exercises (so a future enum addition forces a test).
* CI wiring with the backend test jobs (Section 20.4 item 2).

## Out of scope
* Payload design and emission mechanics — MT-3.9-01/02 (asserted, not re-built).
* Push delivery assertions (10 s dispatch, dedupe) — WP-5.4.
* Policy Engine rule correctness — WP-3.4's own tests; this suite only picks
  representative failures per reason.
* Web/mobile rendering of reasons — WP-4.8/WP-5.8.

## Target paths
* `backend/tests/` — escalation reason table-driven suite
* CI pipeline config (suite invocation)
* WP changelog entry

## Acceptance criteria
- [ ] Every one of the 12 Section 8.4 reasons is exercised by at least one row and
  produces exactly one `review.requested` event with that reason (WP-3.9 acceptance,
  FR-MOB-04).
- [ ] T14 rows assert rule details naming the failed rule and outcome (Section 9.4,
  "with rule details"); T8/T9/T18 rows assert reason without fabricated rule data.
- [ ] Envelope fields match Section 9.6 on every row; no non-entry transition emits
  the event (negative controls).
- [ ] The suite fails when a new enum reason lacks a row (coverage guard).
- [ ] Only Section 9.6 catalog types and Section 8.4 reasons appear (Section 20.4
  items 5–6); suite green in CI (item 2); changelog note added (item 7).

## Test command
`pytest backend/tests -k escalation_reasons -q` — run the reason table against real
Postgres (Section 18) asserting one event per reason with rule details where
applicable, plus the coverage guard and negative controls; then
`pytest backend/tests -q` stays green.

## Attachments
* [Section 8.4 — Review reasons (canonical enum)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.4 — Policy Engine (rule → reason)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Reasons reachable only through other WPs' machinery (T9 sweeper, T18 executor) can
  tempt a shortcut of asserting the hook directly with a synthetic reason — accept a
  gated integration row for those, but do not let synthetic rows replace real
  transition coverage for T8/T14.
* The coverage guard is the anti-rot device: without it, a Section 8.4 enum addition
  ships untested — keep it in the suite, not in review checklists.
* Rule-details assertions must key on the failed rule id, not on human-readable
  message text (message wording will evolve; the rule outcome is the contract).
