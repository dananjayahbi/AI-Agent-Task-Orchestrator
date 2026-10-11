# MT-2.11-05 — Verify Aider and Record Results

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.11-05 |
| Title | Verify Aider and record results |
| Parent WP | WP-2.11 — Client compatibility verification and conformance script (Milestone M2) |
| Requirements | NFR-08 |
| Priority | M |
| Dependencies | MT-2.11-01 (conformance runner + matrix skeleton), MT-2.11-02 (reference baseline), MT-2.5-06 (capability negotiation tests) |
| Parent sections | 10.2, 10.4, 10.9 (Aider row), 11.1, 18 (MCP conformance row), 19 (WP-2.11 acceptance), 20.4, 20.5; 21 (RISK-01) |

## Context
Section 10.9's Aider row is hedged: transport "STDIO or wrapper", prompts "To
verify", images "Likely text-only", note "May need a documented instruction
snippet". Aider is therefore the first client expected to run the **text-only
capability path** — OCR plus description with the untrusted banner instead of image
blocks (Sections 10.4, 10.9; FR-ATT-05/06) — and possibly the fallback instruction
snippet from WP-2.7-04 (G-08). NFR-08 still defines success: the coder flow must
complete via tools alone; the prompt snippet and image path are recorded as
enhancements/workarounds, not gates.

## Inputs / Prerequisites
* MT-2.11-01 — conformance runner and matrix skeleton; MT-2.11-02 — reference
  baseline from the vision-capable client.
* MT-2.5-06 — capability negotiation tests proving the text-only packaging exists
  (the bridge side is done; this run proves it end to end through Aider).
* A local Compose stack with a seeded project, published tasks, a test repository and
  at least one image attachment (to exercise the OCR/description fallback).
* Parent plan Section 10.9 — this row's expectations and the four columns to fill;
  Section 10.4 — capability negotiation (explicit parameter, config, client table,
  default).
* Parent plan Section 11.1 — coder workflow steps; Section 10.2 — STDIO/wrapper
  launch shapes.
* WP-2.7-04 fallback instruction snippet (G-08) — expected to be needed here per the
  Section 10.9 note.

## Scope (in)
* Register the bridge in Aider using the STDIO launch, or the documented wrapper if
  STDIO registration is not natively supported — record which (Section 10.9 "STDIO
  or wrapper").
* Run the MT-2.11-01 conformance runner through Aider and capture the report.
* Verify the text-only attachment path end to end: `read_task_attachment` returns
  OCR text plus description with the untrusted banner, no image blocks (Section 10.9
  "Likely text-only"; FR-ATT-05/06) — and record what was observed rather than
  assuming the expectation.
* Record prompt surfacing (Section 10.7); if prompts are absent or not invocable,
  apply the WP-2.7-04 documented instruction snippet and confirm the flow still
  works, noting snippet usage in the matrix Notes (G-08; Section 10.9 "May need a
  documented instruction snippet").
* Complete the coder workflow (Section 11.1) end to end against the real backend.
* Record results in the Aider row of `docs/agent-guides/compatibility-matrix.md`
  with observed facts and client version; document failures with workarounds (WP-2.11
  acceptance).
* Changelog note (Section 20.4 item 7).

## Out of scope
* The runner — MT-2.11-01. Other clients — MT-2.11-03, MT-2.11-04, MT-2.11-06.
* Changing the bridge's capability table defaults — Section 10.4 resolution is
  MT-2.5-01/02 territory; this run only records behavior.
* Writing the standalone instruction snippet — WP-2.7-04 (this task consumes it).
* Fixing bridge defects found — raise as follow-up work.

## Target paths
* `docs/agent-guides/compatibility-matrix.md` (Aider row updated)
* WP changelog entry (version, transport/wrapper used, snippet usage, text-only
  observation)

## Acceptance criteria
- [ ] Conformance runner completes through Aider with tool-contract checks passing,
  or failures documented with workarounds (Section 19 WP-2.11 acceptance).
- [ ] The coder flow completes end to end via tools alone (Section 11.1; NFR-08).
- [ ] The text-only attachment path is verified and recorded: OCR/description with
  untrusted banner observed for this client (Sections 10.4, 10.9).
- [ ] Transport column records STDIO or wrapper as used; Notes records whether the
  documented instruction snippet was required (G-08; Section 10.9 note).
- [ ] Matrix row fully filled with observed facts and versions — no "To verify"
  (Section 20.5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the MT-2.11-01 conformance runner configured for Aider and confirm exit code 0
plus a complete report including the text-only attachment check; then verify the
Aider row of `docs/agent-guides/compatibility-matrix.md` has all four columns filled
and Notes states transport (STDIO or wrapper) and snippet usage.

## Attachments
* [Section 10.9 — Client compatibility matrix (Aider row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.4 — Capability negotiation](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-2.11 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "Wrapper" is undefined by the plan — if Aider needs one, document exactly what it
  wraps and keep it out of the security boundary (it must not embed tokens;
  FR-SEC-04).
* A text-only run cannot fill the "Images in tool results" column with a vision
  fact — record "text-only path verified" rather than leaving the column ambiguous,
  so MT-2.11-07 can finalize without re-running.
* If the coder flow only succeeds with the fallback snippet, that is still an NFR-08
  pass (tools alone work; the snippet is guidance) — but it must be recorded as a
  conditional workaround per WP-2.11 acceptance.
