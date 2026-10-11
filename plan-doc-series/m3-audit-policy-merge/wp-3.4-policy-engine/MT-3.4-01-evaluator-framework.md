# MT-3.4-01 — Build the policy evaluator framework (pure, versioned, testable)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.4-01 |
| Title | Build the policy evaluator framework (pure, versioned, testable) |
| Parent WP | WP-3.4 — Policy Engine (Milestone M3) |
| Requirements | FR-AUD-02, FR-AUD-03, FR-AUD-04, ADR-009 |
| Priority | M |
| Dependencies | MT-3.1-01 (policy inputs); MT-3.2-03 (authoritative stats/files); MT-3.3-04 (audit report inputs) |
| Parent sections | 9.4 (Policy Engine), 8.3 (invariant 4), 7.2 (Audit Report), 19 (WP-3.4), 20.4, 20.5 |

## Context
Section 9.4 defines the Policy Engine as a pure, deterministic rules evaluator.
Inputs: Task, Project Policy, Resolution (changed files and stats), Audit Report
evidence. Output: `approve` or `escalate` with a list of rule results. ADR-009 chose
a deterministic engine over an LLM judge to prevent self-approval; Section 19 WP-3.4
requires table-driven tests per rule and states the engine never approves when any
rule fails and model text cannot override. This micro-task builds the framework —
context assembly, rule interface, evaluation loop, version stamping — that
MT-3.4-02 … MT-3.4-05 plug individual rules into.

## Inputs / Prerequisites
* Parent plan Section 9.4 — inputs, output contract, design notes (recompute R2–R6
  from the stored patch; persist every rule's outcome; version stored on each Audit
  Report). Use the section by pointer; do not re-derive its table here.
* MT-3.1-01 — Project Policy fields as rule inputs.
* MT-3.2-03 — authoritative `changed_files` / `diff_summary` (patch-derived).
* MT-3.3-04 — Audit Report (`evidence`, `confidence`, `proposed_verdict`,
  `policy_rule_results`, `policy_decision` fields to fill later).
* Section 8.3 invariant 4 — only the engine may set a policy-approved outcome.

## Scope (in)
* An evaluation context type carrying exactly the Section 9.4 inputs (Task, Project
  Policy, Resolution-derived data, Audit Report evidence) — assembled by an adapter
  from persisted rows, with no I/O inside rule evaluation.
* A rule interface and registry: each rule is a pure function over the context
  returning pass/fail plus the Section 9.4 review-reason association for failure;
  rules declare stable ids R1…R9 in registration order.
* The evaluator: runs all registered rules, never short-circuits the result list
  (every rule's outcome is produced for persistence), and maps outcomes to the
  Section 9.4 output — `approve` only when every rule passes, otherwise `escalate`
  (the exact verb per Section 9.4).
* Engine version stamp: a version constant carried on every evaluation result for
  persistence onto the Audit Report (Section 9.4 design note).
* Determinism and purity: no clock, network, database or randomness inside
  evaluation; same context bytes → same result (ADR-009).
* A table-driven test harness scaffold accepting (context, expected result,
  expected per-rule outcomes) cases — WP-3.4's acceptance requires this.
* Add a WP changelog note.

## Out of scope
* Any concrete rule R1–R9 — MT-3.4-02 … MT-3.4-05.
* Persisting results/version onto reports — MT-3.4-06.
* Transition integration T13/T14/T10 — MT-3.4-07.
* Bridge evidence capture (Section 10.8) — WP-2.10; context assembly only reads what
  is already persisted.
* Calling an LLM anywhere in the decision path — explicitly forbidden by ADR-009.

## Target paths
* `backend/apps/audit/` (evaluator framework, context adapter, rule registry)
* `backend/tests/` (framework and determinism tests, harness scaffold)
* WP changelog entry

## Acceptance criteria
- [ ] The evaluator's inputs and output match Section 9.4 by pointer: context = Task +
  Project Policy + Resolution (changed files and stats) + Audit Report evidence;
  result = approve/escalate with per-rule outcomes (Section 20.5 traceability).
- [ ] Evaluation is pure and deterministic — repeated runs on identical context yield
  identical results, no I/O (ADR-009).
- [ ] `approve` is returned only when every registered rule passes; any failure
  produces `escalate` with that rule in the result list (Section 19 WP-3.4: engine
  never approves when any rule fails).
- [ ] Every evaluation output carries the engine version for later persistence
  (Section 9.4 design note; MT-3.4-06 consumes it).
- [ ] Rule ids R1…R9 are reserved in the registry so MT-3.4-02 … MT-3.4-05 register
  into stable slots (Section 20.5 traceability to Section 9.4).
- [ ] Table-driven harness accepts context/expected-outcome cases and is exercised by
  at least one smoke case (Section 19 WP-3.4 acceptance path).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k policy_evaluator -q` and confirm: determinism (same
context twice → identical result), no-I/O guard, approve-only-if-all-pass logic with a
fake rule set, engine version present on every result, and registry id reservation;
then `pytest backend/tests -q` stays green.

## Attachments
* [Section 9.4 — Policy Engine](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.4 goal, deliverables, acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-009 — Deterministic Policy Engine](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The Section 9.4 output verb (`approve`/`escalate`) must map 1:1 onto transition
  guards in MT-3.4-07; fix the vocabulary here so T13/T14 integration cannot drift.
* R7 (confidence) has no input on the coder-evidence path (T10, Section 8.5) — the
  context adapter must represent "no auditor confidence" explicitly; decide the
  convention now (flag as OQ-xx if the plan's wording does not settle it) so rules
  written later do not invent it independently.
