# MT-3.4-06 — Persist rule results and engine version on every audit report

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.4-06 |
| Title | Persist rule results and engine version on every audit report |
| Parent WP | WP-3.4 — Policy Engine (Milestone M3) |
| Requirements | FR-AUD-02, FR-AUD-04, ADR-009 |
| Priority | M |
| Dependencies | MT-3.4-01 … MT-3.4-05 (all rules registered); MT-3.3-04 (Audit Report model) |
| Parent sections | 9.4 (persist results, version stored on each Audit Report), 7.2 (policy_decision, policy_rule_results), 13.2 (review panel shows rule table), 19 (WP-3.4), 20.4, 20.5 |

## Context
Section 9.4's design notes require that the result — every rule and its outcome — is
persisted so the human reviewer sees exactly why the task was escalated, and that the
engine version is stored on each Audit Report for traceability. Section 7.2 already
allots `policy_decision` and `policy_rule_results` (JSON listing every rule and
pass/fail) on the Audit Report; Section 13.2's review panel renders "escalation
reasons with the rule table". This micro-task writes the engine's output onto the
report transactionally so persistence is inseparable from the decision.

## Inputs / Prerequisites
* MT-3.4-01 — evaluation result shape: per-rule outcomes, approve/escalate, engine
  version stamp.
* MT-3.3-04 — Audit Report row with nullable `policy_decision` and
  `policy_rule_results`.
* All rules R1–R9 registered (MT-3.4-02 … MT-3.4-05) so "every rule" is enumerable.
* Section 8.3 invariant 4 — persistence records the engine's decision; nothing else
  writes these fields.

## Scope (in)
* Persist on the Audit Report after every evaluation:
  * `policy_decision` — the engine's `approve`/`escalate` outcome (Section 9.4 verbs);
  * `policy_rule_results` — JSON listing **every** rule R1–R9 with its pass/fail
    outcome (and the failure reason where failed) — never a partial list of only
    failures;
  * engine version — stored per Section 9.4 ("the version is stored on each Audit
    Report"); add the field to the model/migration if MT-3.3-04 did not include it.
* Write both atomically with the decision application (same transaction as the
  transition in MT-3.4-07) so a report can never show a decision without its rule
  results or vice versa.
* Restricted writes: only the engine integration path may set these fields
  (application-role discipline akin to Section 7.4's append-only rule for transitions;
  consistent with invariant 8.3.4).
* Read surface: the listing endpoint (MT-3.3-04) returns the persisted results
  unmodified for the web review panel (Section 13.2) and mobile review sheet
  (Section 14.1).
* Unit tests: full nine-rule result persisted; decision+results atomicity; version
  present; re-evaluation (new attempt) overwrites/appends per the chosen report
  lifecycle from MT-3.3-04's note; engine-only write guard.
* Add a WP changelog note.

## Out of scope
* Producing the evaluation — MT-3.4-01 (framework) and rule MTs.
* Triggering T13/T14/T10 — MT-3.4-07 (this task defines the persistence the
  transition writes alongside).
* Rendering the rule table — WP-4.8 / WP-5.8.
* Coder-path (**T10**, Section 8.5) persistence target — see Risk notes; if the plan
  does not tie coder-evidence decisions to an Audit Report, raise OQ-xx rather than
  inventing a new row type here.

## Target paths
* `backend/apps/audit/` (persistence of policy_decision, policy_rule_results, engine
  version; model field/migration if needed)
* `backend/tests/` (persistence and atomicity tests)
* WP changelog entry

## Acceptance criteria
- [ ] Every evaluation writes `policy_decision` and `policy_rule_results` covering all
  nine rules R1–R9 with per-rule pass/fail (Section 9.4: persist every rule and its
  outcome; Section 7.2 field semantics; Section 20.5 traceability).
- [ ] The engine version from MT-3.4-01 is stored on the Audit Report
  (Section 9.4: version stored on each Audit Report for traceability).
- [ ] Decision and rule results are written in the same transaction as the transition
  (no report can show one without the other; FR-AUD-04 auditability).
- [ ] Only the engine integration path writes these fields — model text, auditor
  notes or API callers cannot alter them (invariant 8.3.4; Section 19 "model text
  cannot override").
- [ ] `GET /tasks/{id}/audit-reports` returns persisted results intact for review
  panels (Section 13.2 rule table).
- [ ] Migration reviewed; OpenAPI schema diff reviewed if the report schema changes
  (Section 20.4 item 4); tests green in CI; changelog note added
  (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k policy_persistence -q` and confirm: all nine rule
outcomes persisted with decision and engine version, atomic write with the transition
(success and rollback paths), engine-only write guard, and listing round-trip; then
`pytest backend/tests -q` stays green.

## Attachments
* [Section 9.4 — Policy Engine design notes (persistence and versioning)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Audit Report entity](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.2 — Review panel (rule table rendering)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The **T10** coder path (Section 8.5) evaluates rules but may have no Audit Report
  yet the plan requires results persisted ("the result … is persisted") — confirm
  where coder-path decisions land (report-less record vs. report per submission) and
  raise OQ-xx if unresolved; do not create an unplanned entity silently.
* JSON result shape is not fixed by the plan beyond "every rule and pass/fail" —
  version it alongside the engine version so later engines can evolve the shape
  without breaking stored history.
