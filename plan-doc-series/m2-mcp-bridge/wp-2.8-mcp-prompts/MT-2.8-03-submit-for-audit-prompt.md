# MT-2.8-03 — Implement prompt orchestrator:submit_for_audit

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.8-03 |
| Title | Implement prompt orchestrator:submit_for_audit |
| Parent WP | WP-2.8 — MCP prompts (Milestone M2) |
| Requirements | FR-MCP-04, NFR-08 |
| Priority | M |
| Dependencies | WP-2.6 complete (MT-2.6-02 branch/sha verification, MT-2.6-03 patch capture, MT-2.6-04 resolution upload); MT-2.8-01, MT-2.8-02 |
| Parent sections | 10.7 (Prompts), 10.5 (tool catalog), 10.6 (rules 3 and 4), 11.1 (steps 6–7), 8.2 (T7, T8), 19 (WP-2.8), 20.4, 20.5 |

## Context
Section 10.7 defines `orchestrator:submit_for_audit` as "Run verification, summarize,
submit." It is the closing move of the coder workflow (Section 11.1 steps 6–7): commit,
run the task's test command with a real exit code (rules 3–4, Section 10.6), submit the
resolution with an honest risk flag, and stop on `LEASE_EXPIRED` or
`TASK_STATE_CONFLICT` rather than continuing blindly. The submission itself lands the
task in `to_be_audited` (T7) or `in_human_review` (T8) — outcomes owned by WP-2.6 and
WP-3.2, never re-derived in the prompt.

## Inputs / Prerequisites
* Parent plan Section 10.7 — the exact three-part behavior.
* Parent plan Section 10.5 — `submit_task_resolution` inputs (`task_id`, `git_branch`,
  `commit_sha`, `execution_summary`, `requires_human_attention`, `risk_justification`)
  and outcome states `to_be_audited` / `in_human_review`.
* Parent plan Section 10.6 rules 3 and 4 — run the test command with real exit codes;
  commit before submission and provide the commit sha.
* Parent plan Section 11.1 steps 6–7 — honest risk flag; stop-and-reorient on errors.
* WP-2.6 — the bridge-side verification (branch exists, sha matches) and patch capture
  the prompt relies on.

## Scope (in)
* A registered prompt definition named exactly `orchestrator:submit_for_audit`, listed
  by `prompts/list` with its guidance text.
* Text walking the three Section 10.7 behaviors: run the task's `test_command` and
  record real exit codes, write a concise execution summary, then submit via
  `submit_task_resolution` with the committed branch and sha and an honest
  `requires_human_attention` / `risk_justification` (Section 11.1 step 6).
* Text stating that outcome state (`to_be_audited` or `in_human_review`) is decided by
  the backend, and that `LEASE_EXPIRED` / `TASK_STATE_CONFLICT` means stop and
  re-orient (Section 11.1 step 7).
* Only existing tools and canonical error codes referenced (Sections 10.5, 9.2).
* A test asserting the prompt is listed and rendered text contains all three steps.
* A WP changelog note.

## Out of scope
* The other three prompts — MT-2.8-01, MT-2.8-02, MT-2.8-04.
* Implementing submission, patch capture, or scope checks — WP-2.6 / WP-3.2.
* Policy Engine decisions on the submission — Section 9.4 (WP-3.4).
* Auditor-side behavior — MT-2.8-04.

## Target paths
* `bridge/` (prompt definitions module for `prompts/list`)
* `bridge/` tests (prompt listing and render tests)
* WP changelog entry

## Acceptance criteria
- [ ] `prompts/list` returns a prompt named exactly `orchestrator:submit_for_audit`
  (Section 19 WP-2.8 deliverable).
- [ ] The rendered text contains the three Section 10.7 behaviors in order: run
  verification, summarize, submit.
- [ ] The text instructs committing before submission with the commit sha and an honest
  risk flag (Sections 10.6 rules 3–4, 11.1 step 6) and does not promise any particular
  outcome state (T7/T8 remain backend decisions).
- [ ] Only tools and error codes from Sections 10.5 / 9.2 are named (Sections 20.4
  item 5, 20.5).
- [ ] The workflow works without the prompt (NFR-08, ADR-011).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `uv run pytest bridge/tests/ -k prompts` and assert `prompts/list` contains
`orchestrator:submit_for_audit` whose rendered text includes verification, summary and
submission steps plus the stop-on-conflict instruction; render check in an MCP inspector
(Section 19 WP-2.8 acceptance); the full bridge suite stays green.

## Attachments
* [Section 10.7 — Prompts](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 11.1 — Coder workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The prompt must not encourage hiding problems: `requires_human_attention` and
  `risk_justification` guidance stays "honest" per Section 11.1 — an over-optimistic
  prompt weakens T8 escalations.
* Outcome wording must match Section 8.2 exactly (T7 → `to_be_audited`, T8 →
  `in_human_review`); re-check against the transition table if WP-3.2 evolves.
