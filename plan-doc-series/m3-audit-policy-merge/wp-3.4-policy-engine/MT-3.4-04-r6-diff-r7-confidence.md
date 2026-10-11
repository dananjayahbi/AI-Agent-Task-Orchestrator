# MT-3.4-04 — Implement R6 diff size and R7 confidence rules

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.4-04 |
| Title | Implement R6 diff size and R7 confidence rules |
| Parent WP | WP-3.4 — Policy Engine (Milestone M3) |
| Requirements | FR-AUD-02, FR-AUD-03, FR-AUD-04, ADR-009 |
| Priority | M |
| Dependencies | MT-3.4-01 (framework); MT-3.2-03 (diff_summary stats); MT-3.1-01 (threshold and confidence policy fields); MT-3.3-04 (confidence on the report) |
| Parent sections | 9.4 (R6, R7), 7.2 (autonomous_diff_threshold_lines, auditor_min_confidence), 8.4, 8.5, 19 (WP-3.4), 20.4, 20.5 |

## Context
Section 9.4 defines **R6 Diff size** — fails when insertions + deletions exceed
`autonomous_diff_threshold_lines` (default 250) → `diff_over_threshold`. **R7
Confidence** — fails when auditor confidence is below `auditor_min_confidence`
(default 4) → `low_confidence`. Both are FR-AUD-03 vetoes ("diff within threshold,
confidence at least 4/5"). R6's input is the authoritative `diff_summary` computed
from the stored patch (Section 9.7, MT-3.2-03); R7's input is the auditor's
`confidence` (1–5) on the Audit Report — evidence the auditor supplies per the
Section 9.4 note, not something the engine re-derives.

## Inputs / Prerequisites
* MT-3.4-01 — rule interface, registry slots R6/R7, table-driven harness.
* MT-3.2-03 — authoritative `diff_summary.files/insertions/deletions`.
* MT-3.1-01 — `autonomous_diff_threshold_lines` (250) and `auditor_min_confidence` (4)
  from Project Policy (Section 7.2).
* MT-3.3-04 — `confidence` persisted on the Audit Report; Section 10.5 verdict shape
  (integer 1–5).
* Section 8.5 — the `audit_required` false path evaluates the same rules on coder
  evidence (which carries no auditor confidence — see Risk notes).

## Scope (in)
* Register **R6**: fail iff `insertions + deletions` > `autonomous_diff_threshold_lines`
  from the task's project policy; reason `diff_over_threshold` (Section 9.4 verbatim),
  with the strict-greater-than comparison exactly as Section 9.4 words it
  ("greater than").
* Register **R7**: fail iff auditor `confidence` < `auditor_min_confidence`; reason
  `low_confidence` (Section 9.4 verbatim).
* Pure functions over the MT-3.4-01 context; R6 uses patch-derived stats only
  (Section 9.4 design note: recompute from stored patch), R7 uses the stored
  confidence value only.
* Table-driven tests: R6 at threshold (passes), one line over (fails); R7 at minimum
  (passes), one below (fails); combined R6+R7 case; policy-variance cases (custom
  threshold/confidence from Section 7.2 fields respected).
* Add a WP changelog note.

## Out of scope
* Transition application — MT-3.4-07 (failures reach **T14** / **T10** escalation
  with enumerated reasons; also informs **T7/T8** pre-submission behavior — no
  transition code here).
* Persisting rule results — MT-3.4-06.
* Collecting or validating auditor confidence — WP-3.5 evidence validation /
  MT-3.3-04 range constraint.
* The `autonomous_diff_threshold_lines` UI editor — WP-4.10.

## Target paths
* `backend/apps/audit/` (R6 and R7 rule implementations)
* `backend/tests/` (table-driven R6/R7 cases)
* WP changelog entry

## Acceptance criteria
- [ ] **R6** fails iff insertions + deletions > `autonomous_diff_threshold_lines`;
  reason `diff_over_threshold` (Section 9.4 verbatim; FR-AUD-03 diff within
  threshold).
- [ ] **R7** fails iff auditor confidence < `auditor_min_confidence`; reason
  `low_confidence` (Section 9.4 verbatim; FR-AUD-03 confidence at least 4/5).
- [ ] R6 reads patch-derived `diff_summary` (MT-3.2-03 authoritative values), never
  agent/auditor claims (Section 9.4 design note); R7 reads the persisted report
  confidence (Section 10.5 supplied value).
- [ ] Policy variance respected: tests cover non-default threshold and minimum from
  Section 7.2 fields (FR-PRJ-05 inputs drive rules).
- [ ] Failures feed FR-AUD-04 escalation via **T14** (audited) / **T10** escalation
  (Section 8.5) — reasons registered here, transitions in MT-3.4-07.
- [ ] Table-driven pass/fail boundary cases per rule (Section 19 WP-3.4 acceptance).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k policy_rules_r6_r7 -q` and confirm: R6 passes at exactly
the threshold and fails one line over; R7 passes at the minimum and fails below;
custom policy values honored; combined case lists both reasons; then
`pytest backend/tests -q` stays green.

## Attachments
* [Section 9.4 — Policy Engine rules R6, R7](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Threshold and confidence policy fields](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.4 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* R7 on the **T10** path (Section 8.5, `audit_required` false): coder evidence carries
  no auditor confidence, so R7's input is absent. The plan does not state whether R7
  is "not applicable" or forced to pass there — settle this in the MT-3.4-01 context
  contract and record it as OQ-xx if unresolved; never let absent confidence equal
  4 by silent default without documenting it.
* Oversize patches (Section 9.7) keep stats-and-file-list-only — confirm
  `diff_summary` totals still populate in that degraded path, or R6 becomes
  unevaluable exactly when diffs are huge (fail-closed decision; raise OQ-xx with
  MT-3.4-03's related question).
