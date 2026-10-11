# MT-3.8-01 — Implement the decomposer role permission (draft-only)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.8-01 |
| Title | Implement the decomposer role permission (draft-only) |
| Parent WP | WP-3.8 — Decomposer support (Milestone M3) |
| Requirements | UC-10, G-19 |
| Priority | M |
| Dependencies | WP-1.4 complete (task creation service); WP-2.4 complete (tool/role plumbing) |
| Parent sections | 12.2 (authorization matrix), 10.5 (create_draft_task), 8.2 (T1), 11.3, 19 (WP-3.8), 20.4, 20.5 |

## Context
UC-10: "A high-level goal is decomposed into `draft` tasks" by the Decomposer Agent,
who creates but never executes (Section 1 role table). G-19 recorded that the spec
mentions a Decomposer with no creation tool; the fix is the role-restricted
`create_draft_task` (Section 10.5). Section 12.2's authorization matrix gives the
Decomposer exactly one capability: "Create draft tasks — Yes", with publish, claim
`pending`, claim `to_be_audited`, submit resolution and submit verdict all "No".
Section 19 WP-3.8 acceptance: "decomposer cannot publish or claim". This micro-task
implements that permission boundary on the backend before the tool itself exists.

## Inputs / Prerequisites
* Parent plan Section 12.2 — authorization matrix rows for the Decomposer column.
* Parent plan Section 10.5 — `create_draft_task` marked "Role-restricted; only
  creates `draft`".
* Parent plan Section 8.2 — T1 (create task, actors O and Decomposer) is the only
  transition a decomposer may cause.
* Parent plan Section 11.3 — decomposer workflow: produces drafts, stops; the Owner
  reviews and publishes.
* WP-1.4 — existing task-creation service and endpoint; WP-2.4 — the role
  plumbing style established by the `role` parameter.

## Scope (in)
* A decomposer role identity for agent callers (same identification mechanism the
  coder/auditor `role` intent uses — Section 10.5), validated server-side; the role
  is never trusted from an unverifiable claim (Section 12.2 is the contract).
* Backend permission enforcement:
  * decomposer may cause **T1 task creation only** (state `draft`); 
  * decomposer is rejected from publish/unpublish (T2/T3), claim `pending` (T4),
    claim `to_be_audited` (T11), submit resolution, submit verdict, review decisions
    and merge queue — every Section 12.2 "No" cell for the Decomposer column.
* Rejections return the catalog code `ROLE_NOT_PERMITTED` (or
  `TASK_STATE_CONFLICT` only where the state machine itself forbids the move for any
  caller) — no new codes.
* Tests: one per matrix cell for the Decomposer column; owner/coder/auditor paths
  unaffected (regression).
* Add a WP changelog note.

## Out of scope
* The `create_draft_task` tool schema and bridge wiring — MT-3.8-02.
* Restriction test suite for the tool path — MT-3.8-03 (this task covers backend
  permission; that task covers tool-level guarantees end-to-end).
* The Owner's publish flow (T2) — WP-1.4 / web UI WPs.
* Device (mobile) create-draft capability marked "Yes (Could)" in Section 12.2 — not
  part of the decomposer role here.

## Target paths
* `backend/apps/tasks/` (permission checks on transition/claim/submission entry points)
* `backend/apps/` (decomposer role identification/validation)
* `backend/tests/` (authorization matrix tests for the Decomposer column)
* WP changelog entry

## Acceptance criteria
- [ ] A decomposer-role caller can create tasks (T1) and nothing else — every "No"
  cell of the Decomposer column in Section 12.2 is enforced (publish, both claims,
  resolution, verdict, review, merge queue) (UC-10; G-19).
- [ ] Rejections use `ROLE_NOT_PERMITTED` from the Section 9.2 catalog where the
  matrix denies the capability (Section 20.4 item 5; no invented codes).
- [ ] Task creation by a decomposer lands in `draft` (T1 side: allocate id, emit
  `task.created`) — Section 8.2; Section 19 WP-3.8 "created tasks appear as `draft`".
- [ ] Coder, auditor and owner behavior unchanged — regression tests green
  (Section 12.2 other columns).
- [ ] Permission checks are server-side (backend), not only bridge-side (Section 12.2
  is enforced where tokens are validated).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k decomposer_permissions -q` and confirm: create-draft
allowed, publish/claim(pending)/claim(to_be_audited)/resolution/verdict/review/merge
each rejected with `ROLE_NOT_PERMITTED`, created task is `draft`, and non-decomposer
regressions pass; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 12.2 — Authorization matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — create_draft_task (role-restricted)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.8 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* How a caller becomes "decomposer" (token kind, capability field, or session role)
  is not spelled out beyond the Section 12.2 matrix and Section 10.5's
  "role-restricted" — follow the existing coder/auditor role plumbing; if no backend
  identity carries the decomposer role, raise OQ-xx instead of trusting a free-text
  request field.
* Section 12.2 lists decomposer create-draft "Yes" but T1's actor column says
  "O, Decomposer" — ensure the T1 registration from WP-1.5 accepts the decomposer
  actor without widening owner-only transitions elsewhere.
