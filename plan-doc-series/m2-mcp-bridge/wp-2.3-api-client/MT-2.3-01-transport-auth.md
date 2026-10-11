# MT-2.3-01 — Implement the transport and authentication layer

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.3-01 |
| Title | Implement the transport and authentication layer |
| Parent WP | WP-2.3 — Backend API client (Milestone M2) |
| Requirements | NFR-04; ADR-005 (OpenAPI is the contract the client speaks) |
| Priority | M |
| Dependencies | WP-2.1 (bridge package skeleton); WP-1.1 (Django project serving `/api/v1`); MT-2.2-03 (agent token loading from environment or user-level config) |
| Parent sections | 10.1, 10.3, 12.2, 19 (WP-2.3), 20.4, 20.5 |

## Context
WP-2.3's first slice is the raw HTTP layer every bridge tool call passes through: base
URL from the manifest (`orchestrator_api`), the project-scoped agent bearer token from
WP-2.2, and the API version header checked at startup (Section 10.11). Section 12.2
fixes how agents authenticate — long-lived, revocable, project-scoped bearer tokens —
and Section 10.3 step 4 guarantees the backend rejects a token whose project does not
match the manifest. Until this layer exists, retries, idempotency and error
translation (later slices) have nothing to attach to.

## Inputs / Prerequisites
* Parent plan Section 10.3 — manifest binding; base URL and token sources; project
  mismatch abort already implemented by WP-2.2.
* Parent plan Section 12.2 — agent authentication: project-scoped bearer token in the
  Authorization header; token created by the Owner via `POST /tokens/agent`.
* Parent plan Section 9.2 — endpoint surface and the standard error envelope the
  transport must be able to parse.
* Parent plan Section 10.11 — version compatibility checked at startup via an API
  version header.
* WP-2.1 — bridge package skeleton and its test harness.

## Scope (in)
* A single typed client module in `bridge/src/` that builds every request against the
  manifest's `orchestrator_api` base path (`/api/v1`).
* Attaching the agent bearer token to every request, read via WP-2.2's token loader
  (never from the manifest, never logged).
* Attaching the API version header and checking the backend's version response at
  session open, failing fast with a clear startup error on mismatch.
* Uniform parsing of the Section 9.2 error envelope into a typed client error that
  carries `code`, `message`, `retryable`, `details`, `correlation_id`.
* Connection timeout and response-size defaults as named configuration with documented
  defaults (Section 9.10 discipline).
* Unit tests with a mocked transport covering success, 401, malformed body and
  version-mismatch paths.

## Out of scope
* Retry/backoff behavior — MT-2.3-02.
* Idempotency key attachment — MT-2.3-03.
* Mapping errors to tool errors (code + hint + next action) — MT-2.3-04.
* OpenAPI contract testing — MT-2.3-05.
* Token loading and manifest discovery — WP-2.2.
* Rate limiting, pagination and endpoint business logic — backend (WP-1.1 onward).

## Target paths
* `bridge/src/` (client transport module)
* `bridge/tests/` (transport/auth unit tests)
* WP changelog entry

## Acceptance criteria
- [ ] Every request carries the manifest base URL, the bearer token and the API
  version header; no request path ever embeds the token in a URL or log line.
- [ ] Non-2xx responses are parsed into the Section 9.2 envelope fields; unparseable
  bodies degrade to a `SERVER_ERROR`-tagged client error rather than crashing.
- [ ] A backend version mismatch aborts startup with a clear, actionable message
  (Section 10.11).
- [ ] Unit tests cover success, 401 (`AUTH_REQUIRED`), malformed body and
  version-mismatch cases and pass in CI (Section 20.4 item 2).
- [ ] No secrets or environment-specific paths committed (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the bridge unit suite for the transport module from the repository root, e.g.
`uv run pytest bridge/tests/ -k transport`, and confirm the auth, malformed-body and
version-mismatch cases pass.

## Attachments
* [Section 10.3 — Manifest discovery and binding](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Authentication and authorization](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Token handling is security-sensitive: verify tokens are scrubbed from logs and
  error messages (Section 12.4 logs scrub tokens) before merging.
* The exact API version header name is not fixed in the plan — treat it as an
  OQ-xx candidate if WP-1.1 has not settled it; do not invent a name silently.
