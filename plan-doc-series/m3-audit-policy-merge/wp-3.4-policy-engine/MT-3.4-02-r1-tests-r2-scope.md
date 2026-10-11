# MT-3.4-02 — Implement R1 tests and R2 scope rules

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.4-02 |
| Title | Implement R1 tests and R2 scope rules |
| Parent WP | WP-3.4 — Policy Engine (Milestone M3) |
| Requirements | FR-AUD-02, FR-AUD-03, FR-AUD-04, ADR-009 |
| Priority | M |
| Dependencies | MT-3.4-01 (framework and registry); MT-3.2-03/MT-3.2-04 (authoritative changed_files and scope semantics) |
| Parent sections | 9.4 (R1, R2), 8.4, 8.5, 19 (WP-3.4), 20.4, 20.5 |

## Context
Section 9.4's rule table defines **R1 Tests** — fails when any test command in
evidence has a non-zero exit code, or when there is no test evidence at all; review
reason `test_failure`. **R2 Scope** — fails when any changed file is outside
`target_scope`; review reason `scope_violation`. Per the Section 9.4 design notes, R2
is recomputed from the patch stored by the bridge (the authoritative `changed_files`
from MT-3.2-03), not from claims in the auditor's text; R1 consumes test evidence
(coder evidence on the T10 path per Section 8.5, auditor evidence on the audited
path). FR-AUD-03 requires all tests exit 0 and no out-of-scope changes for
auto-complete; FR-AUD-04 requires any failed rule to escalate with an enumerated
reason.

## Inputs / Prerequisites
* MT-3.4-01 — rule interface, registry slots R1/R2, table-driven harness.
* Audit Report / coder evidence (`evidence.commands[].exit_code`, Section 10.5 shape)
  as R1's input; "no test evidence at all" must be representable in the context.
* MT-3.2-03 — authoritative `changed_files`; MT-3.2-04 — shared `target_scope` glob
  semantics and path normalization for R2.

## Scope (in)
* Register **R1** in slot R1: fails if any command in evidence has non-zero
  `exit_code`, OR if evidence contains no test command results at all; failure
  carries review reason `test_failure` (Section 9.4 verbatim).
* Register **R2** in slot R2: recompute from the authoritative changed-file list
  against the task's `target_scope` globs (shared matcher with MT-3.2-04); fails if
  any changed file is outside every glob; failure carries review reason
  `scope_violation` (Section 9.4 verbatim).
* Both rules pure over the MT-3.4-01 context — no re-querying, no text parsing of
  auditor notes (Section 9.4 design note).
* Table-driven tests: R1 pass (all zero exits), R1 fail (one non-zero), R1 fail
  (missing test evidence), R2 pass (all in scope), R2 fail (one file outside), and
  combined cases where both fail (both reasons present in the result list).
* Add a WP changelog note.

## Out of scope
* Applying outcomes to transitions — MT-3.4-07 (rules R1/R2 failing escalate via
  **T14** on the audited path and via **T10**'s escalation branch on the
  `audit_required` false path — Section 8.5; no transition logic here).
* Persisting rule results — MT-3.4-06.
* Collecting evidence / running tests — bridge auditor flow (WP-3.5) and rules block
  (Section 10.6).
* The scope check used directly at submission time — MT-3.2-04 (R2 is the engine's
  re-evaluation of the same semantics).

## Target paths
* `backend/apps/audit/` (R1 and R2 rule implementations)
* `backend/tests/` (table-driven R1/R2 cases in the harness)
* WP changelog entry

## Acceptance criteria
- [ ] **R1** fails exactly when an evidence test command has a non-zero exit code or
  evidence contains no test results; failure reason `test_failure` (Section 9.4
  verbatim; FR-AUD-03 tests exit 0).
- [ ] **R2** fails exactly when a changed file is outside `target_scope`, recomputed
  from the stored patch's authoritative file list — never from auditor/coder text
  (Section 9.4 design note; FR-AUD-03 no out-of-scope changes).
- [ ] Failures carry review reasons `test_failure` / `scope_violation` verbatim from
  Section 8.4 for downstream **T14** (audited path) or **T10** escalation
  (Section 8.5 path) — FR-AUD-04.
- [ ] Table-driven cases cover R1 pass/fail, R2 pass/fail and their combination, per
  Section 19 WP-3.4 acceptance ("table-driven tests cover each rule pass/fail and
  combinations").
- [ ] Rules are pure functions of the MT-3.4-01 context; no I/O (ADR-009).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k policy_rules_r1_r2 -q` and confirm each table case: R1
zero-exit pass, non-zero fail, missing-evidence fail; R2 in-scope pass, out-of-scope
fail with `scope_violation`; combined case lists both reasons; then
`pytest backend/tests -q` stays green.

## Attachments
* [Section 9.4 — Policy Engine rules R1, R2](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.4 — Review reasons](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.4 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "No test evidence at all" needs a precise context representation (empty commands
  list vs. missing evidence) — fix it in the MT-3.4-01 context contract so R1 cannot
  pass by accident on absent data; ambiguity here silently approves unevidenced work.
* R2 must share the exact matcher/normalization of MT-3.2-04 or a submission can pass
  the T7 scope guard and then fail R2 (or the reverse) with no plan-level resolution.
