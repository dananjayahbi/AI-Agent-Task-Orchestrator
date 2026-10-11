# MT-2.11-06 — Verify DeepSeek-Based Harness (Text-Only Path) and Record Results

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.11-06 |
| Title | Verify DeepSeek-based harness (text-only path) and record results |
| Parent WP | WP-2.11 — Client compatibility verification and conformance script (Milestone M2) |
| Requirements | NFR-08 |
| Priority | M |
| Dependencies | MT-2.11-01 (conformance runner + matrix skeleton), MT-2.11-02 (reference baseline), MT-2.11-05 (first text-only client recorded) |
| Parent sections | 10.2, 10.4, 10.9 (DeepSeek-based harness row), 11.1, 18 (MCP conformance row), 19 (WP-2.11 acceptance), 20.4, 20.5; 21 (RISK-01) |

## Context
Section 10.9's DeepSeek-based harness row: transport "Varies", prompts "To verify",
images "Text-only", note "Relies on OCR fallback path". This is the plan's canonical
text-only model case, the same one success criterion 3 in Section 1.4 exercises at
system level ("a task with a design screenshot is completed by a text-only model
using the OCR and description fallback"). "Harness" means the client is whatever
harness wraps the DeepSeek model — not a single named product — so the verification
records the harness configuration used, not just a version. NFR-08 is the bar: coder
flow via tools alone.

## Inputs / Prerequisites
* MT-2.11-01 — conformance runner and matrix skeleton; MT-2.11-05 — the first
  text-only client record for comparison.
* A local Compose stack with a seeded project, published tasks, a test repository and
  at least one design-screenshot attachment for the OCR/description fallback.
* Parent plan Section 10.9 — this row's expectations and the four columns to fill;
  Section 10.4 — capability negotiation for a text-only client (client capability
  table entry from MT-2.5-02 may need to name this harness — record, don't silently
  change it here).
* Parent plan Section 11.1 — coder workflow steps; Section 10.2 — transports ("Varies"
  — record which one the harness uses).
* WP-2.7-04 fallback instruction snippet (G-08) if prompts are not surfaced.

## Scope (in)
* Register the bridge in the DeepSeek-based harness using whichever transport the
  harness supports (STDIO or HTTP/SSE per Section 10.2) and record which — Section
  10.9 says "Varies".
* Run the MT-2.11-01 conformance runner through the harness and capture the report.
* Verify the text-only path end to end on a screenshot-bearing task:
  `read_task_attachment` returns OCR plus short description with the untrusted banner
  (Sections 10.4, 10.9; FR-ATT-05/06), and the coder flow can complete using that
  fallback — the Section 1.4 criterion-3 shape at client level.
* Record prompt surfacing (Section 10.7); apply the WP-2.7-04 snippet if absent and
  note its use (G-08).
* Complete the coder workflow (Section 11.1) end to end against the real backend.
* Record results in the DeepSeek-based harness row of
  `docs/agent-guides/compatibility-matrix.md` with observed facts and the harness
  configuration (harness name/version, model, transport); document failures with
  workarounds (WP-2.11 acceptance).
* If the client capability table (MT-2.5-02) lacks an entry for this harness and
  resolution needed an explicit override, record that as a follow-up for the table —
  do not edit it from this task.
* Changelog note (Section 20.4 item 7).

## Out of scope
* The runner — MT-2.11-01. Other clients — MT-2.11-03 … MT-2.11-05.
* The matrix finalization and custom-agent template — MT-2.11-07.
* Changing the bridge capability table (MT-2.5-02) or OCR engines (WP-1.12/WP-1.13).
* The full Section 1.4 criterion-3 system demo — WP-level; this is the client-level
  verification.
* Fixing bridge defects found — raise as follow-up work.

## Target paths
* `docs/agent-guides/compatibility-matrix.md` (DeepSeek-based harness row updated)
* WP changelog entry (harness configuration, transport, fallback-path result)

## Acceptance criteria
- [ ] Conformance runner completes through the harness with tool-contract checks
  passing, or failures documented with workarounds (Section 19 WP-2.11 acceptance).
- [ ] The coder flow completes end to end using the OCR/description fallback on a
  screenshot attachment (Sections 10.4, 10.9; NFR-08).
- [ ] Transport recorded as actually used for the "Varies" cell; images column
  records the text-only observation (Section 10.9).
- [ ] Harness configuration (name, version, model) recorded with the result so the
  row is reproducible (RISK-01).
- [ ] Matrix row fully filled — no "To verify" (Section 20.5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the MT-2.11-01 conformance runner configured for the DeepSeek-based harness and
confirm exit code 0 plus a report containing a passing text-only attachment check;
then verify the DeepSeek-based harness row of
`docs/agent-guides/compatibility-matrix.md` has all four columns filled with observed
facts.

## Attachments
* [Section 10.9 — Client compatibility matrix (DeepSeek-based harness row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 1.4 — Success criterion 3 (text-only fallback)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-2.11 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "DeepSeek-based harness" is a class, not a product — a result for one harness
  configuration does not generalize; the row must name the configuration tested and
  say so (RISK-01).
* If capability resolution required an explicit parameter every time, the client
  table entry (Section 10.4) is incomplete — record it as a follow-up; a run that
  only works with hand-set flags is a conditional pass, not a matrix-ready fact.
* OCR/description quality drives whether this client can actually finish
  screenshot-bearing tasks (RISK-06) — note quality issues in the matrix Notes even
  when the contract checks pass.
