# MT-2.12-04 — Emit Per-Client MCP Configuration Snippets

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.12-04 |
| Title | Emit per-client MCP configuration snippets |
| Parent WP | WP-2.12 — Init command (Milestone M2) |
| Requirements | FR-MCP-08 (init outputs), FR-MCP-01 (single server entry) |
| Priority | M |
| Dependencies | MT-2.12-01 (manifest), MT-2.12-02 (token location), MT-2.12-03 (self-test verdict), MT-2.1-04 (entry points referenced by the snippets), Section 10.9 (client configuration) |
| Parent sections | 10.9 (per-client configuration), 10.11 (init outputs), 19.1 (WP-2.12 fourth slice + acceptance), 20.4, 20.5; Appendix A (`agent-guides/`) |

## Context
WP-2.12's fourth slice is "per-client configuration snippets," and the WP acceptance
— "new repo usable by agent in under 2 minutes" — ends at this step: a manifest, a
stored token and a passing self-test are useless until the user's MCP client (Claude
Code, or whatever Section 10.9's per-client configuration covers) actually launches
the bridge. Section 10.9 owns client configuration patterns (how each client registers
an MCP server); Section 10.2 names the stdio launch shape those snippets reference;
Section 10.11 lists snippets among init's outputs; Appendix A's `agent-guides/`
directory is where durable copies of this guidance live. The snippet must reference
the **stored** token's source (never inline the secret — FR-SEC-04 applies to
generated text too: a snippet pasted into a repo must not carry credentials) and the
stdby stdio entry point from MT-2.1-04, with the manifest supplying project binding.

## Inputs / Prerequisites
* MT-2.12-01 … MT-2.12-03 — manifest path, token location (source, not value),
  self-test verdict (only offer snippets when binding is proven).
* MT-2.1-04 — the entry point/command line the snippet invokes (stdio mode for
  local clients per Section 10.2).
* Parent plan Section 10.9 — per-client configuration section (the clients and
  config-file shapes to target — read it for the authoritative client list rather
  than assuming).
* Parent plan Section 10.11 — init outputs; Appendix A — `agent-guides/` as the
  documentation home; Section 10.2 — how clients launch the server.
* MT-2.12-02 — token stored user-level: snippets instruct clients to rely on that
  (env var or the bridge's config read), not to embed the token.

## Scope (in)
* Init's final step (after a passed self-test): print per-client configuration
  snippets for the clients Section 10.9 covers — for each, the MCP server
  registration block referencing the bridge's stdio entry (command + args resolved to
  the installed bridge, per Section 10.2's launch model) and whatever client-specific
  fields Section 10.9 requires (server name, working directory/repository note).
* Snippets are **copy-pasteable and secret-free**: no token, no absolute
  environment-specific path baked in where a portable reference exists (use the
  bridge's user-level config/loader; if an absolute path to the bridge binary is
  unavoidable for a client, generate it from the current install location — record
  this as generated-per-machine output, not committed content; Section 20.4 item 3
  targets committed files, and the changelog must say snippets are ephemeral
  terminal output).
* Optional durable copy: write the same guidance to `agent-guides/` **only** if a
  guide for client setup already exists there (update in place; do not invent new
  top-level docs) — otherwise terminal output only (this series' file-creation rules
  stand).
* A verification pointer in each snippet: "run the self-test / start the bridge
  under MCP inspector" referencing MT-2.12-03 and MT-2.1-04's acceptance flow, so
  the user can confirm the snippet works.
* Snippet text driven by one template per client (single source — Section 19.6),
  covered by tests asserting: contains the stdio entry, contains no token value
  (fixture token absent), mentions the config source, matches Section 10.9's field
  names for each client it targets.
* Changelog note (Section 20.4 item 7).

## Out of scope
* Installing the bridge (npm/uv/pip distribution, PATH setup) — Section 10.11
  packaging, a later WP; snippets reference the bridge as installed by whatever the
  user has, and degrade to the documented invocation form.
* Configuring the clients themselves (launching their CLIs) — user action; init
  only prints/persists text.
* HTTP-mode client configuration — WP-2.10/2.11 territory; stdio snippets only for
  M2's acceptance (note HTTP snippet deferral in the changelog if Section 10.9
  documents remote clients).
* Token distribution to clients — MT-2.12-02 already stored it user-level; clients
  never receive it directly (FR-SEC-04).
* Claude-Code-specific deep integration beyond the Section 10.9 registration block —
  no hooks/skills authored here.

## Target paths
* `bridge/` init module — snippet generation step (templates beside the init code)
* `agent-guides/` — update only if a client-setup guide already exists (Appendix A)
* `bridge/tests/` (snippet content tests: entry point present, secret-free,
  Section 10.9 field names)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] After a passing self-test, init outputs per-client MCP configuration snippets
  covering the clients Section 10.9 documents — WP-2.12 fourth slice (FR-MCP-08;
  Section 10.11).
- [ ] Every snippet launches the single MCP server entry from MT-2.1-04 (stdio mode,
  Section 10.2) — one server, per-client registration only (FR-MCP-01; Section
  19.6).
- [ ] No snippet contains a token or any secret; fixture-token assertion passes
  (FR-SEC-04; Section 20.4 item 3).
- [ ] Snippets reference the user-level config/token source rather than inlining
  credentials (Section 10.3 step 3 sourcing preserved).
- [ ] Together with MT-2.12-01 … 03, the flow completes in under 2 minutes for a new
  repo — WP-2.12 acceptance (timed run recorded in the changelog).
- [ ] Tests, lint and type check green in CI (Section 20.4 items 1–2); changelog
  note added (item 7).

## Test command
`uv run --directory bridge pytest tests/test_init_snippets.py -v` — snippet per
client contains stdio entry + Section 10.9 fields, no token, config-source
reference, self-test pointer; then the timed end-to-end: fresh repo → `orchestrator
init` → snippets printed, under 120 seconds (record result per Section 20.4 item 1).

## Attachments
* [Section 10.9 — Per-client configuration](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.11 — Init outputs](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-2.12 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Section 10.9's client list is the authority — if it names clients whose config
  format this task cannot verify locally, generate the snippet from the documented
  shape and flag unverifiable ones in the changelog rather than guessing fields.
* Snippets referencing an absolute install path are machine-specific — clearly mark
  terminal output as "for this machine" and never commit generated copies (a
  committed absolute path would violate Section 20.4 item 3's spirit even if the
  letter exempts it).
* The 2-minute acceptance depends on all four init duties; if backend latency on the
  session probe (MT-2.12-03) dominates, consider reporting snippets even on
  self-test failure-with-warnings — but only if Section 10.11's ordering permits it;
  default to the safe ordering (no snippets on failed binding) and record timing.
