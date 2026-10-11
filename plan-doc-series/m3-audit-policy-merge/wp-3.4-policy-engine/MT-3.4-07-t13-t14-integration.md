# MT-3.4-07 — Integrate policy decisions with transitions T13 and T14

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.4-07 |
| Title | Integrate policy decisions with transitions T13 and T14 |
| Parent WP | WP-3.4 — Policy Engine (Milestone M3) |
| Requirements | FR-AUD-02, FR-AUD-03, FR-AUD-04, ADR-009 |
| Priority | M |
| Dependencies | MT-3.4-01 … MT-3.4-06 (engine complete and persisting); MT-3.3-05 (verdict seam); MT-3.2-05 (T10 seam); MT-1.5-01 (transition registry) |
| Parent sections | 8.2 (T13, T14), 8.4, 8.5, 8.3 (invariant 4), 9.4, 9.6, 9.8, 19 (WP-3.4), 20.4, 20.5 |

## Context
Section 8.2 defines the engine's two audited-path transitions. **T13**
`to_be_audited` → merge-pending (task stays `to_be_audited` with `merge_status` =
`pending`) when all Policy Engine rules pass — side effects: `merge_status` =
`pending`, emit `audit.passed`. **T14** `to_be_audited` → `in_human_review` when any
rule fails or the auditor flags — side effect: `review_reason` enumerated
(Section 8.4), push trigger. Section 8.3 invariant 4: the Policy Engine is the only
component that can set a policy-approved outcome. Section 8.5's **T10** coder path
(`audit_required` false) funnels through the same engine: all pass → merge-pending,
otherwise T8-style escalation. This micro-task wires the engine's decisions into the
state machine, closing WP-3.4's slice "integration with transitions T13/T14" and the
seams left by MT-3.2-05 (T10) and MT-3.3-05 (verdict).

## Inputs / Prerequisites
* MT-3.4-01 … MT-3.4-06 — evaluation result (`approve`/`escalate`), all rules
  R1–R9, persisted rule results and engine version.
* MT-1.5-01 — transition registry/guards/transaction machinery; Section 9.2/8.2
  transition rules (illegal transitions → `TASK_STATE_CONFLICT`).
* MT-3.2-05 — T10 seam awaiting the engine decision.
* MT-3.3-05 — verdict endpoint seam awaiting the engine decision.
* Section 9.6 event catalog (`audit.passed`, `audit.escalated`,
  `review.requested` etc.) and Section 9.8 push triggers.

## Scope (in)
* Register and implement **T13** (actors A, S): guard — the engine result is
  `approve`, meaning every rule R1–R9 passes (and the auditor did not flag, which R8
  already covers); side effects — `merge_status` = `pending`, emit `audit.passed`
  (Section 9.6 catalog), task column stays `to_be_audited` with the approved-merging
  badge per the Section 8.1 note; Transition and Event rows in one transaction
  (FR-TSK-03/04).
* Register and implement **T14** (actors A, S): guard — engine result `escalate`
  (any of R1–R9 fails, including R8 auditor flag); side effects — `in_human_review`,
  `review_reason` set to the Section 8.4 reason carried by the failing rule(s) with
  verbatim values (`test_failure`, `scope_violation`, `critical_path_changed`,
  `migration_detected`, `sensitive_config_changed`, `diff_over_threshold`,
  `low_confidence`, `auditor_flagged`, `policy_forced_review`), Section 9.8 push
  trigger, `audit.escalated`/`review.requested` emission per the Section 9.6 catalog.
* Close the **T10** seam (MT-3.2-05): coder-path engine evaluation decides
  merge-pending (approve) vs. T8-style escalation with an enumerated reason
  (Section 8.5).
* Close the **verdict** seam (MT-3.3-05): `POST /tasks/{id}/audit-verdict` runs the
  engine and applies T13 or T14 — the endpoint still never approves on its own
  (invariant 8.3.4).
* Multiple failing rules: every failing reason recorded (per MT-3.4-06 results);
  `review_reason` picks a deterministic primary — document the ordering rule (see Risk
  notes).
* Integration tests: approve path to merge-pending, each single-rule failure to
  `in_human_review` with the exact reason, combined failures, T10 approve/escalate,
  verdict-endpoint end-to-end, `TASK_STATE_CONFLICT` on wrong-state attempts.
* Add a WP changelog note.

## Out of scope
* Human decisions T15/T16 — WP-3.6; merge execution T17/T18 — WP-3.7.
* Bridge-side verdict tool — WP-3.5 (consumes this endpoint).
* Actual push delivery — WP-5.4 (Section 9.8 trigger only).
* Re-running the engine outside the transition paths — MT-3.4-01 framework.

## Target paths
* `backend/apps/audit/` (decision → transition application, seam closures)
* `backend/apps/tasks/` (T13/T14 registrations and guards)
* `backend/tests/` (integration tests for T13/T14/T10 and verdict path)
* WP changelog entry

## Acceptance criteria
- [ ] **T13** fires only when all rules R1–R9 pass: `merge_status` = `pending`, task
  remains `to_be_audited` with merge-pending badge semantics, `audit.passed` emitted
  from the Section 9.6 catalog (Section 8.2 T13; FR-AUD-02).
- [ ] **T14** fires when any of R1–R9 fails (including R8 `auditor_flagged`): task →
  `in_human_review` with `review_reason` set to the verbatim Section 8.4 enum value
  for the failing rule; push triggered per Section 9.8 (FR-AUD-04).
- [ ] No approve path exists outside the engine: an endpoint, model message or note
  cannot produce T13 without an engine `approve` (Section 8.3 invariant 4;
  Section 19 WP-3.4 "the engine never approves when any rule fails; model text
  cannot override").
- [ ] **T10** (Section 8.5) closed: `audit_required` false runs the same rules on
  coder evidence — approve → merge-pending, any failure → escalation with an
  enumerated reason (MT-3.2-05 seam no longer stubbed).
- [ ] Verdict endpoint (MT-3.3-05) closed: a submitted verdict drives T13 or T14
  end-to-end with rule results persisted (MT-3.4-06) in the same transaction.
- [ ] All emitted events are Section 9.6 catalog entries; illegal transitions return
  `TASK_STATE_CONFLICT` (Section 20.4 items 5 and 6).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k policy_transitions -q` and confirm: all-pass → T13
(`merge_status` pending, `audit.passed`), each of R1–R9 failing individually → T14
with its exact Section 8.4 reason, combined failures, T10 approve and escalate, and
verdict endpoint end-to-end; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 8.2 — Transition table (T13, T14)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.4 — Review reasons (canonical enum)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.5 — Behavior when audit_required is false](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.4 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Multiple simultaneous failures produce many reasons but the Task has a single
  `review_reason` field (Section 7.2) — the plan does not fix a primary-reason
  ordering. Choose a deterministic rule (e.g. Section 9.4 table order R1→R9),
  document it next to the mapping and in MT-3.4-06's stored results, and raise OQ-xx
  if the review panels need the full set surfaced differently.
* Ordering with WP-3.7: T13 sets `merge_status` = `pending` but "completed" arrives
  only via T17 — do not pre-advance state in this task; the Section 8.1 note keeps the
  card in `to_be_audited` until the Merge Executor reports.
