# MT-2.9-02 — Implement per-connection project binding from URL path and token

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.9-02 |
| Title | Implement per-connection project binding from URL path and token |
| Parent WP | WP-2.9 — HTTP/SSE transport with per-connection binding (Milestone M2) |
| Requirements | FR-MCP-06 (reject cross-project requests locally; backend token scoping as second barrier), FR-MCP-02 |
| Priority | M |
| Dependencies | MT-2.9-01 (server mode), WP-2.2 (session binding, token loading, mismatch abort), WP-2.3 (API client) |
| Parent sections | 10.2, 10.3, 19 (WP-2.9), 20.4, 20.5 |

## Context
Section 10.2 gives HTTP/SSE its distinct binding source: "Per-connection: project id
in URL path plus project-scoped token" — unlike STDIO, where the working directory
binds one session per process, one HTTP server hosts many connections, each bound to
its own project. Section 10.3 step 4's rule still applies per connection: the backend
verifies the token's project equals the requested project, and a mismatch aborts —
here, aborts that connection. FR-MCP-06 requires local rejection of any cross-project
request as the first barrier, with the backend token scoping as the second. WP-2.9's
acceptance — two simultaneous connections for different projects never share state —
rests on this slice.

## Inputs / Prerequisites
* Parent plan Section 10.2 — HTTP/SSE binding source: project id in URL path plus
  project-scoped token.
* Parent plan Section 10.3 — manifest discovery, token loading, session open,
  project-mismatch abort, cached project context; no tool takes a project id.
* Parent plan FR-MCP-06 — two-barrier cross-project rejection.
* MT-2.9-01 — server accepting connections; WP-2.2 — binding machinery to reuse per
  connection; WP-2.3 — API client for session open and context fetch.
* Section 9.2 codes: `AUTH_REQUIRED`, `AUTH_FORBIDDEN_PROJECT`, `VALIDATION_ERROR`.

## Scope (in)
* URL-path parsing extracting the project id per connection and validating its form
  before any backend call (malformed id → connection-level `VALIDATION_ERROR`
  rejection).
* Per-connection session open: load the presented project-scoped token, open the
  backend session, and enforce that token project equals URL project — on mismatch,
  reject the connection with a clear error and no session state (Section 10.3 step 4
  semantics).
* Connection-scoped state isolation: session, cached project context, and any
  per-connection capability settings live on the connection object — never in
  process-global mutable state (the root cause the isolation test guards against).
* Missing/invalid token → `AUTH_REQUIRED`; token for another project →
  `AUTH_FORBIDDEN_PROJECT`, each with hint and next action per Section 10.5 error
  rules where surfaced to the client.
* Unit tests: valid binding, malformed project id, missing token, mismatched
  token/URL project, and two connections with distinct contexts not overlapping.

## Out of scope
* The server transport itself — MT-2.9-01.
* Connection count limits and lifecycle/eviction — MT-2.9-03.
* The two-connections isolation acceptance test — MT-2.9-04.
* Manifest-based (working-directory) STDIO binding — WP-2.2.
* Backend token verification details — WP-1.x auth.
* Edge/tunnel authentication layers — WP-5.2 (ADR-006).

## Target paths
* `bridge/src/` (per-connection binding module in the HTTP/SSE server)
* `bridge/tests/` (binding tests)
* WP changelog entry

## Acceptance criteria
- [ ] Each connection resolves its project from the URL path and authenticates with
  the presented project-scoped token exactly per Section 10.2.
- [ ] Token/URL project mismatch rejects the connection before any tool runs, with a
  clear error naming the mismatch (Section 10.3 step 4, FR-MCP-06 first barrier).
- [ ] Missing or invalid credentials surface `AUTH_REQUIRED`; wrong-project
  credentials surface `AUTH_FORBIDDEN_PROJECT` (Section 9.2 catalog).
- [ ] Session and context state are per-connection; a test proves two simultaneous
  connections hold independent state objects (supports WP-2.9 acceptance).
- [ ] No tool accepts a project id — binding is transport-level only
  (Section 10.3/10.5).
- [ ] Tests pass in CI (Section 20.4 item 2); changelog note added (item 7).

## Test command
Run the binding tests, e.g. `uv run pytest bridge/tests/ -k connection_binding`;
assert valid binding succeeds, mismatch/missing-token cases reject with the catalog
codes, and two connections hold independent state.

## Attachments
* [Section 10.2 — Run modes](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.3 — Manifest discovery and binding](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The URL path is attacker-controllable input — validate before use and never let a
  path-derived project id reach the filesystem (no manifest lookup by URL; HTTP-mode
  binding uses the backend session, not repo scanning).
* Process-global caches (for example a single "current project" variable inherited
  from STDIO design) are the main cross-contamination hazard; audit WP-2.2 code for
  module-level state when wiring this.
