# MT-2.11-02 — Verify Claude Code CLI (Reference Client) and Record Results

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.11-02 |
| Title | Verify Claude Code CLI (reference client) and record results |
| Parent WP | WP-2.11 — Client compatibility verification and conformance script (Milestone M2) |
| Requirements | NFR-08 |
| Priority | M |
| Dependencies | MT-2.11-01 (conformance runner + matrix skeleton); OQ-05 makes Claude Code CLI the first verified client |
| Parent sections | 10.9 (Claude Code CLI row), 10.2, 11.1, 18 (MCP conformance row), 19 (WP-2.11 acceptance), 20.4, 20.5; 21 (RISK-01) |

## Context
Section 10.9 names Claude Code CLI the **reference client**: STDIO transport,
prompts "Expected yes", images in tool results "Expected yes". Because it is the
reference, its verified run establishes the baseline every other client is compared
against, and WP-2.11's acceptance ("each priority client completes the coder flow end
to end; failures documented with workarounds") starts here. OQ-05 (decided) fixes the
order — Claude Code CLI first — so a blocker found here shapes how the remaining
client MTs are scheduled.

## Inputs / Prerequisites
* MT-2.11-01 — the conformance runner and the matrix skeleton at
  `docs/agent-guides/compatibility-matrix.md`.
* A local Compose stack (backend, worker, web) with a seeded project, published
  tasks and a test repository, so the coder flow can run to submission.
* Parent plan Section 10.9 — the registration/config shape for this client and the
  four matrix columns to fill.
* Parent plan Section 11.1 — the coder workflow steps to complete end to end
  (orient, list, claim, branch, checkpoint, submit).
* Parent plan Section 10.2 — STDIO launch mode the bridge exposes for local clients.
* WP-2.7-04 fallback instruction snippet and the Section 10.9 per-client config
  notes, if the run needs them.

## Scope (in)
* Register the bridge as an MCP server in Claude Code CLI per the Section 10.9
  configuration guidance (STDIO), using the stored token from `init` (MT-2.12-02
  output when available; never inline the token — FR-SEC-04).
* Run the MT-2.11-01 conformance runner under Claude Code CLI and capture the report.
* Confirm the four prompts are surfaced and invocable (Section 10.7) — recorded in
  the "Prompts surfaced" column; their syntax/UX quirks noted in Notes.
* Confirm image content blocks arrive in `read_task_attachment` results on the vision
  path (Section 10.9 expectation "Expected yes"; FR-ATT-05), on a task with an image
  attachment.
* Complete the coder workflow (Section 11.1) end to end against the real backend:
  claim → implement → checkpoint → submit, including a rules-block observation at
  claim (FR-MCP-05).
* Record results in the client's row of `docs/agent-guides/compatibility-matrix.md` —
  Transport, Prompts surfaced, Images in tool results, Notes — replacing "To verify"
  with observed facts and the client version tested.
* Document any failure with a workaround (WP-2.11 acceptance), using the WP-2.7-04
  fallback instruction snippet where prompt support is incomplete (G-08).
* Changelog note (Section 20.4 item 7).

## Out of scope
* The runner itself — MT-2.11-01.
* Other clients — MT-2.11-03 … MT-2.11-06.
* Auditor/decomposer full manual workflows — exercised by the runner's scripted
  scenarios; only the coder flow must be completed manually end to end here.
* Publishing a standalone setup guide page — MT-2.11-07 / MT-6.5-02 (this task only
  records verified facts and workarounds in the matrix).
* Fixing bridge defects found — raise as follow-up work.

## Target paths
* `docs/agent-guides/compatibility-matrix.md` (Claude Code CLI row updated with
  verified facts)
* WP changelog entry (client version, run date, failures/workarounds summary)

## Acceptance criteria
- [ ] The conformance runner completes under Claude Code CLI with all tool-contract
  checks passing, or every failure is documented with a workaround (Section 19
  WP-2.11 acceptance).
- [ ] The coder flow completes end to end: claim, checkpoint, submit accepted by the
  real backend (Section 19 WP-2.11 acceptance; Section 11.1).
- [ ] The matrix row records Transport, Prompts surfaced, Images in tool results and
  Notes as observed facts — no "To verify" left in this row (Section 10.9; Section
  20.5 traceability to NFR-08).
- [ ] Client version and bridge version recorded with the result (reproducibility).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the MT-2.11-01 conformance runner configured for Claude Code CLI and confirm
exit code 0 plus a report with all ten tools exercised; then inspect
`docs/agent-guides/compatibility-matrix.md` and verify the Claude Code CLI row has
all four columns filled with observed values.

## Attachments
* [Section 10.9 — Client compatibility matrix (Claude Code CLI row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-2.11 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 21 — RISK-01 (client differences)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Client versions move fast — record the exact Claude Code CLI version with the
  result; a later version bump silently invalidates "Expected yes" claims (RISK-01).
* Tool-approval UX and prompt surfacing are client-side behaviors the plan only
  predicts ("Expected yes") — if observation differs from expectation, the matrix
  records the fact, not the expectation; do not edit the parent plan from this task
  (raise a plan-update note instead).
* The run mutates a test repository (branches, commits) — use a disposable fixture
  repo so developer working trees stay untouched.
