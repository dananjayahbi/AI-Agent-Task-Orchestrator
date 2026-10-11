# MT-2.11-07 — Publish the Custom-Agent Setup Template and Finalize the Compatibility Matrix

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.11-07 |
| Title | Publish the custom-agent setup template and finalize the compatibility matrix |
| Parent WP | WP-2.11 — Client compatibility verification and conformance script (Milestone M2) |
| Requirements | NFR-08 |
| Priority | M |
| Dependencies | MT-2.11-02, MT-2.11-03, MT-2.11-04, MT-2.11-05, MT-2.11-06 (all client rows recorded); MT-2.7-04 (fallback instruction snippets); MT-2.12-04 (per-client config snippets, if landed) |
| Parent sections | 10.9 (custom agent row, deliverable line), 10.11, 11, 17 (runbook: onboard a new agent client), 19 (WP-2.11 deliverables and acceptance), 20.4, 20.5; 21 (RISK-01) |

## Context
Section 10.9 closes with the WP's deliverable: "a conformance script and per-client
setup page (config, instruction snippet, known limits)". Its Custom agent row says
only "Either / n/a / Depends / Must pass the conformance script" — the matrix treats
custom agents as verified by process, not by a pre-recorded run. This final WP-2.11
task turns the accumulated per-client runs into the two published artifacts: setup
pages for the five named clients (Claude Code CLI, VS Code Copilot, OpenCode, Aider,
DeepSeek-based harness) plus a reusable template for any other MCP client, and a
matrix with no unresolved cells. NFR-08 is the promise the published pages must keep:
every client works via tools alone, with prompts documented as enhancements.

## Inputs / Prerequisites
* MT-2.11-02 … MT-2.11-06 — recorded facts for all five client rows (versions,
  transports, prompt/image observations, workarounds).
* MT-2.11-01 — the conformance runner that custom agents must pass, and the matrix
  skeleton.
* MT-2.7-04 — per-client fallback instruction snippets (G-08) to embed or link.
* MT-2.12-04 — init's printed per-client config snippets (Section 10.11), if WP-2.12
  has landed; otherwise link the configuration section of Section 10.9 by pointer.
* `docs/agent-guides/README.md` — the stub index created by MT-0.1-06.
* Parent plan Section 17 — the "onboard a new agent client" runbook that will point
  at these pages (content written in MT-6.5-03).

## Scope (in)
* Publish one setup page per named client under `docs/agent-guides/`, each with the
  three parts Section 19 lists — configuration (transport + registration shape),
  instruction snippet (the WP-2.7-04 fallback where applicable), known limits — built
  strictly from the recorded matrix facts plus the referenced snippets.
* Publish a **custom-agent setup template**: the same three-part structure with
  placeholders, whose verification step is "pass the MT-2.11-01 conformance script"
  (Section 10.9 Custom agent row), including the capability-negotiation note for
  text-only vs vision harnesses (Section 10.4).
* Finalize `docs/agent-guides/compatibility-matrix.md`: every cell in all six rows
  holds a verified fact or an explicit documented limit — no "To verify" remains;
  client names stay verbatim (Claude Code CLI, VS Code Copilot, OpenCode, Aider,
  DeepSeek-based harness, Custom agent); each row carries the version/configuration
  and date verified.
* Cross-link the matrix, the setup pages and the `docs/agent-guides/` index
  (MT-0.1-06) so a new user reaches the right page in one hop.
* Add a note that the Section 10.9 table in the parent plan remains the plan-level
  authority: if verified facts differ from its "Expected …" placeholders, record a
  plan-update suggestion in the changelog rather than editing the plan here.
* Changelog note (Section 20.4 item 7).

## Out of scope
* Producing the per-client verification results — MT-2.11-02 … MT-2.11-06.
* The `init` command's runtime snippet output — MT-2.12-04.
* The Section 17 "onboard a new agent client" runbook — MT-6.5-03 (links here).
* Editing the parent plan's Section 10.9 table — plan changes go through the plan
  owner, not a micro-task (Section 0 single source of truth).
* Any client not named above beyond the generic template.

## Target paths
* `docs/agent-guides/compatibility-matrix.md` (finalized: six rows, no "To verify")
* `docs/agent-guides/` (one setup page per named client + custom-agent template)
* `docs/agent-guides/README.md` (index updated with links)
* WP changelog entry (including any Section 10.9 plan-update suggestions)

## Acceptance criteria
- [ ] The matrix contains no "To verify" cells; all six rows (five named clients plus
  Custom agent) are filled with verified facts or explicitly documented limits —
  Section 19 WP-2.11 deliverable "updated matrix" (Section 20.5 traceability).
- [ ] Each of the five named clients has a setup page with configuration, instruction
  snippet (or explicit "not needed") and known limits — Section 19 WP-2.11
  deliverable "per-client setup page".
- [ ] The custom-agent template's verification step is the conformance script
  (Section 10.9 Custom agent row).
- [ ] Pages reflect recorded results only — no claim appears that a run did not
  produce (Section 20.4 item 1 discipline; RISK-01).
- [ ] Client names appear verbatim as in Section 10.9 (NFR-08 scope clarity).
- [ ] `docs/agent-guides/README.md` index links matrix, pages and template.
- [ ] Changelog note added, including any plan-update suggestions (Section 20.4
  item 7).

## Test command
Grep `docs/agent-guides/` for `To verify` (expected: zero matches in the matrix),
then confirm each of the five client names and `Custom agent` appears as a row in
`compatibility-matrix.md` and as a linked page in `docs/agent-guides/README.md`;
spot-check one setup page's config section against the Section 10.9 row it documents.

## Attachments
* [Section 10.9 — Client compatibility matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-2.11 deliverables and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 17 — Runbooks (onboard a new agent client)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Consolidation invites drift: pages must restate recorded facts, not "improve" them
  — if a page and a matrix cell disagree, the matrix (produced by the run) wins.
* A client row that only passed with a workaround must show the workaround in
  "known limits" — publishing an unconditional claim would contradict WP-2.11
  acceptance ("failures documented with workarounds").
* The parent plan's Section 10.9 "Expected yes" cells will now be stale next to the
  finalized matrix — that mismatch is intentional until the plan owner updates it;
  flag it in the changelog instead of editing the plan (Section 0).
