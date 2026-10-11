# MT-2.8-02 — Implement prompt orchestrator:checkpoint

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.8-02 |
| Title | Implement prompt orchestrator:checkpoint |
| Parent WP | WP-2.8 — MCP prompts (Milestone M2) |
| Requirements | FR-MCP-04, NFR-08 |
| Priority | M |
| Dependencies | WP-2.6 complete (MT-2.6-01 `log_task_checkpoint` with next-due hint); MT-2.8-01 (prompt registration pattern) |
| Parent sections | 10.7 (Prompts), 10.5 (tool catalog), 10.6 (rules block rule 5), 8.6 (lease extension), 11.1, 19 (WP-2.8), 20.4, 20.5 |

## Context
Section 10.7 defines `orchestrator:checkpoint` with a two-behavior contract: "Commit
current work and log a checkpoint." This is the prompt that keeps leases alive —
Section 8.6 makes each valid checkpoint extend `lease_expires_at` (up to
`lease_max_total_minutes`), and rules-block rule 5 (Section 10.6) requires a checkpoint
at least every N minutes and at each meaningful milestone. RISK-02 (agents forgetting
to checkpoint) is mitigated partly by this prompt plus the `next_checkpoint_due` hint
returned by `log_task_checkpoint` (WP-2.6).

## Inputs / Prerequisites
* Parent plan Section 10.7 — the exact two-step behavior.
* Parent plan Section 10.5 — `log_task_checkpoint` inputs (`task_id`, `message`,
  `percentage`) and its `LEASE_EXPIRED` error meaning.
* Parent plan Section 8.6 — checkpoint extends the lease; after the hard cap the owner
  must submit or release; late checkpoints from an expired owner return `LEASE_EXPIRED`.
* Parent plan Section 10.6 rule 5 — cadence expectation the text restates by reference.
* WP-2.6 — implemented checkpoint tool with the next-due hint to point at.

## Scope (in)
* A registered prompt definition named exactly `orchestrator:checkpoint`, returned by
  `prompts/list` with its guidance text.
* Text instructing the agent to commit current work first, then log a checkpoint via
  `log_task_checkpoint` with an honest message and percentage, honoring the returned
  next-due hint.
* Text restating (by pointer) the lease rules: checkpoint extends the lease only while
  the caller owns it; on `LEASE_EXPIRED` stop and re-orient instead of continuing
  (Section 11.1 step 7) — never attempt to resurrect a lost lease.
* Only existing tools and canonical error codes referenced (Sections 10.5, 9.2).
* A test asserting the prompt is listed and its rendered text contains both behaviors.
* A WP changelog note.

## Out of scope
* The other three prompts — MT-2.8-01, MT-2.8-03, MT-2.8-04.
* Implementing `log_task_checkpoint` or the next-due hint — WP-2.6.
* Liveness-mode auto-extensions (OQ-04) — off by default, not part of the prompt.
* Server-side lease sweeper behavior — WP-1.6.

## Target paths
* `bridge/` (prompt definitions module for `prompts/list`)
* `bridge/` tests (prompt listing and render tests)
* WP changelog entry

## Acceptance criteria
- [ ] `prompts/list` returns a prompt named exactly `orchestrator:checkpoint`
  (Section 19 WP-2.8 deliverable).
- [ ] The rendered text contains both Section 10.7 behaviors: commit current work, then
  log a checkpoint — in that order.
- [ ] The text points at `log_task_checkpoint` and its next-due hint, and restates the
  Section 8.6 stop-on-`LEASE_EXPIRED` rule without inventing lease semantics.
- [ ] Only tools and error codes from Sections 10.5 / 9.2 are named (Sections 20.4
  item 5, 20.5).
- [ ] The workflow works without the prompt — same guidance exists in tool description
  and rules-block rule 5 (NFR-08, ADR-011).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `uv run pytest bridge/tests/ -k prompts` and assert `prompts/list` contains
`orchestrator:checkpoint` whose rendered text includes the commit-then-log sequence and
the `LEASE_EXPIRED` stop instruction; render check in an MCP inspector
(Section 19 WP-2.8 acceptance); the full bridge suite stays green.

## Attachments
* [Section 10.7 — Prompts](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.6 — Lease semantics in detail](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Prompt cadence wording must not promise lease extension beyond
  `lease_max_total_minutes` (Section 8.6 hard cap) — the tool enforces the cap, the
  text must not contradict it.
* RISK-01: on clients that do not surface prompts, checkpoint discipline relies on
  rules-block rule 5 and the tool description; verify the three channels stay aligned.
