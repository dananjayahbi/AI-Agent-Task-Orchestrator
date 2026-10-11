# MT-2.7-04 — Write per-client fallback instruction snippets (G-08)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.7-04 |
| Title | Write per-client fallback instruction snippets (G-08) |
| Parent WP | WP-2.7 — Rules injection (Milestone M2) |
| Requirements | FR-MCP-05, NFR-08 (works with each supported client; prompts/rules are enhancement-safe) |
| Priority | M |
| Dependencies | MT-2.7-01..03 (rules content and channels complete) |
| Parent sections | 10.6, 10.9, 19 (WP-2.7), 20.4, 20.5 |

## Context
Gap G-08's last sentence: "A fallback instruction snippet for each client is
documented (WP-2.7, WP-2.11)." Some clients do not surface MCP server instructions
(Section 10.9 matrix shows several "To verify"), so for those the same rules must be
injectable by other means — a short snippet the human pastes into the client's
system-prompt/instructions configuration. This slice authors those snippets from the
single rules source so a client that ignores initialize instructions still enforces
the Section 10.6 rules; WP-2.11 later verifies per-client behavior and publishes the
setup pages that embed them.

## Inputs / Prerequisites
* Parent plan gap G-08 — the fallback snippet obligation and its WP-2.7/WP-2.11
  ownership split.
* Parent plan Section 10.9 — client compatibility matrix (Claude Code CLI, VS Code
  Copilot, OpenCode, Aider, DeepSeek-based harness, custom agent) with prompt/
  instruction surfacing "To verify".
* Parent plan Section 10.6 — the rules content the snippets must carry.
* MT-2.7-01/02 — templates and merged render as the single source.
* NFR-08 — tools-alone operability; snippets are reinforcement, not a requirement
  for the tools to work.

## Scope (in)
* A per-client snippet set generated from the shared rules render (coder block as
  the base, with a variant for text-only clients noting the attachment/untrusted-data
  handling of Section 10.6 rule 6), one per Section 10.9 matrix row.
* A short "how to apply" note per client pointing at the client's instruction
  mechanism generically (the precise config syntax is WP-2.11's setup-page work —
  do not invent unverified config keys here).
* Explicit statement in each snippet file that snippets are fallback text: tools and
  claim responses remain authoritative and sufficient (NFR-08).
* A generation test: snippets contain every Section 10.6 rule and match the render
  source (no hand-maintained divergence).

## Out of scope
* Verifying which clients actually need each snippet — WP-2.11 (fills the Section
  10.9 matrix with verified facts).
* Publishing setup pages/guides — WP-2.11.
* Prompt content — WP-2.8.
* Altering the initialize/claim delivery — MT-2.7-03.

## Target paths
* `docs/agent-guides/` (per-client fallback instruction snippets)
* `bridge/src/` or `bridge/tests/` (snippet generation source/test, if generated
  from the render path)
* WP changelog entry

## Acceptance criteria
- [ ] One snippet exists for each Section 10.9 matrix client row (Claude Code CLI,
  VS Code Copilot, OpenCode, Aider, DeepSeek-based harness, custom agent).
- [ ] Each snippet carries all Section 10.6 coder rules (and the auditor variant
  where applicable), generated from or test-pinned to the MT-2.7-01 render source —
  no independent hand-retyped copy (Section 20.5).
- [ ] Snippets state they are fallbacks; tools alone remain sufficient (NFR-08).
- [ ] No client config syntax is asserted as verified — verification defers to
  WP-2.11, noted in the guides.
- [ ] Generation/consistency test passes in CI (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the snippet consistency test, e.g. `uv run pytest bridge/tests/ -k rules_snippet`;
assert every Section 10.6 rule appears in each per-client snippet and matches the
shared render output.

## Attachments
* [Gap G-08 — Rules delivery channels](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.9 — Client compatibility matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Divergence risk is highest here: pasted snippets live outside the package. Generate
  or test-pin them to the render source so rules edits propagate.
* Recording unverified per-client config syntax would create false confidence —
  keep "To verify" status visible until WP-2.11 confirms it.
