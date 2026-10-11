# MT-3.4-05 — Implement R8 auditor flag and R9 auto-complete switch rules

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.4-05 |
| Title | Implement R8 auditor flag and R9 auto-complete switch rules |
| Parent WP | WP-3.4 — Policy Engine (Milestone M3) |
| Requirements | FR-AUD-02, FR-AUD-03, FR-AUD-04, ADR-009 |
| Priority | M |
| Dependencies | MT-3.4-01 (framework); MT-3.3-04/MT-3.3-05 (proposed_verdict persisted); MT-3.1-01 (auto_complete_enabled policy) |
| Parent sections | 9.4 (R8, R9), 7.2 (auto_complete_enabled), 8.4, 8.5, 10.5 (verdict enum), 19 (WP-3.4), 20.4, 20.5 |

## Context
Section 9.4's final pair: **R8 Auditor flag** fails when the auditor's proposed
verdict is not "pass" → `auditor_flagged`. **R9 Switch** fails when
`auto_complete_enabled` is false → `policy_forced_review` (auto-complete disabled).
R8 enforces Section 8.2 T14's guard wording ("any rule fails or auditor flags") and
FR-AUD-02 (auditor proposes, engine disposes). R9 implements Section 7.2's switch —
"if false, every task goes to human review" — the project-wide kill switch for
auto-complete, and Section 8.4's `policy_forced_review` reason.

## Inputs / Prerequisites
* MT-3.4-01 — rule interface, registry slots R8/R9, table-driven harness.
* Audit Report `proposed_verdict` (Section 7.2), set from the Section 10.5 verdict
  enum `pass` / `flag_risk` / `fail` (MT-3.3-05).
* MT-3.1-01 — Project Policy `auto_complete_enabled` (default true, Section 7.2).

## Scope (in)
* Register **R8**: fail iff `proposed_verdict` != "pass" (i.e. `flag_risk` or `fail`);
  reason `auditor_flagged` (Section 9.4 verbatim). On the coder-evidence **T10** path
  (Section 8.5, no auditor verdict exists) R8's input is absent — represent that
  explicitly per the MT-3.4-01 context contract (see Risk notes), consistent with how
  R7's absent input is handled.
* Register **R9**: fail iff the project's `auto_complete_enabled` is false; reason
  `policy_forced_review` (Section 8.4 verbatim: "auto-complete disabled").
* Pure functions over the MT-3.4-01 context; R9 reads the policy flag only — a model
  message, auditor note or rules text can never flip it (Section 19: "model text
  cannot override").
* Table-driven tests: R8 pass (`pass` verdict), R8 fail (`flag_risk`, `fail`
  separately); R9 pass (enabled), R9 fail (disabled); combined case; verdict-absent
  (T10 path) behavior per the documented convention.
* Add a WP changelog note.

## Out of scope
* Transition application — MT-3.4-07 (R8 failure is part of **T14**'s "auditor flags"
  guard; R9 failure forces **T14**/**T10** escalation regardless of other rules; no
  transition code here).
* Persisting rule results — MT-3.4-06.
* Validating the verdict payload — MT-3.3-05 / WP-3.5.
* The web/mobile policy editor toggle — WP-4.10.

## Target paths
* `backend/apps/audit/` (R8 and R9 rule implementations)
* `backend/tests/` (table-driven R8/R9 cases)
* WP changelog entry

## Acceptance criteria
- [ ] **R8** fails iff `proposed_verdict` is not "pass" (`flag_risk` or `fail`);
  reason `auditor_flagged` (Section 9.4 verbatim; Section 10.5 verdict enum).
- [ ] **R9** fails iff `auto_complete_enabled` is false; reason
  `policy_forced_review` (Section 8.4 verbatim; Section 7.2 switch semantics: every
  task goes to human review).
- [ ] R9 is decided only by the persisted policy flag — no auditor note, execution
  summary or model-provided text can influence it (Section 19 WP-3.4: "model text
  cannot override"; ADR-009).
- [ ] R9 failing forces escalation even when every other rule passes — the engine's
  combined result must be `escalate` (Section 9.4 output contract).
- [ ] Failures feed FR-AUD-04 escalation via **T14** (audited path; R8 also satisfies
  T14's auditor-flags guard) or **T10**'s escalation branch (Section 8.5) — reasons
  registered here, transitions in MT-3.4-07.
- [ ] Table-driven pass/fail cases per rule and combined (Section 19 WP-3.4
  acceptance).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k policy_rules_r8_r9 -q` and confirm: R8 pass on `pass`,
fail on `flag_risk` and on `fail`; R9 pass when enabled, fail when disabled with all
other rules green; combined case escalates with `auditor_flagged` /
`policy_forced_review`; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 9.4 — Policy Engine rules R8, R9](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Auditor verdict enum](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.4 — Review reasons](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* R8's absent input on the **T10** path must follow the same convention settled for
  R7 in MT-3.4-01; "no proposed verdict yet" must not read as "verdict != pass" (which
  would escalate every coder-path submission) nor be silently ignored without a
  documented rule — record the convention and OQ-xx if the plan stays ambiguous.
* `auto_complete_enabled` false escalates everything, including tasks an owner would
  trivially approve — that is the Section 7.2 intent; do not add heuristics that
  soften it.
