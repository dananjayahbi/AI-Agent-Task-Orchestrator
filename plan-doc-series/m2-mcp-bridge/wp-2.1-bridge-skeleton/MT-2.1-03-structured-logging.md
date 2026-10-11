# MT-2.1-03 — Implement Structured Logging for the Bridge

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.1-03 |
| Title | Implement structured logging for the bridge |
| Parent WP | WP-2.1 — Bridge package skeleton (Milestone M2) |
| Requirements | NFR-10 (observability), FR-SEC-01 (no credential leakage), G-07 |
| Priority | M |
| Dependencies | MT-2.1-01 (package layout), MT-2.1-02 (log level/format config), MT-0.5-02/MT-0.5-03 (error/header conventions) |
| Parent sections | 10.1 (responsibilities), 10.10 (resilience — retry/logging), 17 (observability), 19.1 (WP-2.1 third slice), 20.4, 20.5 |

## Context
WP-2.1's third slice is "logging." Section 17 fixes the global contract: JSON lines
on stdout, correlation ids propagated, `st_dev + pid + level + timestamp + component`,
no secrets or raw prompt content, debuggability without live attachment (NFR-10
"traceable through structured logs"). The bridge runs inside agent processes (stdio or
executor modes, Section 10.2), so its logging must interoperate with those hosts:
stdout JSON lines are the only channel the plan gives it (no log files of its own),
and Section 10.10's resilience behavior ("event-driven retry"; retry and stale-session
handling) depends on those logs being greppable when a remote run's logs are the only
evidence. Section 9.6/9.10-adjacent discipline about redaction applies equally here:
the bridge handles tokens (FR-SEC-01, FR-SEC-04) and attachment content (G-07) — none
of which may appear in logs.

## Inputs / Prerequisites
* MT-2.1-01 — package layout and the logging/config seams to fill.
* MT-2.1-02 — log level/format keys resolved at startup.
* Parent plan Section 17 — field schema, correlation id rules, redaction requirements.
* Parent plan Section 10.10 — retry/stale-session behaviors whose logs must correlate
  with backend logs.
* Parent plan Section 10.2 — run modes (stdio shares the agent process's stdout —
  format must not corrupt the MCP framing; this is a design constraint to respect,
  verify against the MCP SDK's logging transport).
* MT-0.5-03 — header/response conventions (for any HTTP-side logging of requests).

## Scope (in)
* A logging setup for the bridge emitting JSON lines to stdout with the Section 17
  base fields (`st_dev + pid + level + timestamp + component`) plus the bridge's own
  component tag (e.g. `bridge.<module>`), configured by MT-2.1-02's level/format keys.
* Correlation id handling: accept and propagate a correlation id from incoming MCP
  requests/environment (matching the backend's convention) so one agent action is
  traceable across bridge and backend (Section 17; NFR-10).
* Redaction enforced in one place: a serializer/filter that strips tokens,
  authorization headers, and truncates/omits attachment content and prompt text
  (Section 17 "no secrets or raw prompt content"; G-07).
* Retry/stale-session log lines per Section 10.10's expectations — one structured
  event per retry attempt and per stale-session abort, with attempt counts, so
  operations can reconstruct behavior from logs alone.
* Tests: emitted records parse as JSON and contain the base fields; redaction unit
  tests (token-looking strings, long content never leak); correlation id round-trip;
  log level filtering; changelog note (Section 20.4 item 7).

## Out of scope
* Backend observability (Section 17's app logs, metrics, alerting) — owned by
  Foundations/M1 WPs; this task only makes the bridge logs consistent with the shared
  schema.
* OpenTelemetry traces — the plan's traceability is log-based (Section 17); do not
  add a tracing SDK the plan does not specify.
* MCP protocol-level `notifications/message` logging to the client — distinct from
  stdout diagnostics; if the SDK exposes it, wiring it is out of this skeleton slice
  (record as follow-up if Section 10.4's negotiation implies it).
* Log persistence/rotation on the agent machine — host-owned; stdout only.

## Target paths
* `bridge/` logging module (Section 10.1 responsibility seam from MT-2.1-01)
* `bridge/tests/` (JSON schema, redaction, correlation, level tests)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] Bridge logs are JSON lines on stdout with the Section 17 base fields plus a
  component tag — Section 17; NFR-10 (traceable without live attachment).
- [ ] No token, authorization header, attachment content, or raw prompt text appears
  in any log record — enforced by a single redaction point with tests (Section 17;
  FR-SEC-01; G-07).
- [ ] Correlation ids propagate across bridge↔backend calls so a single agent action
  is reconstructable from both logs (Section 17).
- [ ] Retry and stale-session handling emit one structured event per occurrence with
  attempt/session context (Section 10.10).
- [ ] Stdio mode does not corrupt MCP framing (Section 10.2 constraint verified
  against the SDK's logging behavior — note the verification method in the changelog).
- [ ] Tests, lint and type check green in CI (Section 20.4 item 2); no secrets or
  environment-specific paths (item 3); changelog note added (item 7).

## Test command
`uv run --directory bridge pytest tests/test_logging.py -v` — JSON parse + base
fields, redaction cases, correlation round-trip, level filtering, retry/stale-session
event shape; `uv run --directory bridge ruff check .` green.

## Attachments
* [Section 17 — Observability and log schema](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.10 — Bridge resilience](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [NFR-10 — Debuggability](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* stdio run mode shares stdout with MCP framing (Section 10.2): if the SDK routes
  protocol messages through stdout, interleaved diagnostics could break the transport
  — verify against the MCP Python SDK's logging behavior before enabling info-level
  stdio logging; if conflict exists, default stdio logging to stderr-with-JSON or
  SDK-mediated logging and record the deviation from "stdout" as a risk note with a
  new OQ (`OQ-15+`) rather than guessing.
* Redaction by regex over token-shaped strings is heuristic — pair it with the
  structural rule that the token value is never a log field (config redaction from
  MT-2.1-02) so safety does not depend on pattern coverage alone.
* Correlation-id formats differ between the backend (Section 17) and MCP request
  ids — establish explicitly which field carries which id to avoid interleaving two
  id spaces in one log line.
