# MT-2.1-04 — Create Entry-Point Stubs for stdio, HTTP and Executor Modes

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.1-04 |
| Title | Create entry-point stubs for stdio, HTTP and executor modes |
| Parent WP | WP-2.1 — Bridge package skeleton (Milestone M2) |
| Requirements | FR-MCP-01 (single MCP server entry) |
| Priority | M |
| Dependencies | MT-2.1-01 (package layout), MT-2.1-02 (config), MT-2.1-03 (logging), ADR-004 (MCP Python SDK) |
| Parent sections | 10.1 (transport), 10.2 (run modes), 10.11 (packaging/entry), 19.1 (WP-2.1 acceptance), 23 (ADR-004), 20.4, 20.5 |

## Context
Section 10.2 enumerates three run modes: stdio (Claude Code, `npx`-style local
invocation), streamable HTTP (remote/supabase-hosted agent scenarios), and
executor-embedded (in-process runtimes like OpenClaw). Section 10.1 makes transport
handling a bridge responsibility; Section 10.11 pins packaging to an `orchestrator`
CLI (the init-command surface, WP-2.12). WP-2.1's acceptance is the observable
milestone: "starts under MCP inspector, with an empty tool set" — i.e. the stdio
entry point exists, boots the MCP server via the ADR-004 SDK, advertises no tools
yet, and shuts down cleanly. This micro-task creates the three mode entry points as
stubs that share one server-construction path (Section 10.11's single-entry
discipline), with stdio actually runnable under the inspector and HTTP/executor
skeletons that parse config and raise a clear "not yet implemented" boundary until
their WPs land (WP-2.10 HTTP mode; executor wiring as the plan assigns).

## Inputs / Prerequisites
* MT-2.1-01 — package layout and the transport/entry-point placeholder module.
* MT-2.1-02 — config keys (mode selection, backend URL, log level) these stubs read.
* MT-2.1-03 — JSON logging active before any entry point emits diagnostics.
* Parent plan Section 10.2 — the three modes and how each is launched (stdio via the
  agent's MCP config; HTTP as a served endpoint; executor as an embedded call).
* Parent plan Section 10.11 — `orchestrator` CLI as the eventual single packaging
  surface; ADR-004 — official MCP Python SDK, single MCP server.
* MCP inspector — the Section 19.1 acceptance harness (used manually/CI as the repo
  already does; the inspector itself is not packaged).

## Scope (in)
* One shared server-construction function building the MCP server (ADR-004 SDK) with
  an empty tools registry — the single source all three entry points use
  (Section 10.11 single entry; Section 19.6 one implementation).
* **stdio entry point**: a runnable module/console invocation that starts the MCP
  server on stdio, applying MT-2.1-02 config and MT-2.1-03 logging — this is the
  surface the WP-2.1 acceptance verifies under the MCP inspector: server starts,
  handshake completes, tool list is empty, clean shutdown on stdin close.
* **streamable HTTP entry point stub**: parses config, confirms mode selection, and
  exits with a clear not-implemented message pointing at WP-2.10 (no half-built
  server); logs the attempt via MT-2.1-03.
* **executor-embedded entry point stub**: an importable callable with the same clear
  boundary for in-process runtimes (Section 10.2 third mode).
* Mode selection precedence (explicit invocation > config key > default stdio)
  documented in the example config; changelog note (item 7).

## Out of scope
* Real HTTP serving, sessions, and SSE/transport negotiation — WP-2.10 (Section 10.10
  resilience applies there).
* Executing the bridge inside a specific embedded runtime (OpenClaw etc.) — the plan
  leaves embedding details to that integration; stub only.
* Any tool registration — WP-2.4 onward (empty tool set is the acceptance here).
* The `orchestrator init` CLI command and full CLI packaging — WP-2.12 (Section
  10.11); this task may expose module entry points that WP-2.12 later wraps.
* Manifest resolution/capability negotiation/session binding — WP-2.2 / WP-2.4.

## Target paths
* `bridge/` entry-point module (transport seam from MT-2.1-01) + console-script/
  module invocation declared in `bridge/pyproject.toml`
* `bridge/tests/` (server construction: empty tool set; stub mode-selection tests)
* `bridge/` example config updated with the mode key (MT-2.1-02's file)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] The stdio entry point starts under the MCP inspector, completes the handshake,
  and reports an **empty tool set** — WP-2.1 acceptance, verbatim (FR-MCP-01;
  ADR-004 single MCP server).
- [ ] All three Section 10.2 modes have entry points sharing one server-construction
  path; HTTP and executor stubs fail fast with a clear not-implemented message
  (no partial transport) — Section 10.2; Section 19.6.
- [ ] Mode selection precedence documented in the example config and tested
  (Section 10.2).
- [ ] Startup/shutdown emit the MT-2.1-03 structured logs; config comes from
  MT-2.1-02's layered loader (no inline defaults bypassing it).
- [ ] `uv run --directory bridge ruff check .` and `uv run --directory bridge pytest
  -q` pass; inspector check recorded (Section 20.4 items 1–2).
- [ ] No secrets or environment-specific paths committed (item 3); changelog note
  added (item 7).

## Test command
`uv run --directory bridge pytest tests/test_entrypoints.py -v` — empty tool set via
the shared constructor, mode precedence, stub fail-fast messages; plus the manual/
CI inspector run for the acceptance: MCP inspector → stdio command → server lists zero
tools (record the invocation in the changelog per Section 20.4 item 1).

## Attachments
* [Section 10.2 — Bridge run modes](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.11 — Packaging and CLI entry](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-2.1 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The inspector acceptance is environment-sensitive (Node tooling + Python stdio
  process); if the inspector cannot run in CI, record the exact local command and
  result as the Section 20.4 item-1 proof and note the CI gap — do not replace the
  inspector check with an import-only test and claim acceptance.
* Section 10.2's descriptions of how each mode is launched (npx-style, HTTP URL,
  embedded) may imply wrapper scripts the plan does not enumerate; keep stubs at
  module/console level and let WP-2.11/2.12 packaging decide wrappers.
* "Not-implemented" stubs must exit with non-zero status and a message naming the
  implementing WP — a stub that silently no-ops would let an HTTP deployment appear
  healthy while serving nothing.
