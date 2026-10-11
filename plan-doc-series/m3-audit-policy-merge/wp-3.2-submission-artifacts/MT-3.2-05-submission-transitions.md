# MT-3.2-05 — Implement submission transitions T7, T8, T10 with review reasons

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.2-05 |
| Title | Implement submission transitions T7, T8, T10 with review reasons |
| Parent WP | WP-3.2 — Submission handling and artifacts (Milestone M3) |
| Requirements | FR-AUD-01, FR-TSK-03 |
| Priority | M |
| Dependencies | MT-3.2-01 … MT-3.2-04 (resolution, artifacts, stats, scope check); MT-1.5-01 (transition registry); MT-3.1-01 (audit_required policy) |
| Parent sections | 8.2 (T7, T8, T10), 8.4, 8.5, 7.2, 9.6, 19 (WP-3.2), 20.4, 20.5 |

## Context
Section 8.2 defines the three submission-driven transitions this WP exists for. **T7**
`in_progress` → `to_be_audited` when a clean, auditable submission arrives. **T8**
`in_progress` → `in_human_review` when the coder self-flags or the patch is out of
scope, setting `review_reason` to `self_flagged` or `scope_violation` (Section 8.4
verbatim) and triggering push. **T10** `in_progress` → policy decision when
`audit_required` is false: the Policy Engine runs on coder evidence and the task
either becomes merge-pending or escalates T8-style (Section 8.5). Section 19 WP-3.2
acceptance pins two behaviors: out-of-scope patch → `in_human_review` with
`scope_violation`; self-flagged submission → review with `self_flagged`.

## Inputs / Prerequisites
* MT-3.2-01 — stored resolution (valid, one per attempt).
* MT-3.2-02 / MT-3.2-03 — patch stored, authoritative stats and changed files.
* MT-3.2-04 — scope-violation flag for the T8 guard.
* MT-3.1-01 — `audit_required_default` / per-task `audit_required` (Section 7.2).
* MT-1.5-01 — transition registry, guards, side-effect transaction machinery
  (Section 9.1: `tasks` owns all state changes).
* Section 9.6 event catalog for the events these transitions emit.

## Scope (in)
* Register and implement **T7** (actor C): guards per Section 8.2 — lease owner and
  not expired, resolution valid, `audit_required` true, not self-flagged, scope check
  ok; side effects — store resolution + patch, clear worker (including
  `claimed_role` and lease fields), write the Transition and Event rows.
* Register and implement **T8** (actors C, S): guard — `requires_human_attention`
  true OR changed files outside scope; side effects — `review_reason` =
  `self_flagged` or `scope_violation` (Section 8.4 verbatim), push-notification trigger
  per Section 9.8, Transition and Event rows written in the same transaction.
* Register and implement **T10** (actor C): guard — `audit_required` false; the
  Policy Engine runs on coder evidence (Section 8.5) and the outcome is either
  merge-pending (all rules pass) or a T8-style escalation with an enumerated review
  reason; leave a single explicit seam where WP-3.4 supplies the engine decision.
* Ordering: evaluate `requires_human_attention` and scope first — a self-flagged or
  out-of-scope submission takes T8 regardless of `audit_required`.
* Unit tests for each guard/side-effect combination, the exact Section 19 acceptance
  cases, and rejection of illegal states with `TASK_STATE_CONFLICT`.
* Add a WP changelog note.

## Out of scope
* Rule evaluation R1–R9 and the T10 engine decision itself — WP-3.4 (MT-3.4-07 fills
  the seam); until then T10's engine call is stubbed to "escalate" only via tests,
  never auto-approve (invariant 8.3.4: the Policy Engine is the only component that
  can set a policy-approved outcome).
* Auditor claim/verdict transitions T11–T14 — WP-3.3 / WP-3.4.
* Actual FCM push delivery — WP-5.4; only the Section 9.8 in-process trigger.
* Bridge evidence capture — WP-2.6.

## Target paths
* `backend/apps/tasks/` (registrations and guards for T7, T8, T10)
* `backend/tests/` (submission transition tests)
* WP changelog entry

## Acceptance criteria
- [ ] **T7** matches Section 8.2 exactly: guards (lease owner/unexpired, valid
  resolution, `audit_required` true, not self-flagged, scope ok) and side effects
  (store resolution + patch, clear worker) — task lands in `to_be_audited`
  (FR-AUD-01).
- [ ] **T8** matches Section 8.2: `requires_human_attention` or out-of-scope patch →
  `in_human_review` with `review_reason` set to `self_flagged` or `scope_violation`
  verbatim from Section 8.4; push path triggered (Section 19 WP-3.2 acceptance).
- [ ] **T10** matches Section 8.2/8.5: `audit_required` false runs the Policy Engine
  on coder evidence — approve path (merge-pending) only reachable through the engine
  seam; otherwise T8-style escalation with an enumerated reason.
- [ ] All three transitions go through the single state-machine service with
  Transition rows (actor recorded) and Event rows in one transaction
  (FR-TSK-03, FR-TSK-04).
- [ ] Illegal attempts (wrong state, non-owner) return `TASK_STATE_CONFLICT` /
  `LEASE_NOT_OWNED` from the catalog (Section 20.4 item 5).
- [ ] Events used are in the Section 9.6 catalog (Section 20.4 item 6).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k submission_transitions -q` and confirm: clean T7 to
`to_be_audited`, self-flag → `in_human_review`/`self_flagged`, out-of-scope →
`in_human_review`/`scope_violation`, T10 seam never approves without the engine, and
`TASK_STATE_CONFLICT` on illegal states; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 8.2 — Transition table (T7, T8, T10)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.4 — Review reasons (canonical enum)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.5 — Behavior when audit_required is false](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.2 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Sequencing with WP-3.4: T10 is unusable for auto-approve until the engine seam is
  filled (MT-3.4-07); ship the seam stubbed and failing-closed (escalate), never
  pass-through — the plan forbids any other approver (invariant 8.3.4).
* Push trigger must reuse the Section 9.8 dedupe key design; keep the seam narrow so
  WP-5.4 plugs in without touching T8/T10 guards.
* Self-flagged + out-of-scope combinations: plan gives no precedence between the two
  `review_reason` values — prefer `self_flagged` only when scope is clean, document
  the precedence in tests, and flag genuine ambiguity as OQ-xx.
