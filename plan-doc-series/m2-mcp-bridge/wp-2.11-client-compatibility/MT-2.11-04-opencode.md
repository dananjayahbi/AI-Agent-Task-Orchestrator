# MT-2.11-04 — Verify OpenCode and Record Results

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.11-04 |
| Title | Verify OpenCode and record results |
| Parent WP | WP-2.11 — Client compatibility verification and conformance script (Milestone M2) |
| Requirements | NFR-08 |
| Priority | M |
| Dependencies | MT-2.11-01 (conformance runner + matrix skeleton), MT-2.11-02 (reference baseline) |
| Parent sections | 10.2, 10.9 (OpenCode row), 11.1, 18 (MCP conformance row), 19 (WP-2.11 acceptance), 20.4, 20.5; 21 (RISK-01) |

## Context
Section 10.9's OpenCode row expects STDIO transport with prompts and images "To
verify". OpenCode is the third client in the OQ-05 verification order and a plain
local CLI client, so this run mostly tests whether the bridge's STDIO launch model
(Section 10.2) and tool contract translate to a client the plan does not control.
WP-2.11 acceptance: priority client completes the coder flow end to end; failures
documented with workarounds. NFR-08 remains the standard — tools alone must work.

## Inputs / Prerequisites
* MT-2.11-01 — conformance runner and matrix skeleton; MT-2.11-02 — reference
  baseline.
* A local Compose stack with a seeded project, published tasks and a test repository.
* Parent plan Section 10.9 — this row's expectations and the four columns to fill;
  Section 10.2 — STDIO launch shape.
* Parent plan Section 11.1 — coder workflow steps for the end-to-end run.
* WP-2.7-04 fallback instruction snippet (G-08) if prompt support turns out
  incomplete.

## Scope (in)
* Register the bridge as an MCP server in OpenCode per Section 10.9 guidance
  (STDIO), using the stored token — never inlined (FR-SEC-04).
* Run the MT-2.11-01 conformance runner through OpenCode and capture the report.
* Record prompt surfacing (Section 10.7's four prompts) and image content blocks in
  attachment results (FR-ATT-05) on a vision path, as observed facts in the
  "Prompts surfaced" and "Images in tool results" columns.
* Complete the coder workflow (Section 11.1) end to end against the real backend,
  observing the rules block at claim (FR-MCP-05).
* Record results in the OpenCode row of
  `docs/agent-guides/compatibility-matrix.md` with observed facts and client version;
  document failures with workarounds (WP-2.11 acceptance), applying the fallback
  instruction snippet where prompts are incomplete (G-08).
* Changelog note (Section 20.4 item 7).

## Out of scope
* The runner — MT-2.11-01. Other clients — MT-2.11-03, MT-2.11-05, MT-2.11-06.
* The custom-agent template and matrix finalization — MT-2.11-07.
* OpenCode-specific features beyond MCP registration and the conformance/coder flows.
* Fixing bridge defects found — raise as follow-up work.

## Target paths
* `docs/agent-guides/compatibility-matrix.md` (OpenCode row updated)
* WP changelog entry (version, run date, failures/workarounds summary)

## Acceptance criteria
- [ ] Conformance runner completes through OpenCode with tool-contract checks
  passing, or failures documented with workarounds (Section 19 WP-2.11 acceptance).
- [ ] The coder flow completes end to end (Section 11.1).
- [ ] Matrix row fully filled — Transport, Prompts surfaced, Images in tool results,
  Notes — with no "To verify" left (Section 10.9; Section 20.5).
- [ ] Client and bridge versions recorded with the result (reproducibility).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the MT-2.11-01 conformance runner configured for OpenCode and confirm exit code
0 plus a complete report; then verify the OpenCode row of
`docs/agent-guides/compatibility-matrix.md` contains observed facts in all four
columns.

## Attachments
* [Section 10.9 — Client compatibility matrix (OpenCode row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-2.11 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 21 — RISK-01 (client differences)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* If OpenCode's MCP support differs by version, the row is only valid for the
  recorded version — state it explicitly (RISK-01).
* STDIO launch differences (working directory, env passing) can break manifest
  discovery (Section 10.3) before any tool runs — if binding fails, record it as a
  transport/config failure with the exact invocation that worked, not as a tool
  failure.
