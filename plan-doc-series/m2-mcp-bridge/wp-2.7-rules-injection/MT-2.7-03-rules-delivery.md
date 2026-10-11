# MT-2.7-03 — Deliver rules through initialize instructions and claim responses

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.7-03 |
| Title | Deliver rules through initialize instructions and claim responses |
| Parent WP | WP-2.7 — Rules injection (Milestone M2) |
| Requirements | FR-MCP-05 |
| Priority | M |
| Dependencies | MT-2.7-01 (templates), MT-2.7-02 (merged output), MT-2.4-04 (claim handler to wire), WP-2.1 (server initialize handshake) |
| Parent sections | 10.6, 19 (WP-2.7), 20.4, 20.5 |

## Context
WP-2.7's acceptance criterion: "rules appear in claim response and initialize
instructions; project rules appended correctly." Gap G-08 fixes the channels the MCP
protocol actually supports: server `instructions` at initialize, tool descriptions,
and a mandatory `rules` block in the `claim_task` response. This slice wires the
merged rules text (MT-2.7-02's single render path) into two of those channels — the
initialize-time server instructions and the claim response field — leaving tool
descriptions to WP-2.4's schema work and per-client fallback snippets to MT-2.7-04.

## Inputs / Prerequisites
* Parent plan gap G-08 — the three delivery channels and the mandatory claim `rules`
  block.
* Parent plan Section 10.6 — rules block delivered on connect and on every claim.
* Parent plan Section 9.3 step 6 — claim returns task details, lease and rules block.
* MT-2.7-01/02 — templates and merged render output.
* MT-2.4-04 — claim handler with the awaiting `rules` field; WP-2.1 — MCP server
  initialize handshake.
* Session state — bound project and cached context from WP-2.2.

## Scope (in)
* Initialize-time delivery: populate the MCP server `instructions` field of the
  initialize response with the merged rules for the session's role context (coder
  template by default at connect; the plan delivers rules on connect — use the
  standard block, since role is chosen at claim time).
* Claim-time delivery: fill the `rules` block of every `claim_task` response with
  the merged render for the claiming role (coder or auditor), reflecting that
  claim's task test command and lease-derived checkpoint interval.
* Consistency: both channels draw from the single MT-2.7-02 render path so the text
  cannot diverge.
* Tests: initialize response contains the coder rules and appended project rules;
  claim responses contain role-appropriate rules (coder vs auditor) with correct
  parameters; repeated claims re-deliver fresh lease-derived intervals.

## Out of scope
* Tool descriptions as a rules channel — WP-2.4 (schema/description text; note the
  dependency in the changelog if descriptions do not yet summarize rules).
* Per-client fallback instruction snippets — MT-2.7-04.
* Prompt-based workflows — WP-2.8.
* Backend delivery of rules — the bridge is the delivery mechanism (Section 10.6).

## Target paths
* `bridge/src/` (initialize instructions wiring; claim response wiring)
* `bridge/tests/` (delivery tests)
* WP changelog entry

## Acceptance criteria
- [ ] The initialize response's server instructions contain the Section 10.6 rules
  plus appended project rules (WP-2.7 acceptance).
- [ ] Every `claim_task` response contains a `rules` block for the claiming role —
  coder eight-rule block or auditor obligations — with task- and lease-parameterized
  values (Section 10.6, G-08).
- [ ] Project rules are appended after standard rules in both channels, identically
  (WP-2.7 acceptance; single render path).
- [ ] Both channels produce byte-identical merged text for the same role/session
  inputs, asserted by test.
- [ ] Tests pass in CI (Section 20.4 item 2); no codes involved beyond the catalog
  on error paths (item 5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the delivery tests, e.g. `uv run pytest bridge/tests/ -k rules_delivery`;
assert initialize instructions and claim-response rules both contain merged coder
and auditor rules with correct parameters.

## Attachments
* [Section 10.6 — Rules block](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Gap G-08 — Rules delivery channels](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Not every client surfaces server instructions; that is exactly why G-08 keeps the
  claim response mandatory and MT-2.7-04 provides fallback snippets — do not treat
  initialize instructions as sufficient alone.
* Initialize instructions are fixed for the session while claims are per-claim; if
  role-specific rules were expected at connect, that contradicts the plan's flow —
  role is only known at claim time, so connect-time delivery uses the coder default.
