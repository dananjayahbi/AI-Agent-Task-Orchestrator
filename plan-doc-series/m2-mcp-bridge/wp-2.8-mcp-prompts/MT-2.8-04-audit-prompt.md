# MT-2.8-04 — Implement prompt orchestrator:audit

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.8-04 |
| Title | Implement prompt orchestrator:audit |
| Parent WP | WP-2.8 — MCP prompts (Milestone M2) |
| Requirements | FR-MCP-04, NFR-08 |
| Priority | M |
| Dependencies | WP-2.4 complete (role-aware listing and claim); WP-2.6 complete; MT-2.8-01 to MT-2.8-03; `submit_audit_verdict` contract fixed by Section 10.5 (implementation WP-3.5) |
| Parent sections | 10.7 (Prompts), 10.5 (tool catalog), 11.2 (auditor workflow), 9.4 (Policy Engine), 12.1 (AUDITOR_SAME_AS_CODER), 19 (WP-2.8), 20.4, 20.5 |

## Context
Section 10.7 defines the fourth prompt: `orchestrator:audit` — "Auditor workflow: claim,
check out branch, run matrix, review diff vs criteria, submit verdict." It mirrors
Section 11.2: an independent session lists `to_be_audited` tasks, checks out the branch
with read-only intent, runs the project's full test and lint commands, inspects the diff
against acceptance criteria and scope, and submits a structured verdict with evidence
and confidence — while "the backend decides the outcome" (Section 9.4, ADR-009). The
auditor never edits code (Section 11.2 step 4; Section 10.8: the Git helper never
pushes, force-resets or deletes).

## Inputs / Prerequisites
* Parent plan Section 10.7 — the exact five-part behavior.
* Parent plan Section 10.5 — `get_available_tasks` with `role: auditor`,
  `claim_task` with `role: auditor` (errors `AUDITOR_SAME_AS_CODER`,
  `TASK_ALREADY_CLAIMED`), `get_task_details`, `submit_audit_verdict` (verdict enum
  `pass` / `flag_risk` / `fail`, confidence 1–5, evidence with exit codes).
* Parent plan Section 11.2 — the auditor workflow text mirrors step for step.
* Parent plan Section 9.4 / ADR-009 — the verdict is input; the Policy Engine decides.
* WP-3.5 — implements `submit_audit_verdict` and the auditor flow; this prompt is
  written against the Section 10.5 contract.

## Scope (in)
* A registered prompt definition named exactly `orchestrator:audit`, listed by
  `prompts/list` with its guidance text.
* Text walking the Section 10.7 behavior: claim a `to_be_audited` task with
  `role: auditor`, check out the branch read-only, run the full test and lint matrix,
  review the diff against acceptance criteria and `target_scope`, submit the verdict
  with honest confidence and evidence — never modifying the branch.
* Text stating the independence rule (auditor session differs from coder session;
  `AUDITOR_SAME_AS_CODER`) and that the backend's Policy Engine, not the verdict text,
  decides the outcome (Section 9.4).
* Only existing tools, verdict fields and canonical error codes referenced
  (Sections 10.5, 9.2).
* A test asserting the prompt is listed and its rendered text contains all five steps.
* A WP changelog note.

## Out of scope
* The other three prompts — MT-2.8-01 to MT-2.8-03.
* Implementing `submit_audit_verdict`, evidence validation and the auditor flow —
  WP-3.5 (this prompt integrates with it, see Risk notes).
* Policy Engine rules and verdict-driven transitions — WP-3.4 (T13/T14).
* The auditor rules block half of Section 10.6 — WP-2.7.

## Target paths
* `bridge/` (prompt definitions module for `prompts/list`)
* `bridge/` tests (prompt listing and render tests)
* WP changelog entry

## Acceptance criteria
- [ ] `prompts/list` returns a prompt named exactly `orchestrator:audit`
  (Section 19 WP-2.8 deliverable).
- [ ] The rendered text contains the five Section 10.7 steps: claim, check out branch,
  run matrix, review diff vs criteria, submit verdict.
- [ ] The text keeps the auditor read-only (never modify the branch — Sections 11.2,
  10.8) and states that the backend decides the outcome (Section 9.4, ADR-009).
- [ ] Verdict vocabulary matches the Section 10.5 schema (`pass` / `flag_risk` /
  `fail`, confidence 1–5) — nothing invented (Sections 20.4 item 5, 20.5).
- [ ] The workflow works without the prompt (NFR-08, ADR-011); prompt lists and renders
  in an MCP inspector (Section 19 WP-2.8 acceptance).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `uv run pytest bridge/tests/ -k prompts` and assert `prompts/list` contains
`orchestrator:audit` whose rendered text includes claim, read-only checkout, matrix
run, criteria review and verdict submission, with the Section 10.5 verdict vocabulary;
render check in an MCP inspector (Section 19 WP-2.8 acceptance); the full bridge suite
stays green.

## Attachments
* [Section 10.7 — Prompts](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 11.2 — Auditor workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.4 — Policy Engine](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* WP-2.8 lands before WP-3.5, so `submit_audit_verdict` may not exist yet when this
  prompt is written — the Section 10.5 contract is the stable anchor; re-verify the
  rendered text against the implemented tool schema when WP-3.5 integrates the auditor
  flow (its slice list includes "auditor rules and prompt integration").
* The prompt must not imply the verdict is final: wording stays "submit verdict";
  outcome language belongs to Section 9.4 (ADR-009) — otherwise auditors could believe
  they perform T13/T14 directly.
