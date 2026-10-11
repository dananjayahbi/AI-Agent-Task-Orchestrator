# MT-3.3-03 — Implement audit lease handling with expiry release

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.3-03 |
| Title | Implement audit lease handling with expiry release |
| Parent WP | WP-3.3 — Auditor claim and verdict API (Milestone M3) |
| Requirements | FR-AUD-01, G-20 |
| Priority | M |
| Dependencies | MT-3.3-01 (auditor claim / T11); MT-3.3-02 (independence passes first); WP-1.6 lease semantics; MT-1.5-01 (transition registry) |
| Parent sections | 8.2 (T11, T12), 8.6 (lease semantics), 7.2, 19 (WP-3.3), 20.4, 20.5 |

## Context
Section 8.2 gives auditors the same lease discipline as coders: **T11** sets the audit
lease on auditor claim ("same lease rules"), and **T12** (`to_be_audited` →
`to_be_audited`) fires when the audit lease expires — release the audit lease and
increment the audit retry counter, without leaving the state. Section 19 WP-3.3
acceptance is precise: "audit lease expiry releases the audit claim without losing the
resolution." G-20 made auditor lease part of the independence design; Section 8.6
defines acquire/extend/expire/fencing semantics the audit lease must mirror.

## Inputs / Prerequisites
* MT-3.3-01 — the auditor claim that performs the T11 side (lease fields set after
  independence passes).
* Parent plan Section 8.2 rows T11 and T12 — exact guards and side effects.
* Parent plan Section 8.6 — lease acquire/extend/expire/fencing rules (policy
  `lease_duration_minutes`, `lease_max_total_minutes`, lease generation).
* MT-1.5-01 — transition registry for registering T12.
* Section 7.2 — lease fields on Task (`lease_acquired_at`, `lease_expires_at`,
  `claimed_role`, worker/auditor identity, audit retry counter).
* Section 7.2 Task Resolution — must remain intact through T12.

## Scope (in)
* On successful auditor claim (T11 side effects): set lease fields for the auditor
  with the same policy-driven semantics as coder leases (duration, hard cap,
  lease generation increment) and `claimed_role` = `auditor`.
* Register and implement **T12** (actor S): guard — auditor lease expired
  (`lease_expires_at` < now while `claimed_role` = `auditor`); side effects — release
  the audit lease (clear auditor lease fields and `claimed_role`), increment the audit
  retry counter, task stays `to_be_audited`, Transition row written. The resolution
  and its artifacts are untouched.
* Checkpoint extension by the auditor reuses the existing extension rules
  (Section 8.6, MT-1.6-03) — no parallel extension logic.
* A service function the lease sweeper can invoke for expired audit leases (call-site
  scheduling stays with WP-1.7, mirroring how T5 was integrated).
* Unit tests: acquire sets fields; extension respects the hard cap; expiry releases
  only the audit side and preserves the resolution; re-claim after T12 allowed.
* Add a WP changelog note.

## Out of scope
* Sweep scheduling/interval — WP-1.7 (this task provides the T12 invocation point).
* Coder lease behavior (T4/T5/T6) — WP-1.6 / WP-1.7.
* Audit retry counter exhaustion policy (what happens after N audit retries) — the
  plan defines no T-transition for it; raise OQ-xx if a bound is needed, do not invent
  one.
* Losing/changing the resolution or artifacts — explicitly forbidden here.

## Target paths
* `backend/apps/` (audit lease acquire/extend on claim; T12 registration and guard)
* `backend/tests/` (audit lease and T12 tests)
* WP changelog entry

## Acceptance criteria
- [ ] T11 sets an audit lease with Section 8.6 semantics (policy duration, hard cap,
  fencing generation) and `claimed_role` = `auditor` (FR-AUD-01; G-20 lease parity).
- [ ] T12 matches Section 8.2: expired audit lease releases the audit claim, increments
  the audit retry counter, and leaves the task in `to_be_audited`.
- [ ] After T12 the Task Resolution, patch artifact and audit-side history are intact —
  Section 19 WP-3.3 acceptance "expiry releases the audit claim without losing the
  resolution".
- [ ] A new independent auditor can claim again after T12 (subject to MT-3.3-02).
- [ ] No coder-lease side effects are touched by T12; coder regression tests stay
  green (Section 8.3 invariant 1).
- [ ] Transition/Event rows written per Section 8.2 rules; events from the
  Section 9.6 catalog only (Section 20.4 item 6).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k audit_lease -q` and confirm: T11 lease fields set per
policy, extension capped by `lease_max_total_minutes`, T12 releases only the audit
side with resolution intact and audit retry counter incremented, and re-claim works;
then `pytest backend/tests -q` stays green.

## Attachments
* [Section 8.2 — Transition table (T11, T12)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.6 — Lease semantics in detail](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.3 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* T12 must run through the same sweeper cadence as T5 (Section 9.9, every 60 s,
  idempotent, skip-locked); if the sweeper integration point from WP-1.7 is not
  extensible, coordinate rather than adding a second timer.
* Event semantics for T12 are not pinned to a catalog event name — check
  Section 9.6 before emitting anything new; use an existing catalog event or emit
  only the Transition row, never an uncataloged event (Section 20.4 item 6).
