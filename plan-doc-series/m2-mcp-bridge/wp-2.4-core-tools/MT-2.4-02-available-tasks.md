# MT-2.4-02 — Implement get_available_tasks with role parameter and filters

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.4-02 |
| Title | Implement get_available_tasks with role parameter and filters |
| Parent WP | WP-2.4 — Tools: availability, details, claim, release, context (Milestone M2) |
| Requirements | FR-MCP-03, FR-LEA-01 |
| Priority | M |
| Dependencies | MT-2.4-01 (schemas), MT-2.3-01..04 (API client), WP-2.2 (bound session) |
| Parent sections | 9.2 (GET `/projects/{pid}/work`), 10.5, 19 (WP-2.4), 20.4, 20.5 |

## Context
`get_available_tasks` is the agent's discovery tool: Section 10.5 gives it the
`role` parameter (coder default, `auditor`), `priority_filter` and `limit`, with
role-scoped visibility — coders see `pending`, unblocked tasks; auditors see
`to_be_audited`. It calls the backend's `GET /projects/{pid}/work` with the role and
filters (Section 9.2), where the project comes from the bound session, never from the
arguments. Responses are compact descriptors including attachment descriptors —
never full content (content is fetched on demand via `read_task_attachment`, WP-2.5).

## Inputs / Prerequisites
* Parent plan Section 9.2 — `GET /projects/{pid}/work` (available tasks, `role`,
  filters), caller: Agent.
* Parent plan Section 10.5 — tool row for `get_available_tasks` and tool design rules.
* Parent plan Section 8.2 (state machine) — `pending` and `to_be_audited` as the
  role-relevant states.
* MT-2.4-01 — schema and validation for this tool.
* MT-2.3-01..04 — API client with auth, retries and error translation.
* WP-2.2 — cached bound project id for the request path.

## Scope (in)
* Handler for `get_available_tasks` that resolves the project from the session,
  forwards `role`, `priority_filter` and `limit` to `GET /projects/{pid}/work`, and
  shapes the response into compact task descriptors (id, title, priority, state,
  dependency status, attachment descriptors with `ATTACHMENT_NOT_READY` status when
  processing, no attachment content).
* Default `role` of `coder`; explicit `auditor` accepted; other values rejected with
  `VALIDATION_ERROR` (schema from MT-2.4-01).
* Backend errors translated through MT-2.3-04 (for example `AUTH_FORBIDDEN_PROJECT`,
  `VALIDATION_ERROR`, `ROLE_NOT_PERMITTED`) with hint and next action preserved.
* Unit tests with a mocked backend for: coder view, auditor view, empty result,
  filters applied, and error passthrough.

## Out of scope
* Full task payload (criteria, scope, feedback) — `get_task_details`, MT-2.4-03.
* Claiming — MT-2.4-04.
* Attachment content reads — WP-2.5.
* Backend filtering/pagination implementation — WP-1.x agent-work endpoint.
* Cursor pagination exposure beyond the `limit` input defined in Section 10.5 — do
  not invent extra inputs; raise an OQ-xx if overflow paging is needed.

## Target paths
* `bridge/src/` (tool handler module)
* `bridge/tests/` (handler tests)
* WP changelog entry

## Acceptance criteria
- [ ] Coder sessions receive only `pending`, unblocked tasks; auditor sessions only
  `to_be_audited` — asserted by tests against the Section 10.5 role rules.
- [ ] `role` defaults to `coder`; invalid role values fail with `VALIDATION_ERROR`
  and a hint/next action (Section 10.5 error rule, Section 9.2 catalog).
- [ ] The response contains compact descriptors including attachment descriptors and
  never attachment content (Section 10.5).
- [ ] The project id comes from the bound session; the tool schema exposes no
  `project_id` (Section 10.3).
- [ ] Tests pass in CI; no codes outside the Section 9.2 catalog are used
  (Section 20.4 items 2 and 5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the handler tests, e.g. `uv run pytest bridge/tests/ -k get_available_tasks`;
assert role-filtered results, default role, and structured errors for invalid input.

## Attachments
* [Section 10.5 — Tool catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — REST API surface](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Role visibility is an authorization concern, not just UX: the backend enforces it,
  but the bridge must not weaken it by filtering client-side only — tests must pin
  both layers' contract via the mocked backend responses.
* Descriptor bloat (embedding checkpoint history or criteria) would defeat the
  "cheap listing" intent; keep outputs to the descriptor fields Section 10.5 implies.
