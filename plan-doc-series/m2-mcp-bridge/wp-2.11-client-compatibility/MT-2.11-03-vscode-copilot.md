# MT-2.11-03 — Verify VS Code Copilot and Record Results

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.11-03 |
| Title | Verify VS Code Copilot and record results |
| Parent WP | WP-2.11 — Client compatibility verification and conformance script (Milestone M2) |
| Requirements | NFR-08 |
| Priority | M |
| Dependencies | MT-2.11-01 (conformance runner + matrix skeleton), MT-2.11-02 (reference baseline recorded) |
| Parent sections | 10.2, 10.9 (VS Code Copilot / IDE row), 11.1, 18 (MCP conformance row), 19 (WP-2.11 acceptance), 20.4, 20.5; 21 (RISK-01) |

## Context
Section 10.9's VS Code Copilot / IDE row is the most open of the priority clients:
transport "HTTP/SSE or STDIO" (to verify), prompts "To verify", images "To verify",
and the explicit note "Check tool-approval UX". It is the IDE-hosted client, so
neither transport choice nor the approval interaction is settled until measured.
WP-2.11's acceptance requires this priority client to complete the coder flow end to
end with failures documented, and NFR-08 keeps the bar honest: tools alone must
work, prompts and images are recorded enhancements.

## Inputs / Prerequisites
* MT-2.11-01 — conformance runner and matrix skeleton; MT-2.11-02 — reference
  baseline for comparison.
* A local Compose stack with a seeded project, published tasks and a test repository.
* Parent plan Section 10.9 — this row's config/notes expectations and the four
  columns to fill; Section 10.2 — both candidate transports (STDIO launch and the
  bridge's HTTP/SSE mode from WP-2.9).
* Parent plan Section 11.1 — coder workflow steps for the end-to-end run.
* Bridge HTTP/SSE server (MT-2.9-01/02) if the HTTP/SSE transport is the one chosen
  for verification.

## Scope (in)
* Register the bridge in VS Code Copilot / IDE per Section 10.9 guidance, testing
  **both** candidate transports where the client allows (STDIO and HTTP/SSE) and
  recording which one(s) work — Section 10.9 says "To verify" for transport.
* Run the MT-2.11-01 conformance runner through this client and capture the report.
* Record prompt surfacing (Section 10.7) — surfaced or not, with the invocation UX —
  and image content blocks in attachment results (FR-ATT-05) on a vision path.
* **Tool-approval UX check** (the Section 10.9 note): observe and document how the
  client presents each tool call for approval, whether approvals survive a multi-step
  coder flow, and any behavior that would stall an unattended agent (this is the
  client-specific risk RISK-01 calls out).
* Complete the coder workflow (Section 11.1) end to end against the real backend.
* Record results in the VS Code Copilot row of
  `docs/agent-guides/compatibility-matrix.md` with observed facts and the client
  version; document failures with workarounds (WP-2.11 acceptance), falling back to
  the WP-2.7-04 instruction snippet if prompts are incomplete (G-08).
* Changelog note (Section 20.4 item 7).

## Out of scope
* The runner — MT-2.11-01. Other clients — MT-2.11-04 … MT-2.11-06.
* Deciding a "supported transport" as policy — the plan leaves it open; this task
  records what works, and MT-2.11-07 consolidates the matrix.
* Editor extensions, hooks or IDE-specific integrations beyond MCP registration.
* Fixing bridge defects found — raise as follow-up work.

## Target paths
* `docs/agent-guides/compatibility-matrix.md` (VS Code Copilot row updated)
* WP changelog entry (version, transport(s) tested, approval-UX findings)

## Acceptance criteria
- [ ] Conformance runner completes through VS Code Copilot with tool-contract checks
  passing, or failures documented with workarounds (Section 19 WP-2.11 acceptance).
- [ ] The coder flow completes end to end in the IDE (Section 11.1).
- [ ] Transport column records which of STDIO / HTTP-SSE was verified (Section 10.9
  "To verify" resolved with a fact).
- [ ] The tool-approval UX note from Section 10.9 is answered: documented behavior
  plus any unattended-flow blockers (RISK-01).
- [ ] Matrix row fully filled (Transport, Prompts surfaced, Images in tool results,
  Notes) with client and bridge versions (Section 20.5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the MT-2.11-01 conformance runner configured for VS Code Copilot and confirm
exit code 0 plus a complete report; then verify the VS Code Copilot row of
`docs/agent-guides/compatibility-matrix.md` contains no "To verify" cells and the
Notes column documents the tool-approval UX observation.

## Attachments
* [Section 10.9 — Client compatibility matrix (VS Code Copilot row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-2.11 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 21 — RISK-01 (client differences)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "HTTP/SSE or STDIO" may be conditional on client version or settings — record the
  exact configuration that worked so the result is reproducible; if only one
  transport works, say so plainly rather than generalizing.
* Tool-approval UX can make the coder flow technically pass yet practically
  unusable unattended — if so, that is a documented failure with a workaround per
  WP-2.11 acceptance, not a silent pass.
* The IDE client may need the bridge reachable over HTTP/SSE from the dev machine —
  keep it on localhost/LAN per Section 15.1 (no tunnel exposure of agent endpoints
  unless remote agents are deliberately in play).
