# MT-2.2-04 — Open and End Agent Sessions with a Cached Project Context

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.2-04 |
| Title | Open and end agent sessions with a cached project context |
| Parent WP | WP-2.2 — Manifest discovery and session binding (Milestone M2) |
| Requirements | FR-MCP-02, FR-MCP-06 (session duration/exit), FR-SEC-01 |
| Priority | M |
| Dependencies | MT-2.2-01 (manifest), MT-2.2-02 (validated manifest), MT-2.2-03 (token), MT-1.2-03 (`POST /agent-sessions`), MT-1.3-02 (Project Context API) |
| Parent sections | 10.3 (steps 4–5), 9.2 (agent-sessions endpoints), 19.1 (WP-2.2 fourth slice), 19.3 (bridge must not duplicate backend logic), 20.4, 20.5 |

## Context
Section 10.3's steps 4–5: step 4 — "Open agent session via `POST /agent-sessions`";
step 5 — "Cache project context (name, policy summary, rules) for the session."
WP-2.2's fourth slice is "session open/end with context cache," and FR-MCP-06 bounds
the lifetime: an agent session spans bridge startup until process exit — the cache
lifetime is that same span. The endpoints exist from M1: MT-1.2-03 created
`POST /agent-sessions` (returns `agent_session_id`, used by claim); the end/
authorization side sits in MT-1.2-07-adjacent enforcement; Project Context comes
from MT-1.3-02's Section 9.2 endpoints (`GET /projects/{id}/context`). Section 19.3
is the bright line: the bridge **must not duplicate backend logic** — it calls the
APIs, stores what they return for the session duration, and never derives policy
client-side. The resume-context cache named in Section 10.1's responsibilities is
exactly this step-5 artifact.

## Inputs / Prerequisites
* MT-2.2-01 … MT-2.2-03 — manifest path/id and token in hand; this step consumes
  them in Section 10.3's order.
* MT-1.2-03 — `POST /agent-sessions` contract (request/response fields, auth).
* MT-1.3-02 — Project Context API (`GET /projects/{id}/context`) returning name,
  policy summary, rules per Section 10.3 step 5.
* Parent plan Section 9.2 — endpoint signatures and canonical error codes the bridge
  must map/propagate (`AUTH_REQUIRED`, `AUTH_FORBIDDEN_PROJECT`, `RATE_LIMITED` from
  NFR-06).
* Parent plan Section 10.2/FR-MCP-06 — session tied to process lifetime; Section
  10.10 — retry/event-driven behavior for transient failures.

## Scope (in)
* Session open: on bridge startup (after steps 1–3), call `POST /agent-sessions`
  with the manifest-derived project id and the bearer token; store the returned
  `agent_session_id` as the session-scoped value used by subsequent tool calls
  (per `x-agent-session` conventions the backend defines — follow MT-1.2-03's exact
  field, do not invent headers).
* Project-context fetch and cache: immediately after open, call the Project Context
  endpoint and hold `{name, policy summary, rules}` in memory for the session
  duration (FR-MCP-06 lifetime; Section 10.3 step 5) — an in-process cache only; no
  disk persistence (plan says "for the session").
* Session end: on clean shutdown (entry-point teardown from MT-2.1-04 — stdio stdin
  close, signal handling), call the session-end endpoint (the `POST /agent-sessions/
  {id}/end`-style counterpart the backend exposes per Section 9.2); best-effort with
  a short timeout, log failure without blocking exit (Section 10.10 resilience
  posture); on crash, no end call — backend staleness handling covers it (note this
  dependency on the backend's stale-session sweep in the changelog).
* Error mapping: backend 4xx/5xx with canonical codes surface as structured bridge
  errors (MT-2.1-03 logs, no token leakage); `AUTH_FORBIDDEN_PROJECT` at open aborts
  startup — pre-empting MT-2.2-05's *mismatch* check is fine because this call's
  failure is the authoritative project verification (server-verified, FR-SEC-01).
* Tests: open/end happy path against a mock/stub backend; context cache populated
  and served; transient failure retries per Section 10.10 (bounded, event-driven) or
  clear abort; end-call best-effort on shutdown; no duplicate backend logic (cache
  read-only — nothing computes policy client-side); changelog note (item 7).

## Out of scope
* The project-mismatch abort — MT-2.2-05 (this task opens the session; mismatch is
  the cross-check between manifest and returned context).
* Backend session model, staleness sweep, permission checks — M1 (MT-1.2-03,
  MT-1.2-07, backend sweeper WPs).
* Tool-call usage of the session id — WP-2.4 (this task establishes the lifecycle).
* MCP protocol session semantics (MCP `initialize` handshake) — MT-2.1-04 /
  WP-2.4; agent sessions here are the backend's resource, distinct from the MCP
  handshake.
* Persisting resume context across bridge restarts — not specified for the bridge
  ("for the session"); do not add on-disk caching.

## Target paths
* `bridge/` session module (resume-context cache seam from MT-2.1-01's layout)
* `bridge/tests/` (open/end/cache tests against a stubbed backend)
* `bridge/` entry-point wiring (MT-2.1-04 hooks for startup/teardown)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] Startup after steps 1–3 calls `POST /agent-sessions` and stores the returned
  session id for all subsequent bridge calls — Section 10.3 step 4 (FR-MCP-02).
- [ ] Project context `{name, policy summary, rules}` is fetched once and cached in
  memory for the session lifetime, read-only — Section 10.3 step 5; FR-MCP-06;
  Section 19.3 (no duplicated backend logic).
- [ ] Clean shutdown calls the session-end endpoint best-effort with a bounded
  timeout; failure logs and exits without hanging (Section 10.10; NFR-09 practical
  behavior for local tooling).
- [ ] Backend canonical errors (`AUTH_REQUIRED`, `AUTH_FORBIDDEN_PROJECT`,
  `RATE_LIMITED`, `SERVER_ERROR`) propagate distinguishably; no token ever appears
  in the mapped error or logs (Section 9.2 catalog; Section 20.4 item 5; MT-2.1-03).
- [ ] Session id and cache are process-memory only — not written to disk (FR-SEC-04
  hygiene; "for the session").
- [ ] Tests, lint and type check green in CI (item 2); no secrets (item 3);
  changelog note added (item 7).

## Test command
`uv run --directory bridge pytest tests/test_session_lifecycle.py -v` — open stores
id, context cached and reused, end called on teardown (and skipped on forced exit),
transient-failure handling, error mapping with redaction; `uv run --directory bridge
ruff check .` green.

## Attachments
* [Section 10.3 — Session open/end and context cache (steps 4–5)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-MCP-06 — Session lifecycle](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — Agent session endpoints](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Two "session" concepts (MCP protocol handshake vs. backend agent_session_id) will
  confuse readers — name the bridge's variable and log field distinctly (e.g.
  `agent_session_id`) and note the distinction in the changelog; mixing them is a
  real integration bug risk with WP-2.4.
* End-on-shutdown in stdio mode can race the agent's process teardown — bound the
  call aggressively and treat non-2xx as log-and-continue; the plan's staleness
  handling on the backend is the safety net (confirm that sweep exists in the M1
  backend WPs; if not yet implemented, record the gap rather than blocking exit).
* If the Project Context endpoint returns fields beyond `{name, policy summary,
  rules}`, cache only the Section 10.3 set — caching extra data invites client-side
  policy drift (Section 19.3).
