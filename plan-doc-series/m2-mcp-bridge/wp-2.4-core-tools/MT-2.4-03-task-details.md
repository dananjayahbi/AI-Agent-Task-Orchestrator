# MT-2.4-03 — Implement get_task_details with criteria, scope, feedback

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.4-03 |
| Title | Implement get_task_details with criteria, scope, feedback |
| Parent WP | WP-2.4 — Tools: availability, details, claim, release, context (Milestone M2) |
| Requirements | FR-MCP-03, FR-TSK-02 (task fields surfaced) |
| Priority | M |
| Dependencies | MT-2.4-01 (schemas), MT-2.4-02 (listing handler pattern), MT-2.3-01..04 (API client) |
| Parent sections | 9.2 (GET `/tasks/{id}`), 10.5, 19 (WP-2.4), 20.4, 20.5 |

## Context
Section 10.5 gives `get_task_details` the job of returning the full task payload for
one task: criteria, scope, test command, feedback from previous attempts, and
resolution info for auditors. This is where an agent learns what "done" means for a
task (FR-TSK-02 fields) after discovering it via `get_available_tasks`. The tool takes
only `task_id`; project scoping comes from the bound session and is enforced by the
backend token scope (FR-MCP-06).

## Inputs / Prerequisites
* Parent plan Section 9.2 — `GET /tasks/{id}` (Agent-readable for own project).
* Parent plan Section 10.5 — `get_task_details` row: inputs and included content.
* Parent plan FR-TSK-02 — the task field set (description, acceptance criteria,
  target scope, test command, priority, state, attachments, checkpoints,
  resolution).
* MT-2.4-01 — schema; MT-2.3-01..04 — API client and error translation.
* WP-2.2 — bound session.

## Scope (in)
* Handler for `get_task_details` that calls `GET /tasks/{id}` with the bound-session
  token and returns the full payload: title and markdown description, acceptance
  criteria list, target scope globs, test command, priority, state, dependency and
  lease status, attachment descriptors, and — for auditors — resolution info
  (execution summary, risk justification, patch/branch/commit references).
* Feedback from previous attempts included when the backend returns it (Section 10.5
  explicitly lists it for both roles).
* Response shaping kept structured and complete but not inflated with unrelated
  project data (tool design rule: compact and structured).
* Errors mapped via MT-2.3-04: `TASK_NOT_FOUND`, `AUTH_FORBIDDEN_PROJECT`,
  `VALIDATION_ERROR` surfaced with hint and next action.
* Unit tests: coder payload, auditor payload with resolution info, not-found and
  forbidden paths.

## Out of scope
* Fetching attachment content — WP-2.5 (`read_task_attachment`).
* Claiming, releasing — MT-2.4-04/05.
* Checkpoint history streaming — WP-2.6/WP-5.7 concerns; only what
  Section 10.5 lists is returned.
* Backend serialization and authorization logic — WP-1.x.

## Target paths
* `bridge/src/` (tool handler module)
* `bridge/tests/` (handler tests)
* WP changelog entry

## Acceptance criteria
- [ ] The response includes all Section 10.5-listed content: criteria, scope, test
  command, previous-attempt feedback, and resolution info for auditors — asserted by
  fixture tests.
- [ ] Only `task_id` is accepted; no `project_id` in schema or call
  (Section 10.3/10.5).
- [ ] `TASK_NOT_FOUND` and `AUTH_FORBIDDEN_PROJECT` surface as structured tool
  errors with code, hint and next action (Section 10.5, Section 9.2).
- [ ] Full attachment contents are never inlined — only descriptors
  (Section 10.5, WP-2.5 boundary).
- [ ] Tests pass in CI; error codes all in the Section 9.2 catalog
  (Section 20.4 items 2, 5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the handler tests, e.g. `uv run pytest bridge/tests/ -k get_task_details`;
assert criteria/scope/test-command/feedback fields present, auditor resolution info
present, and structured errors for not-found/forbidden.

## Attachments
* [Section 10.5 — Tool catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-TSK-02 — Task fields](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Resolution info exposure is role-sensitive: auditors need it, coders should not be
  handed another worker's resolution by accident — pin the behavior with the
  role-split fixture test.
* Markdown description can be large; truncating it would break agents' understanding
  of the task — if the backend ever caps it, raise an OQ-xx rather than silently
  truncating.
