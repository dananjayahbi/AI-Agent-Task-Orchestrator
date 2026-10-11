# MT-2.9-03 — Implement connection lifecycle and connection limits

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.9-03 |
| Title | Implement connection lifecycle and connection limits |
| Parent WP | WP-2.9 — HTTP/SSE transport with per-connection binding (Milestone M2) |
| Requirements | FR-MCP-01, FR-MCP-06; NFR-04 (reconnect with backoff, no lost state) |
| Priority | M |
| Dependencies | MT-2.9-01 (server), MT-2.9-02 (per-connection binding and state) |
| Parent sections | 10.2, 10.10, 19 (WP-2.9), 20.4, 20.5 |

## Context
A long-running local service hosting many connections needs explicit lifecycle
ownership: when a connection opens, what state it accrues, when it is torn down, and
how the service bounds resource use. WP-2.9's deliverables list "connection-scoped
session, connection limits." Section 10.10 governs the failure semantics — backend
unreachable produces retryable errors with backoff, and session end triggers a
best-effort `release` or leaves the lease to expire — while NFR-04 requires
reconnection to work automatically without losing state. This slice defines those
rules for the HTTP/SSE mode without changing the transport itself.

## Inputs / Prerequisites
* Parent plan Section 10.2 — long-running local service hosting per-connection
  sessions.
* Parent plan Section 10.10 — resilience semantics: retryable errors, backoff,
  best-effort release on session end, leases left to expire otherwise.
* Parent plan Section 9.9 — lease sweeper (expired leases are reclaimed backend-side;
  connection teardown may simply rely on it).
* MT-2.9-01 (server), MT-2.9-02 (connection state object to lifecycle-manage).
* WP-2.4 tools — the claim/release machinery invoked at teardown.

## Scope (in)
* Connection state machine: open → bound → active → closing → closed, with
  deterministic transitions and cleanup of the connection's session, cached context
  and subscriptions on every exit path (client disconnect, server shutdown, error).
* Bounded resources: a documented maximum concurrent connections default with a clear
  rejection (structured error, hint to close idle sessions) when exceeded; idle
  timeout closing connections that have carried no traffic for a documented interval
  (both defaults per Section 9.10 discipline).
* Best-effort session end on connection close: call the backend session-end endpoint
  (Section 9.2 `POST /agent-sessions/{id}/end`); a failed end attempt is logged and
  left to lease expiry/sweeper per Section 10.10 — never blocks shutdown.
* Reconnect friendliness: a client reconnecting after a dropped SSE stream gets a
  fresh connection binding; in-flight tool calls fail with retryable errors rather
  than hanging (NFR-04).
* Tests: lifecycle transitions, limit rejection, idle timeout (simulated clock),
  backend-down teardown path, and cleanup leaving no per-connection residue.

## Out of scope
* Server transport and handshake — MT-2.9-01.
* Binding rules (URL/token) — MT-2.9-02.
* Cross-project isolation acceptance test — MT-2.9-04.
* Backend lease sweeping — Section 9.9.
* Rate limiting and auth at the edge — WP-5.2/WP-6.x (Section 12.1).
* Event-stream resume semantics for owner/mobile SSE — Section 9.6 / WP-4.3, WP-5.5.

## Target paths
* `bridge/src/` (connection lifecycle module in the HTTP/SSE server)
* `bridge/tests/` (lifecycle and limit tests)
* WP changelog entry

## Acceptance criteria
- [ ] Every connection exit path (client disconnect, idle timeout, server shutdown,
  error) runs the same cleanup, leaving no session or context residue — asserted by
  tests (supports WP-2.9 acceptance).
- [ ] A documented maximum-connections default rejects excess connections with a
  structured error and hint; no unbounded resource growth.
- [ ] Best-effort `POST /agent-sessions/{id}/end` runs on close; failure degrades to
  logged lease expiry per Section 10.10 without blocking exit.
- [ ] Retryable-error behavior on backend outage matches MT-2.3-02 (NFR-04).
- [ ] Only Section 9.2 catalog codes appear on error paths; tests pass in CI
  (Section 20.4 items 2, 5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the lifecycle tests, e.g. `uv run pytest bridge/tests/ -k connection_lifecycle`;
assert cleanup on each exit path, limit rejection, idle timeout, and non-blocking
teardown when session-end fails.

## Attachments
* [Section 10.10 — Resilience](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.2 — Run modes](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan does not fix numeric defaults for connection caps or idle timeouts —
  choose conservative values, document them (Section 9.10), and flag them for
  review rather than presenting them as plan-specified.
* Skipping session-end on the failure path is correct per Section 10.10, but
  silently leaking sessions on the success path is not — cover both with tests.
