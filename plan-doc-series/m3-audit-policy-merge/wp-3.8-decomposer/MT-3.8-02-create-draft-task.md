# MT-3.8-02 — Implement the create_draft_task tool with depends_on

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.8-02 |
| Title | Implement the create_draft_task tool with depends_on |
| Parent WP | WP-3.8 — Decomposer support (Milestone M3) |
| Requirements | UC-10, G-19 |
| Priority | M |
| Dependencies | MT-3.8-01 (backend permission); WP-1.4 complete (task creation service, id sequencing); WP-2.4 complete (tool registration pattern) |
| Parent sections | 10.5 (create_draft_task), 11.3, 7.2 (Task fields), 7.3 (id generation), 8.2 (T1), 19 (WP-3.8), 20.4, 20.5 |

## Context
Section 10.5 adds the `create_draft_task` tool (gap G-19): "Decomposer creates `draft`
tasks" with inputs title, description, criteria, scope, test command, priority and
`depends_on`, and the key behavior "Role-restricted; only creates `draft`". Section
11.3 defines the workflow: the decomposer receives a high-level goal, produces draft
tasks with dependencies and scope, and stops — the Owner publishes (T2). Section 19
WP-3.8 deliverables: tool and backend permission; draft-only guarantee. MT-3.8-01
landed the permission; this task lands the tool.

## Inputs / Prerequisites
* MT-3.8-01 — decomposer permission boundary the tool runs inside.
* Parent plan Section 10.5 — exact tool inputs and behavior row (contract by pointer).
* Parent plan Section 7.2 — Task fields the inputs map to (`title`, `description`,
  `acceptance_criteria`, `target_scope`, `test_command`, `priority`, dependencies via
  `depends_on`).
* Parent plan Section 7.3 — task id allocation (project row lock, `task_counter`
  increment) reused from the existing creation service.
* WP-1.4 — existing task creation service/endpoint to call rather than a parallel one;
  WP-2.4 — tool registration, deterministic schema and error-hint conventions
  (Section 10.5 tool design rules).

## Scope (in)
* Bridge tool `create_draft_task` registered per Section 10.5 with inputs: title,
  description, criteria, scope, test command, priority, `depends_on`.
* Backend path: the tool calls the existing task-creation service as the decomposer
  role (MT-3.8-01), guaranteeing state `draft` — the tool has no publish capability
  and no state argument (draft-only guarantee).
* `depends_on` handling: referenced tasks must exist in the same project and be
  `draft`-creatable dependencies; validation rejects unknown/foreign ids with catalog
  codes (`VALIDATION_ERROR` for malformed/unknown references — no invented codes).
  Completion semantics for offering the task later remain FR-TSK-07 (claim-time), not
  this tool.
* Task id allocation through the Section 7.3 sequence (atomic, gap-tolerant) — same
  code path as owner creation.
* Structured errors with stable codes, human-readable hints and a next-action
  suggestion per Section 10.5 tool design rules.
* Tests: schema determinism, created task is `draft` with all fields stored,
  `depends_on` accepted and validated, cross-project/unknown id rejected,
  permission denial from MT-3.8-01 surfaces as a tool error.
* Add a WP changelog note.

## Out of scope
* Publishing (T2) or unpublishing — Owner only (Section 11.3; WP-1.4/web).
* Claiming anything — WP-1.6 (decomposer claim denied by MT-3.8-01).
* The MCP prompt for decomposition — WP-2.8 prompts (if any); tool only.
* Web/mobile task creation forms — WP-4.5 / FR-MOB-08.
* Dependency-unmet claim gating — FR-TSK-07 / WP-1.6.

## Target paths
* `bridge/` (create_draft_task tool registration and schema)
* `backend/apps/tasks/` (decomposer-facing creation validation for `depends_on`)
* `bridge/tests/` and `backend/tests/` (tool and validation tests)
* WP changelog entry

## Acceptance criteria
- [ ] `create_draft_task` exists with exactly the Section 10.5 inputs (title,
  description, criteria, scope, test command, priority, `depends_on`) — no project id
  argument (Section 10.5 tool design rule) (G-19; FR-MCP-03 discipline).
- [ ] Created tasks always appear as `draft` — Section 19 WP-3.8 acceptance
  "created tasks appear as `draft`"; T1 is the only transition exercised
  (Section 8.2).
- [ ] `depends_on` persists on the created tasks and validates referenced ids in the
  bound project; unknown/foreign ids rejected with a catalog code
  (Section 20.4 item 5).
- [ ] The tool is role-restricted: non-decomposer callers are rejected via
  MT-3.8-01's `ROLE_NOT_PERMITTED` path (Section 10.5 behavior column).
- [ ] Task ids allocated via the Section 7.3 sequence under the project row lock.
- [ ] Public contracts (tool schema) updated with schema diff reviewed; error codes
  all in the catalog (Section 20.4 items 4 and 5); tests green in CI; changelog note
  added (Section 20.4 items 2 and 7).

## Test command
Run the bridge/backend tool tests (`pytest backend/tests -k create_draft_task -q`
and the bridge suite for the same name) and confirm: draft-only creation, full field
mapping, `depends_on` round-trip, unknown-id rejection with a catalog code, and
permission denial; then both suites stay green.

## Attachments
* [Section 10.5 — Tool catalog (create_draft_task)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 11.3 — Decomposer workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.8 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Draft-only must be structural (no state input, service forces `draft`), not a
  validated default — a permissive default would let the tool drift toward publish
  capability, breaking Section 19 WP-3.8 acceptance.
* `depends_on` cycles among drafts are not addressed in the plan; detect and reject
  self-references at minimum, and raise OQ-xx for cycle policy rather than inventing
  a complex rule here.
