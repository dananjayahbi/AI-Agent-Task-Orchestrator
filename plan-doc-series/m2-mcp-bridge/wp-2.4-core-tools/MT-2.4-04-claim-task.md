# MT-2.4-04 — Implement claim_task returning lease, rules block, branch name

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.4-04 |
| Title | Implement claim_task returning lease, rules block, branch name |
| Parent WP | WP-2.4 — Tools: availability, details, claim, release, context (Milestone M2) |
| Requirements | FR-MCP-03, FR-LEA-01 (atomic claim; exactly one claimant wins) |
| Priority | M |
| Dependencies | MT-2.4-01 (schemas), MT-2.4-02/03 (listing and details), MT-2.3-01..04 (API client), WP-1.6 (lease and claim service), WP-2.7 (rules block content, merged in at MT-2.7-03) |
| Parent sections | 9.2 (`POST /tasks/{id}/claim`), 9.3, 10.5, 10.6, 10.8, 19 (WP-2.4), 20.4, 20.5 |

## Context
`claim_task` is the atomicity-critical tool. Section 9.3 defines the backend claim
algorithm: resolve project from token, exclusive lock with skip-locked, re-validate
state/dependencies/concurrency inside the lock, set lease fields, increment lease
generation and attempt number, commit, and return task details, lease and rules block.
Section 10.5 fixes the tool's inputs (`task_id`, `agent_identifier`, `role`), its
return content (lease, rules block, branch name) and its four specific errors:
`TASK_ALREADY_CLAIMED`, `CONCURRENCY_LIMIT_REACHED`, `DEPENDENCY_UNMET`,
`AUDITOR_SAME_AS_CODER`. The branch name follows the G-09 canonical rule
(`auto_branch_prefix` + task index, e.g. `feat/PID00007-T004`) derived by the WP-2.10
helper. WP-2.4's acceptance — two concurrent bridges claiming one task produce one
success and one `TASK_ALREADY_CLAIMED` — is proven in MT-2.4-07.

## Inputs / Prerequisites
* Parent plan Section 9.3 — claim algorithm behavioral description.
* Parent plan Section 10.5 — `claim_task` row: inputs, return content, exact errors.
* Parent plan Section 10.6 — rules block delivered on every claim (content produced
  by WP-2.7; this task wires the response field even if WP-2.7 lands later).
* Parent plan gap G-09 — canonical branch naming.
* Parent plan Section 12.2 — role matrix: coders claim `pending`, auditors claim
  `to_be_audited`.
* MT-2.4-01 schemas; MT-2.3-01..04 client; WP-1.6 claim endpoint; WP-2.10 branch
  derivation (MT-2.10-02).

## Scope (in)
* Handler for `claim_task` calling `POST /tasks/{id}/claim` with `agent_identifier`
  and `role` (default `coder`), idempotency key attached by MT-2.3-03.
* Response assembly: lease block (lease id/generation, expiry, checkpoint cadence),
  the rules block (Section 10.6 — from WP-2.7's templates when available, otherwise
  the standard block skeleton with a note to wire MT-2.7-03), and the canonical
  branch name from the WP-2.10 derivation helper.
* Exact error mapping with hint/next action: `TASK_ALREADY_CLAIMED` → re-run
  `get_available_tasks`; `CONCURRENCY_LIMIT_REACHED` → release a held task or wait;
  `DEPENDENCY_UNMET` → surface blocking task ids; `AUDITOR_SAME_AS_CODER` → claim
  with a different `agent_identifier` or reassign; `TASK_NOT_FOUND`,
  `ROLE_NOT_PERMITTED`, `LEASE_...` never fabricated here.
* Unit tests: successful claim payload shape; each named error path; default role;
  no `project_id` argument.

## Out of scope
* Backend locking and skip-locked semantics — WP-1.6 (Section 9.3 executes there).
* Rules content authoring and project rules merge — WP-2.7 (MT-2.7-01..03).
* Branch creation in the local repository — WP-2.10 / the agent's workflow via
  `orchestrator:start_work` (WP-2.8).
* Release, checkpoint, submit — MT-2.4-05, WP-2.6.
* The concurrency acceptance test itself — MT-2.4-07.

## Target paths
* `bridge/src/` (claim handler module; integration with branch-name helper)
* `bridge/tests/` (handler tests)
* WP changelog entry

## Acceptance criteria
- [ ] A successful claim returns the three Section 10.5 artifacts — lease, rules
  block, branch name — with the branch name matching G-09
  (e.g. `feat/PID00007-T004`).
- [ ] The four named claim errors surface with their exact Section 9.2 codes, each
  with a hint and next action (Section 10.5 error rule).
- [ ] `role` defaults to `coder`; auditors may claim only `to_be_audited` tasks;
  invalid combinations return `ROLE_NOT_PERMITTED` or `AUDITOR_SAME_AS_CODER`
  as appropriate (Section 12.2 matrix).
- [ ] Mutating call carries an idempotency key (MT-2.3-03, NFR-12, ADR-012).
- [ ] No `project_id` input; project resolved from the bound session/token
  (Sections 9.3 step 1 and 10.3).
- [ ] Tests pass in CI and use only catalog codes (Section 20.4 items 2, 5);
  changelog note added (item 7).

## Test command
Run the claim handler tests, e.g. `uv run pytest bridge/tests/ -k claim_task`;
assert response contains lease/rules/branch fields and each of the four named error
codes with hint and next action. Cross-reference MT-2.4-07 for the concurrent-claim
acceptance test.

## Attachments
* [Section 9.3 — Claim algorithm](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.6 — Rules block](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Claim is the highest-contention path (Section 18 concurrency layer, RISK-03): if
  the mock tests pass but MT-2.4-07's real-Postgres test fails, the defect is in
  WP-1.6, not the bridge — keep the layers separable when debugging.
* Wiring an empty rules block before WP-2.7 lands risks agents training on blanks;
  keep the "wire MT-2.7-03" note visible in code and changelog.
