# MT-2.8-01 — Implement prompt orchestrator:start_work

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.8-01 |
| Title | Implement prompt orchestrator:start_work |
| Parent WP | WP-2.8 — MCP prompts (Milestone M2) |
| Requirements | FR-MCP-04, NFR-08 |
| Priority | M |
| Dependencies | WP-2.4 complete (MT-2.4-01 to MT-2.4-06 core tools); WP-2.6 complete (checkpoint and submission tools); MT-2.10-02 (branch naming derivation) |
| Parent sections | 10.7 (Prompts), 10.5 (tool catalog), 10.8 (Git helper), 11.1 (coder workflow), 19 (WP-2.8), 20.4, 20.5 |

## Context
Section 10.7 fixes the first of the four MCP prompts: `orchestrator:start_work` "Guides
the agent: orient, list tasks, claim, create or switch to the task branch, read
requirements and attachments as needed." Section 19 WP-2.8 makes prompt definitions and
text deliverables listed through `prompts/list`, with acceptance that each prompt lists
and renders in the inspector while workflows still work from tools alone (NFR-08,
ADR-011). The prompt is guidance text over already-shipped tools — it invents no
behavior and no new contract.

## Inputs / Prerequisites
* Parent plan Section 10.7 — the exact `orchestrator:start_work` behavior chain.
* Parent plan Section 10.5 — the tools the text may reference: `get_project_context`,
  `get_available_tasks`, `claim_task`, `get_task_details`, `read_task_attachment`, plus
  their canonical error codes (`TASK_ALREADY_CLAIMED`, `CONCURRENCY_LIMIT_REACHED`,
  `DEPENDENCY_UNMET`).
* Parent plan Section 11.1 — the coder workflow the prompt mirrors (steps 1–3).
* Parent plan Section 10.8 — branch creation/switching by the Git helper (never pushes,
  force-resets or deletes).
* WP-2.4 and WP-2.6 — implemented tools whose descriptions and claim response already
  carry the same logic (Section 10.7 last paragraph).

## Scope (in)
* A registered prompt definition named exactly `orchestrator:start_work`, returned by
  `prompts/list` with its guidance text.
* Text covering the Section 10.7 chain in order: orient (project context), list tasks
  for the bound project, claim one, create or switch to the task branch using the
  branch name returned by `claim_task`, read requirements and fetch attachments only as
  needed.
* Text pointing at the rules block (Section 10.6) and the stop-and-reorient rule when
  `LEASE_EXPIRED` or `TASK_STATE_CONFLICT` appears (Section 11.1 step 7).
* Only references to tools and error codes that already exist in Sections 10.5 and 9.2
  (Section 20.4 item 5 discipline).
* A test asserting the prompt is listed and its rendered text contains each chain step.
* A WP changelog note.

## Out of scope
* The other three prompts — MT-2.8-02, MT-2.8-03, MT-2.8-04.
* Implementing or changing any tool — WP-2.4 / WP-2.6 already did.
* Per-client prompt surfacing differences — WP-2.11 conformance (Section 10.9).
* Prompt argument schemas — the plan defines none; see Risk notes.

## Target paths
* `bridge/` (prompt definitions module for `prompts/list`)
* `bridge/` tests (prompt listing and render tests)
* WP changelog entry

## Acceptance criteria
- [ ] `prompts/list` returns a prompt named exactly `orchestrator:start_work`
  (Section 19 WP-2.8 deliverable: listing through `prompts/list`).
- [ ] The rendered text walks the five Section 10.7 steps in order: orient, list tasks,
  claim, create or switch to the task branch, read requirements/attachments as needed.
- [ ] Every tool and error code named in the text exists in Sections 10.5 / 9.2 — none
  invented (Sections 20.4 item 5, 20.5).
- [ ] The text requires no prompt-only knowledge: the same workflow is achievable from
  tool descriptions and the claim response alone (Section 10.7 last paragraph, NFR-08,
  ADR-011).
- [ ] Prompt lists and renders in an MCP inspector (Section 19 WP-2.8 acceptance).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the bridge test suite filtered to prompts (for example
`uv run pytest bridge/tests/ -k prompts`), asserting `prompts/list` contains
`orchestrator:start_work` with each of the five chain steps present in the rendered
text; then verify manually in an MCP inspector that the prompt renders (Section 19
WP-2.8 acceptance); the full bridge suite stays green.

## Attachments
* [Section 10.7 — Prompts](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-2.8 MCP prompts](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* RISK-01: clients differ in prompt support — this prompt must remain a pure
  enhancement; if any step reads as mandatory, it violates ADR-011 and NFR-08.
* The plan defines no prompt arguments; do not invent any. If a target client requires
  an argument shape to surface prompts, record the question before adding one
  (Section 20.1 item 5).
* Inspector availability varies per client (Section 10.9 "to verify") — the listing
  assertion in the test suite is the authoritative check, not any one client.
