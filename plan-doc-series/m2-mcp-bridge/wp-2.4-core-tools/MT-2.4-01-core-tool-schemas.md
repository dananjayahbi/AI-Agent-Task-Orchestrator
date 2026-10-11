# MT-2.4-01 — Define deterministic schemas for the five core tools

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.4-01 |
| Title | Define deterministic schemas for the five core tools |
| Parent WP | WP-2.4 — Tools: availability, details, claim, release, context (Milestone M2) |
| Requirements | FR-MCP-03, NFR-11 |
| Priority | M |
| Dependencies | WP-2.1 (bridge skeleton), WP-2.2 (session binding), MT-2.3-01..04 (API client) |
| Parent sections | 10.3, 10.5, 18 (Contract row), 19 (WP-2.4), 20.4, 20.5 |

## Context
WP-2.4's first slice defines the JSON Schemas for the five original-specification tools
kept by Section 10.5: `get_available_tasks`, `get_task_details`, `claim_task`,
`release_task`, `get_project_context`. Section 10.5 fixes their names, key inputs and
behavior; FR-MCP-03 requires deterministic schemas and structured errors. Schemas are a
public contract (Section 20.4 item 4), so they are modeled here — by pointer to
Section 10.4/10.5 rather than re-derived — before any handler code exists, keeping the
contract-test layer (Section 18) able to pin them.

## Inputs / Prerequisites
* Parent plan Section 10.5 — tool catalog table: exact tool names, key inputs,
  key behaviors and the tool design rules (no tool takes a project id; outputs are
  compact and structured; every error carries stable code, hint, next action).
* Parent plan Section 10.3 — session binding means project identity is never a tool
  argument.
* Parent plan Section 18 — Contract layer includes "MCP tool schemas".
* Section 9.2 catalog — the only error codes any tool may emit.
* WP-2.2 — bound session state the handlers will read.

## Scope (in)
* Schema definitions for the five tools with exact names from Section 10.5:
  `get_available_tasks` (`priority_filter`, `limit`, `role` — coder default),
  `get_task_details` (`task_id`), `claim_task` (`task_id`, `agent_identifier`,
  `role`), `release_task` (`task_id`, `reason`), `get_project_context` (no inputs).
* Strict input validation: unknown properties rejected, enums for `role`
  (`coder`/`auditor`) and documented filter values, `limit` bounds.
* Output descriptors: compact structured shapes — task descriptors for
  `get_available_tasks` including attachment descriptors but never full content;
  no `project_id` parameter on any tool.
* Error declarations per tool referencing only Section 9.2 codes (for example
  `claim_task`: `TASK_ALREADY_CLAIMED`, `CONCURRENCY_LIMIT_REACHED`,
  `DEPENDENCY_UNMET`, `AUDITOR_SAME_AS_CODER`, `TASK_NOT_FOUND`).
* A schema-validation test module asserting valid fixtures pass and malformed inputs
  fail with `VALIDATION_ERROR`-shaped tool errors.

## Out of scope
* Handler/transport implementation of each tool — MT-2.4-02..06.
* The five additional tools (`read_task_attachment`, `log_task_checkpoint`,
  `submit_task_resolution`, `submit_audit_verdict`, `create_draft_task`) —
  WP-2.5, WP-2.6, and their WPs.
* MCP prompts — WP-2.8.
* Publishing/diffing the schema as a versioned artifact — WP-2.11 conformance work.

## Target paths
* `bridge/src/` (tool schema definitions)
* `bridge/tests/` (schema validation tests)
* WP changelog entry

## Acceptance criteria
- [ ] All five tools exist with exact Section 10.5 names and inputs; nothing added,
  dropped, or renamed (Section 20.5 traceability).
- [ ] No schema exposes a `project_id` parameter (Section 10.3/10.5 design rule).
- [ ] Every declared error code appears in the Section 9.2 catalog
  (Section 20.4 item 5).
- [ ] Malformed inputs are rejected deterministically with a `VALIDATION_ERROR` tool
  error carrying hint and next action (FR-MCP-03, Section 10.5 rules).
- [ ] Schema-validation tests pass in CI (Section 20.4 item 2).
- [ ] Public contract noted as changed with schema diff reviewed if the schemas are
  versioned externally (Section 20.4 item 4).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the schema tests, e.g. `uv run pytest bridge/tests/ -k tool_schema`; confirm
valid fixtures for all five tools pass and out-of-contract inputs fail with
`VALIDATION_ERROR`.

## Attachments
* [Section 10.5 — Tool catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.3 — Manifest discovery and binding](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Re-typing inputs from Section 10.5 invites drift — treat the plan table as
  authoritative and diff the schemas against it line by line.
* Adding "helpful" convenience parameters (project id, owner id) would break the
  binding model; the no-`project_id` test is the guard.
