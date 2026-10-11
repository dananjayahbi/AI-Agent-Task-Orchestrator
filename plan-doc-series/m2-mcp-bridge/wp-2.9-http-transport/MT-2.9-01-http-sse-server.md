# MT-2.9-01 — Implement the local HTTP/SSE server mode

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.9-01 |
| Title | Implement the local HTTP/SSE server mode |
| Parent WP | WP-2.9 — HTTP/SSE transport with per-connection binding (Milestone M2) |
| Requirements | FR-MCP-01 (STDIO and SSE/HTTP transports from one codebase) |
| Priority | M |
| Dependencies | WP-2.1 (bridge skeleton, STDIO mode), WP-2.2 (manifest/session binding), WP-2.4 (tools served over transport) |
| Parent sections | 10.1, 10.2, 19 (WP-2.9), 20.4, 20.5 |

## Context
Section 10.2 defines the HTTP/SSE run mode: a long-running local process serving MCP
over HTTP with SSE, used by VS Code/Copilot and networked or Dockerized agents — the
second transport FR-MCP-01 requires from the same codebase as STDIO. Section 10.1
lists "speak MCP to agents (STDIO and HTTP/SSE)" as the bridge's first
responsibility. This slice stands up the server shell: bind a local address, speak
the MCP protocol over HTTP/SSE, and reuse the existing tool/session machinery —
project binding per connection arrives in MT-2.9-02.

## Inputs / Prerequisites
* Parent plan Section 10.2 — run modes table: HTTP/SSE (local service), long-running
  local process; binding source is per-connection (filled in by MT-2.9-02).
* Parent plan Section 10.1 — responsibilities: one codebase, both transports.
* Parent plan Section 10.9 — clients that may use HTTP/SSE (VS Code/Copilot row:
  "HTTP/SSE or STDIO — To verify").
* WP-2.1 — existing STDIO server entry point and tool dispatch to reuse.
* WP-2.2/WP-2.4 — session binding and tools that the served protocol exposes.

## Scope (in)
* A long-running local service entry point in the bridge package: configurable
  listen address/port with documented defaults (Section 9.10), serving the MCP
  message stream over HTTP with SSE for server-to-client messages, per Section 10.2.
* Reuse of the same tool registry, schemas (WP-2.4), prompts (WP-2.8) and error
  translation (WP-2.3) as STDIO — one codebase, two transports (FR-MCP-01).
* Graceful startup/shutdown lifecycle: clean log line with bound address, orderly
  shutdown that ends sessions (Section 10.10 best-effort release applies where a
  session existed).
* Health/liveness endpoint for the local service so operators and tests can confirm
  it is up (mirrors Section 9.2 ops discipline; local-only).
* Unit/integration tests: server starts on an ephemeral port, completes an MCP
  initialize handshake over HTTP/SSE, dispatches a tool call, and shuts down cleanly.

## Out of scope
* Per-connection project binding from URL and token — MT-2.9-02.
* Connection lifecycle limits and eviction — MT-2.9-03.
* Cross-project isolation testing — MT-2.9-04.
* STDIO mode changes — WP-2.1.
* Merge Executor mode (third run mode) — its own WP per Section 10.2.
* Public exposure/tunnels — Section 15 (this service is local; remote access is
  Cloudflare's WP-5.1 concern).

## Target paths
* `bridge/src/` (HTTP/SSE server entry point)
* `bridge/tests/` (server integration tests)
* WP changelog entry

## Acceptance criteria
- [ ] The service starts as a long-running local process, listens on a documented
  default address, and logs its bound address (Section 10.2 run mode).
- [ ] An MCP initialize handshake and at least one tool call succeed over HTTP/SSE,
  served by the same tool registry as STDIO (FR-MCP-01, Section 10.1).
- [ ] Graceful shutdown completes without tracebacks and ends open sessions
  best-effort (Section 10.10).
- [ ] Listen configuration has documented defaults and no hard-coded
  environment-specific values (Section 9.10, Section 20.4 item 3).
- [ ] Tests pass in CI (Section 20.4 item 2); error codes used are Section 9.2
  catalog codes (item 5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the transport tests, e.g. `uv run pytest bridge/tests/ -k http_server`; confirm
initialize handshake, one tool dispatch, health endpoint, and clean shutdown on an
ephemeral port.

## Attachments
* [Section 10.2 — Run modes](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.1 — Bridge responsibilities](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Binding beyond loopback without intent would expose the bridge on the LAN —
  default to local-only binding and document any wider bind as an explicit opt-in
  (Section 12.4 accepts local HTTP only for LAN development, documented risk).
* Divergent behavior between STDIO and HTTP/SSE paths is the classic drift risk of
  dual transports; keep dispatch shared and cover both in tests.
