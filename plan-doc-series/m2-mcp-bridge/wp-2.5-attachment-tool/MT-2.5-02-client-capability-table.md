# MT-2.5-02 — Create the editable client capability table file

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.5-02 |
| Title | Create the editable client capability table file |
| Parent WP | WP-2.5 — Tool: `read_task_attachment` with capability negotiation (Milestone M2) |
| Requirements | FR-ATT-05 |
| Priority | M |
| Dependencies | MT-2.5-01 (resolver with the table-lookup hook) |
| Parent sections | 10.4, 10.9, 19 (WP-2.5), 20.4, 20.5 |

## Context
Section 10.4 step 3 resolves capabilities by looking up the MCP client name/version
against "a maintained capability table (editable file)". Section 10.9's client
compatibility matrix is the seed content, but most of its cells read "To verify" or
"Expected" — WP-2.11 runs the conformance script to confirm them. This task creates
the editable table file the resolver reads, seeded from Section 10.9 without
overclaiming, plus the edit procedure so WP-2.11 can update it after verification.

## Inputs / Prerequisites
* Parent plan Section 10.4 — step 3 semantics (client name/version lookup, editable
  file).
* Parent plan Section 10.9 — the compatibility matrix rows: Claude Code CLI, VS Code
  Copilot / IDE, OpenCode, Aider, DeepSeek-based harness, Custom agent, with their
  transport, prompt and image columns.
* MT-2.5-01 — resolver that consumes the table through its lookup hook.
* WP-2.11 — future consumer that verifies entries and edits the table.

## Scope (in)
* An editable capability-table file shipped with the bridge package, keyed by MCP
  client name and version (range or exact, matching what the client reports at
  startup).
* Seeding from Section 10.9: only cells verified as "yes" map to vision-capable;
  "Expected", "To verify", "Likely text-only" and "Text-only" entries stay at the
  text-safe/`unknown` default until WP-2.11 confirms them.
* Loader behavior already exercised by MT-2.5-01: file present → parsed; file absent
  or malformed → default `unknown` for every client (never a crash).
* A short editing procedure (format, key rules, how WP-2.11 records verified results)
  living next to the file.
* Unit tests for parsing (well-formed entries, unknown fields ignored safely,
  version-range matching, missing-file fallback).

## Out of scope
* The resolver's decision logic — MT-2.5-01.
* Running the conformance script or flipping entries to "verified" — WP-2.11.
* Packaging/image/text behavior downstream of the resolved capability — MT-2.5-03/04.
* Backend or web/mobile clients.

## Target paths
* `bridge/` — capability table file plus loader data
* `bridge/tests/` — table parsing tests
* WP changelog entry

## Acceptance criteria
- [ ] An editable table file exists keyed by client name/version, loaded by the
  resolver's step-3 lookup (Section 10.4).
- [ ] Every Section 10.9 client appears as an entry, with no capability marked
  verified that the plan does not state as verified (no invented facts).
- [ ] Missing or malformed file degrades to `unknown` (text-safe) for all clients
  instead of failing the bridge.
- [ ] The editing procedure documents how WP-2.11 updates entries after the
  conformance run.
- [ ] Parsing and fallback tests pass; lint/type checks green (Section 20.4 item 2);
  changelog note added (item 7).

## Test command
`uv run pytest bridge/tests/ -k capability_table -q` — assert seeded entries match
Section 10.9, unverified clients resolve text-safe, and a missing/corrupt file falls
back to `unknown`; then the full bridge suite stays green.

## Attachments
* [Section 10.9 — Client compatibility matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.4 — Capability negotiation](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Inventing capabilities: marking a "To verify" client as vision-capable would make
  the resolver hand image blocks to a text-only client — keep unverified entries at
  `unknown` and let WP-2.11's evidence (conformance output) drive edits.
* Version-key format drift between what clients report and what the table matches on
  can silently skip entries; pin the key format in the editing procedure and test it.
* The file is data, not code — editing it must not require a bridge release, but a
  bad edit must still degrade to `unknown` (loader test above).
