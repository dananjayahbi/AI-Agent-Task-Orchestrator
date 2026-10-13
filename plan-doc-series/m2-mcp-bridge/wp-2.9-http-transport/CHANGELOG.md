# WP-2.9 — HTTP/SSE transport with per-connection binding: changelog

Short notes per parent plan Section 20.4, item 7 — one entry per micro-task of
WP-2.9. All four MTs completed 2026-10-12/13 in the `bridge/` package
(`orchestrator_bridge/http_service/` plus the HTTP entry point): the exit-2
stub of WP-2.1 is replaced by the real local service — one codebase, two
transports (FR-MCP-01). Per-connection state lives only on connection
objects; the Wave 6 acceptance — two simultaneous connections for different
projects never share state — is proven by a barrier-synchronized
two-thread integration test against the real multi-connection server.

## 2026-10-12 — MT-2.9-01: The local HTTP/SSE server mode

* `entrypoints/http.py` — the exit-2 stub is gone: the entry now runs the
  real service (the mode dispatch, config layering and structured logging
  still ride the shared `entrypoints.cli` bootstrap; explicit
  `orchestrator-bridge-http` / `--mode http` / `ORCHESTRATOR_BRIDGE_MODE`
  precedence unchanged).
* `http_service/runner.py` — uvicorn lifecycle with one build path shared
  by production and tests: layered-settings listen address, one clean
  startup log line carrying the **bound** address, muted uvicorn chatter,
  bounded graceful stop (5 s drain), exit `0` on clean shutdown and exit
  `1` with one scrubbed line (no traceback) on bind failure (NFR-10).
  No manifest is consulted — HTTP binds per connection (Section 10.2).
* `http_service/app.py` — the ASGI application: `GET /health` liveness
  (status/mode/connection counters; local-only) and
  `GET|POST|DELETE /projects/{project_id}/mcp` serving MCP
  streamable-HTTP (POST = client→server, `mcp-session-id` routing, GET =
  server→client SSE). Requests ride the SDK's per-connection
  `StreamableHTTPSessionManager`; tools, schemas, rules instructions and
  error translation come from the **same** `create_server` path as stdio
  (FR-MCP-01 — asserted byte-identical in the handshake test).
* Configuration (Section 9.10): four documented defaults, no
  environment-specific values — `http_host` 127.0.0.1 (loopback-only; a
  wider bind is an explicit opt-in per Section 12.4), `http_port` 8765
  (avoids the backend's 8000; 0 = ephemeral), `http_max_connections` 16,
  `http_idle_timeout_seconds` 900 — all flagged for review as
  plan-unspecified (MT-2.9-03 risk note), wired through
  `ORCHESTRATOR_BRIDGE_HTTP_*` env keys, `.env.example` and
  `user-config.example.toml`, validated in `config.py`. `uvicorn` is a
  declared direct dependency (imported by the bridge itself).
* `tests/http_harness.py` — the WP-2.9 test harness: the production entry
  on a loopback ephemeral port with a raw streamable-HTTP JSON-RPC client
  and a fake clock; only the bridge→backend leg is the WP-2.3 send seam —
  MCP traffic crosses real sockets.
* Tests (`tests/test_http_server.py`, 5): health liveness, initialize +
  tool dispatch + clean shutdown over real HTTP/SSE, bind-failure exit
  line, mode/config wiring.

## 2026-10-12 — MT-2.9-02: Per-connection project binding from URL path and token

* `http_service/binding.py` — the first barrier, per Section 10.2:
  * the URL project id is validated against the manifest schema's
    canonical pattern (`^PID[0-9]{5}$`) **before any backend call or
    filesystem touch** — malformed → connection-level
    `VALIDATION_ERROR` (400); the URL is attacker-controllable input and
    HTTP mode has no manifest lookup at all;
  * the `Authorization: Bearer` token must be present, well-formed and
    header-safe (the stdio step-3 rule, now exported as
    `credentials.header_safe`) — else `AUTH_REQUIRED` (401) with a
    fix-oriented hint, never echoing the presented value;
  * the backend session opens **with that token** (ADR-004: no project in
    the body — the backend resolves and verifies) and the project context
    is read for the URL's project, so a token scoped elsewhere fails with
    `AUTH_FORBIDDEN_PROJECT` (403) and a best-effort
    `POST /agent-sessions/{id}/end` removes the half-opened session —
    "no session state survives a rejected connection";
  * the connection's synthetic `StartupBinding` carries only documented
    defaults (G-09's `feat/{PID}-` prefix); the token is layered into a
    frozen per-connection `Settings` copy (single redaction boundary).
* `http_service/connection.py` + `app.py` dispatch order — the two-barrier
  FR-MCP-06 contract: URL validation → token → capacity admission →
  session open (backend verification, second barrier) → established
  requests re-checked against the connection's URL project **and** its
  own token (cross-project request or foreign token → local
  `AUTH_FORBIDDEN_PROJECT`, no tool runs, no backend call for the
  requested project). Each connection owns its `ToolRuntime`, MCP server
  and session manager — nothing per-connection lives in process-global
  state. No tool accepts a project id over HTTP (test-scanned schemas).
* Tests (`tests/test_connection_binding.py`, 11): valid binding, malformed
  id before the backend, missing/wrong-scheme/unsafe tokens, other-project
  token rejected with no session state (backend `end` observed), backend
  rejected credential → `AUTH_REQUIRED`, cross-project URL refused locally,
  foreign token on an established connection, per-connection state
  independence, registration only after initialize.

## 2026-10-12 — MT-2.9-03: Connection lifecycle and connection limits

* `http_service/connection.py` — the deterministic state machine
  `open → bound → active → closing → closed` with a transition table
  (illegal transitions raise); **one** cleanup path
  (`Connection.finalize`, idempotent) every exit route shares: stop the
  session manager (bounded 5 s — teardown can log and give up, never
  hang), then best-effort session end (Section 10.10 — failures log and
  leave the lease to the sweeper), then `closed`.
* `http_service/registry.py` — the single capacity/idle authority: a
  synchronous check+reserve admission counter (interleaved handshakes
  cannot overshoot the cap on one loopback), established connections keyed
  by MCP session id (unknown id → local 404 with reconnect hint, NFR-04),
  an idle sweeper on a fixed 30 s tick that never closes a connection
  holding an open SSE stream (tests drive it with an injected clock — no
  wall-clock waits), and close-out through the same finalize path for
  client `DELETE`, idle timeout, setup failure and server shutdown.
* Capacity rejection is a Section 9.2 envelope: 503
  `CONCURRENCY_LIMIT_REACHED`, retryable, with close-idle-sessions hint
  and the config key to raise the cap.
* Tests (`tests/test_connection_lifecycle.py`, 10): synchronous
  reservation accounting, bound→active progression, structured capacity
  rejection, idle timeout closing only silent connections, failed
  handshake leaving zero state (reservation returned), client DELETE
  cleanup, shutdown finalizing open connections, backend-down teardown
  never blocking, backend outage yielding a retryable tool error
  (MT-2.3-02 semantics), reconnect getting a fresh binding.

## 2026-10-13 — MT-2.9-04: Two-connections cross-project isolation test

* `tests/test_cross_project_isolation.py` (2) — the Wave 6 acceptance
  against the **real multi-connection server** (real sockets, real
  streamable-HTTP framing; only the backend leg is the send seam):
  * `test_cross_project_isolation_two_simultaneous_connections` — two
    client threads meet on a `threading.Barrier` (genuinely concurrent,
    no sleep ordering — the MT risk note) and drive connections A
    (PID00007) and B (PID00008) through interleaved tool calls:
    `get_project_context` returns each project's own name/rules,
    `get_available_tasks` lists only its own project's work, a claim on A
    is invisible to B, session ids differ, and closing A leaves B fully
    functional; a deliberate cross-project attempt is rejected locally
    with the catalog code before any cross-project data returns
    (FR-MCP-06 first barrier).
  * `test_cross_project_isolation_backend_sessions_scoped_per_token` —
    the second barrier observed through the harness: a wrong-project
    token cannot even open the other project's context (backend
    verification), and the rejected connection leaves no session state.
* `tests/conftest.py` — additive `FakeBackend.route_dynamic` fallback for
  bridge-minted session-id paths (`.../end`); existing exact-route tests
  untouched.

## Verification-finisher pass (2026-10-13)

* The original bridge agent's outage left the WP-2.9 source complete but
  two **stub-era tests** in `tests/test_entrypoints.py` unupdated — with
  the stub gone, `cli(["--mode", "http"])` started the real server and
  hung the suite. Replaced with dispatch-contract tests (fake runner):
  `--mode http` dispatches to the service, and the stub's "not yet
  implemented" message must stay gone from the HTTP path (the executor's
  exit-2 stub remains, per WP-3.7's boundary).
* Strict-mypy and formatter passes across the WP's files (send-callable
  signature, header decode typing, harness return annotations, a live
  state read helper for the lifecycle assertions).
* `uv run ruff check .`, `ruff format --check .`, `mypy .` (strict) and
  the full bridge suite are green; live-backend opt-in tests stay
  skipped by design (a backend finisher is active).

## Open items / CI follow-ups

* **Numeric defaults flagged for review** (MT-2.9-03 risk note): the
  connection cap (16), idle timeout (900 s), sweep tick (30 s), manager
  stop budget (5 s) and uvicorn graceful-stop drain (5 s) are
  conservative helper-chosen values, not plan-specified.
* **`ORCHESTRATOR_BRIDGE_HTTP_IDLE_TIMEOUT_SECONDS` naming**: one env
  prefix (`ORCHESTRATOR_BRIDGE_HTTP_`) covers host/port/cap/timeout —
  recorded here so the configuration convention owner can confirm the
  uniform prefix (docs/plan/conventions/configuration.md).
* **Resume semantics**: event-stream resume for owner/mobile SSE is
  Section 9.6 / WP-4.3, WP-5.5 territory — this transport closes dropped
  SSE streams with a reconnect hint (NFR-04) and does not implement
  resumability.
* Local smoke evidence: HTTP mode serves on loopback with token auth and
  shuts down cleanly (recorded in the verification report alongside this
  changelog); the deep coverage is the harness suite above.
