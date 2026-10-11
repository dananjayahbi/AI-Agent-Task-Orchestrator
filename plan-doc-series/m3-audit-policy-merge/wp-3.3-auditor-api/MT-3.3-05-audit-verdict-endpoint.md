# MT-3.3-05 — Implement the audit verdict endpoint

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.3-05 |
| Title | Implement the audit verdict endpoint |
| Parent WP | WP-3.3 — Auditor claim and verdict API (Milestone M3) |
| Requirements | FR-AUD-01, FR-AUD-02, G-03 |
| Priority | M |
| Dependencies | MT-3.3-02 (independence re-checked); MT-3.3-03 (auditor lease owner); MT-3.3-04 (report model); MT-3.2-05 (transition machinery) |
| Parent sections | 9.2 (audit-verdict endpoint), 10.5 (verdict shape), 8.2 (T13/T14 as outcome), 8.3 (invariant 4), 19 (WP-3.3), 20.4, 20.5 |

## Context
Section 9.2 exposes `POST /tasks/{id}/audit-verdict` (auditor/owner callers: the
auditor session) as the backend counterpart of the `submit_audit_verdict` tool
(Section 10.5, gap G-03). Section 10.5 fixes the payload: `task_id`, `verdict`
(`pass` / `flag_risk` / `fail`), `confidence` 1–5, `notes`, `evidence`,
`acceptance_criteria_results` — and states "Policy Engine decides final state".
Section 8.3 invariant 4 is absolute: the Policy Engine is the only component that can
set a policy-approved outcome. So this endpoint validates, authorizes and persists the
auditor's proposal (`proposed_verdict` on the Audit Report), then delegates the
outcome to the engine decision seam that MT-3.4-07 completes.

## Inputs / Prerequisites
* Parent plan Section 9.2 — `POST /tasks/{id}/audit-verdict` endpoint row.
* Parent plan Section 10.5 — auditor verdict input shape (pointer; validation detail
  belongs to WP-3.5 for the tool, but the endpoint must accept the same contract).
* MT-3.3-03 — the auditor lease whose owner may submit; MT-3.3-02 — independence
  re-checked at verdict time.
* MT-3.3-04 — Audit Report row to populate (`proposed_verdict`, evidence, confidence).
* Section 8.2 T13/T14 — the transitions the engine outcome will drive (WP-3.4).

## Scope (in)
* `POST /tasks/{id}/audit-verdict`: 
  * authorization — only the current auditor lease owner (agent token) may submit;
    non-lease callers get catalog errors (`ROLE_NOT_PERMITTED`, `LEASE_NOT_OWNED`,
    `TASK_STATE_CONFLICT` as applicable);
  * payload validation — required `task_id`, `verdict` in the 10.5 enum
    (`pass` / `flag_risk` / `fail`), `confidence` integer 1–5, `evidence` present with
    its required structure; invalid input → `VALIDATION_ERROR` with field details;
  * persistence — create the Audit Report (MT-3.3-04) with `proposed_verdict`,
    `evidence`, `confidence`, `auditor_notes`, `auditor_session_id`, `resolution_id`;
  * outcome — invoke the Policy Engine decision seam; the endpoint itself NEVER
    approves (invariant 8.3.4); engine outcome drives T13/T14 once MT-3.4-07 lands,
    with the seam failing closed (escalate) until then.
* Idempotency: a retried verdict POST for the same report does not double-apply a
  transition (Section 9.2 idempotency-key rule).
* Unit/integration tests: validation matrix, ownership enforcement, report creation,
  seam delegation (no direct state change from the endpoint), idempotent replay.
* Add a WP changelog note.

## Out of scope
* Bridge tool schema, evidence guidance text and invalid-evidence messages — WP-3.5
  (MT-3.5-01/02).
* Rule evaluation and the actual T13/T14 execution — WP-3.4 (MT-3.4-07 fills the
  seam).
* Human review decisions T15/T16 — WP-3.6.
* Owner-side verdict submission — the Section 9.2 caller column says Auditor/Owner;
  if Owner submission is exercised from web, wire it in WP-4.8, not here.

## Target paths
* `backend/apps/audit/` (verdict endpoint, engine decision seam interface)
* `backend/tests/` (verdict endpoint tests)
* WP changelog entry

## Acceptance criteria
- [ ] `POST /tasks/{id}/audit-verdict` accepts exactly the Section 10.5 contract:
  `verdict` in `pass` / `flag_risk` / `fail`, `confidence` 1–5, required `evidence`
  (FR-AUD-02; Section 10.5 pointer).
- [ ] Only the current auditor lease owner may submit; violations return catalog
  codes only (Section 9.2 catalog; Section 20.4 item 5).
- [ ] A successful submission persists an Audit Report with `proposed_verdict` and
  evidence per MT-3.3-04 / Section 7.2.
- [ ] The endpoint never moves the task to a policy-approved outcome itself — the
  decision is delegated to the Policy Engine seam (Section 8.3 invariant 4;
  Section 19 WP-3.4 "the engine never approves when any rule fails").
- [ ] Replayed idempotent requests do not double-apply transitions
  (Section 9.2 idempotency rule).
- [ ] OpenAPI updated with schema diff reviewed (Section 20.4 item 4); tests green in
  CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k audit_verdict -q` and confirm: payload validation matrix
(bad verdict, out-of-range confidence, missing evidence), lease-owner-only rejection
with catalog codes, report persisted with proposed verdict, engine seam invoked with
no direct state change, and idempotent replay; then `pytest backend/tests -q` stays
green.

## Attachments
* [Section 10.5 — Auditor verdict input shape](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — Audit endpoints](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.3 — Invariants (engine is the only approver)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Sequencing gap: until MT-3.4-07 lands, verdicts can be stored but no transition
  fires — ship the seam failing-closed (escalate to `in_human_review` with an
  enumerated reason only through the engine path, or hold and document), never an
  implicit approve; confirm the chosen interim behavior against Section 8.5/9.4 and
  raise OQ-xx if held verdicts need a visible state.
* The Section 9.2 caller column lists "Auditor / Owner" — decide whether Owner
  submission is in this endpoint's contract now or in WP-4.8; do not leave the
  authorization rule ambiguous between the two.
