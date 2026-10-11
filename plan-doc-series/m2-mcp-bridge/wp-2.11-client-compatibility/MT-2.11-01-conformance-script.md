# MT-2.11-01 — Build the MCP Conformance Script Exercising All Tools and Prompts

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.11-01 |
| Title | Build the MCP conformance script exercising all tools and prompts |
| Parent WP | WP-2.11 — Client compatibility verification and conformance script (Milestone M2) |
| Requirements | NFR-08, FR-MCP-03, FR-MCP-04, FR-MCP-05 |
| Priority | M |
| Dependencies | MT-2.4-07, MT-2.5-06, MT-2.6-04, MT-2.7-03, MT-2.8-04, MT-2.9-04 (WP-2.4 through WP-2.9 complete: all tools, attachment tool, checkpoint/submit, rules delivery, prompts, transports) |
| Parent sections | 10.5, 10.6, 10.7, 10.9, 11.1–11.3, 18 (MCP conformance row), 19 (WP-2.11 first slice), 20.4, 20.5; Appendix A (`bridge/tests/`) |

## Context
Section 19 (WP-2.11) lists "script" as the first slice and makes the conformance
script a deliverable; Section 18's MCP conformance row defines what it must be: a
scripted client that exercises all tools and prompts for coder, auditor and
decomposer, run per supported agent client, with output that feeds the Section 10.9
compatibility matrix. NFR-08 fixes the contract the script must judge against —
clients must work **via tools alone**, prompts being an enhancement — and RISK-01
(client differences in prompt support, image handling and tool-approval UX) is the
risk this whole WP retires. The script is the reusable measuring instrument; the
per-client MTs (MT-2.11-02 … 06) are the individual measurements.

## Inputs / Prerequisites
* Parent plan Section 10.5 — the ten tools and their key behavior/errors to exercise
  (`get_available_tasks` … `get_project_context`).
* Parent plan Section 10.7 — the four prompts (`orchestrator:start_work`,
  `orchestrator:checkpoint`, `orchestrator:submit_for_audit`, `orchestrator:audit`)
  and the note that logic must also work when prompts are not surfaced (NFR-08).
* Parent plan Section 10.6 — the rules block delivered on connect and on every claim
  (FR-MCP-05), a check inside the script.
* Parent plan Sections 11.1–11.3 — coder, auditor and decomposer workflows the
  scenarios follow.
* Parent plan Section 10.9 — the matrix columns each run's report must fill
  (Transport, Prompts surfaced, Images in tool results, Notes).
* Local Compose stack running (WP-0.2, WP-1.x) with a seeded project and a test
  repository so claims and submissions can complete.
* OQ-05 (decided) — verification order: Claude Code CLI first, then VS Code Copilot,
  OpenCode, Aider, DeepSeek harness; the script must be client-agnostic so that order
  is just a run sequence.

## Scope (in)
* A conformance runner under `bridge/tests/` (Appendix A: "conformance and unit
  tests") that connects to the bridge as an MCP client and drives the full tool
  catalog of Section 10.5 for each of the three roles: coder (orient → list → claim →
  details → attachment read → checkpoint → submit/release), auditor (list
  `to_be_audited` → claim → `submit_audit_verdict`), decomposer (`create_draft_task`
  only, per Section 11.3 and role restriction).
* Prompt checks for all four Section 10.7 prompts: recorded as *surfaced* or *not
  surfaced* per client — never a hard failure (NFR-08: tools alone must work).
* Rules-block check: present at initialize and in the `claim_task` response
  (FR-MCP-05), with project-specific rules from `system_prompt_rules` merged.
* Capability-aware attachment check: image content blocks on the vision path and
  OCR-plus-description text on the text-only path, always with the untrusted banner
  (Sections 10.4, 10.9; FR-ATT-05/06).
* Stable error-code checks on the scripted failure paths (e.g. double claim yields
  `TASK_ALREADY_CLAIMED`) against the Section 9.2 catalog — codes must exist in the
  catalog (Section 20.4 item 5).
* A report artifact per run, keyed to the four Section 10.9 matrix columns plus a
  pass/fail per check, so MT-2.11-02 … 06 can record results without re-deriving the
  format.
* Create the matrix skeleton `docs/agent-guides/compatibility-matrix.md`, transcribing
  the Section 10.9 rows (all six client rows, verbatim client names) with "To verify"
  cells, so later MTs fill verified facts in place; MT-2.11-07 finalizes it.
* Harness self-tests proving the script detects a deliberately broken tool response.
* Changelog note (Section 20.4 item 7).

## Out of scope
* Running the script under any real client — MT-2.11-02 … MT-2.11-06.
* The custom-agent setup template and matrix finalization — MT-2.11-07.
* Fixing bridge/backend gaps the script finds — raise them as follow-up tasks; the
  script only reports (keep this task verifiable in one session).
* Backend API test coverage (already owned by `backend/tests/` in M1).
* Merge Executor flows — the bridge-side executor is not an MCP role (Section 11.4).
* Publishing per-client setup pages beyond the matrix skeleton — WP-2.11 later slices
  and MT-6.5-02.

## Target paths
* `bridge/tests/` (conformance runner modules and harness self-tests)
* `docs/agent-guides/compatibility-matrix.md` (matrix skeleton transcribed from
  Section 10.9; rows filled by MT-2.11-02 … 06, finalized by MT-2.11-07)
* WP changelog entry

## Acceptance criteria
- [ ] The runner exercises all ten Section 10.5 tools and checks all four Section
  10.7 prompts for coder, auditor and decomposer roles — Section 18 MCP conformance
  row (FR-MCP-03, FR-MCP-04).
- [ ] Prompt absence is reported, not failed; tool-contract breakage fails the run
  (NFR-08; Section 10.9 "prompts are an enhancement").
- [ ] Rules block verified present at connect and on claim (FR-MCP-05).
- [ ] Attachment checks cover both the vision and text-only packaging with the
  untrusted banner (Sections 10.4, 10.9).
- [ ] Error-path checks assert only codes from the Section 9.2 catalog (Section 20.4
  item 5).
- [ ] The report fills the four Section 10.9 matrix columns and gives a per-check
  pass/fail, and `docs/agent-guides/compatibility-matrix.md` exists with all six
  verbatim client rows awaiting verification (Section 20.5 traceability).
- [ ] Harness self-tests, lint and type check green in CI (Section 20.4 items 1–2);
  changelog note added (item 7).

## Test command
`uv run --directory bridge pytest tests/ -k conformance -v` — harness self-tests pass
(including the broken-response detection case); then run the runner once against the
local Compose stack and confirm exit code 0, all ten tools exercised, all four
prompts recorded, and a report file whose columns match Section 10.9 exactly.

## Attachments
* [Section 10.9 — Client compatibility matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and quality strategy (MCP conformance row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-2.11 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Appendix A places conformance tests in `bridge/tests/`, but the plan does not fix
  the runner's invocation shape (standalone entry vs pytest session) — pick one,
  document it in the changelog, and keep per-client runs reproducible from that one
  documented command.
* The script needs a live backend and seeded data; if CI cannot host the full stack,
  gate the runner on the Compose-based E2E job (Section 18 runs E2E against Compose)
  rather than inventing a lighter backend stub.
* "Images in tool results" cannot be judged from a text-only harness session — the
  report must state which capability path was exercised (Section 10.4), so
  MT-2.11-02 … 06 do not record false "To verify" results.
