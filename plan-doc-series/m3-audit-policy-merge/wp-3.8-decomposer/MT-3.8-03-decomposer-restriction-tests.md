# MT-3.8-03 — Write decomposer restriction tests (cannot publish or claim)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.8-03 |
| Title | Write decomposer restriction tests (cannot publish or claim) |
| Parent WP | WP-3.8 — Decomposer support (Milestone M3) |
| Requirements | UC-10, G-19 |
| Priority | M |
| Dependencies | MT-3.8-01 (permission enforcement); MT-3.8-02 (tool surface under test) |
| Parent sections | 12.2 (authorization matrix), 8.2 (T2, T4, T11), 10.5, 19 (WP-3.8), 20.4, 20.5 |

## Context
Section 19 WP-3.8 acceptance is a behavioral statement: "decomposer cannot publish or
claim; created tasks appear as `draft`." Section 12.2's matrix enumerates every
capability the decomposer must be denied, and UC-10's role definition (create, never
execute) is only proven by tests that attempt the forbidden operations and observe
the denials. This micro-task is the test slice of the WP: a restriction suite that
locks the boundary so later refactors of claim, publish or tool registration cannot
quietly widen decomposer power.

## Inputs / Prerequisites
* MT-3.8-01 — backend permission checks and `ROLE_NOT_PERMITTED` rejections.
* MT-3.8-02 — `create_draft_task` tool surface.
* Parent plan Section 12.2 — the full Decomposer column to enumerate cases.
* Parent plan Section 8.2 — transitions the tests attempt to trigger: T2 (publish,
  Owner), T4 (claim `pending`, coder), T11 (claim `to_be_audited`, auditor).
* Canonical error codes `ROLE_NOT_PERMITTED`, `TASK_ALREADY_CLAIMED`,
  `TASK_STATE_CONFLICT` (Section 9.2 catalog).

## Scope (in)
* A restriction test suite covering, for a decomposer-role caller:
  * create draft succeeds and the row is `draft` (positive control);
  * publish (T2) denied — `ROLE_NOT_PERMITTED`;
  * unpublish (T3) denied;
  * claim `pending` (T4) denied — `ROLE_NOT_PERMITTED`;
  * claim `to_be_audited` (T11) denied — `ROLE_NOT_PERMITTED`;
  * submit resolution denied; submit audit verdict denied;
  * review decision (T15/T16 entry) denied; merge queue read/start denied per
    Section 12.2 (Decomposer: merge queue "No");
  * work listing for a decomposer reveals no claimable work (Section 10.5 roles are
    coder/auditor — decomposer has no listing role).
* Same tests exercised through both surfaces where applicable: direct API calls and
  the `create_draft_task` tool path (MT-3.8-02).
* Regression guard: owner publish, coder claim and auditor claim still succeed in the
  same suite (proving the denial is role-scoped, not globally broken).
* Coverage: every "No" cell of the Section 12.2 Decomposer column has at least one
  asserting test (traceability, Section 20.5).
* Add a WP changelog note.

## Out of scope
* Implementing or changing the permission checks — MT-3.8-01 (tests must fail if it
  regresses; do not "fix" enforcement here).
* Owner/coder/auditor feature tests beyond the regression controls.
* MCP conformance script for the decomposer — Section 12/Section 19 MCP conformance
  deliverable (WP-2.11).
* Publishing UX and review flows — WP-4.x.

## Target paths
* `backend/tests/` (decomposer restriction suite)
* `bridge/tests/` (tool-path restriction cases)
* WP changelog entry

## Acceptance criteria
- [ ] Every "No" cell of the Decomposer column in Section 12.2 has an asserting test
  (publish, unpublish, claim `pending`, claim `to_be_audited`, resolution, verdict,
  review decisions, merge queue) (Section 20.5 traceability; G-19).
- [ ] Publish attempts (T2) and claim attempts (T4, T11) by a decomposer fail with
  `ROLE_NOT_PERMITTED` from the catalog — Section 19 WP-3.8 acceptance "decomposer
  cannot publish or claim" (Section 20.4 item 5; no invented codes).
- [ ] Positive control: `create_draft_task` succeeds and the created task is
  `draft` (Section 19 WP-3.8 acceptance; Section 10.5).
- [ ] Owner/coder/auditor regression controls pass in the same run — denials are
  role-scoped.
- [ ] Both surfaces covered: API-level and tool-level denials.
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k decomposer_restriction -q` plus the bridge suite filter
`-k create_draft_task` and confirm: all Section 12.2 "No" cells asserted with catalog
codes, draft-creation positive control, and role regression controls; then the full
suites stay green.

## Attachments
* [Section 12.2 — Authorization matrix (Decomposer column)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.2 — Transitions T2, T4, T11](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.8 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* These tests are the WP's acceptance evidence — if an enforcement gap surfaces
  (e.g. an endpoint missing the permission check), fix belongs in MT-3.8-01/backend,
  not in weakening an assertion; never adjust an expected denial to make the suite
  pass.
* Section 12.2 "Create draft tasks — Yes (Could)" for Device is a separate column;
  do not let device tests inherit decomposer expectations or vice versa — keep the
  suite role-scoped to avoid false confidence.
