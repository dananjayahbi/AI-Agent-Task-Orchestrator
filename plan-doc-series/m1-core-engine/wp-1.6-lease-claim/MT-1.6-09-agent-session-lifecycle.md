# MT-1.6-09 — Implement the Agent Session Open and End Endpoints

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.6-09 |
| Title | Implement the agent session open and end endpoints (`POST /agent-sessions`, `POST /agent-sessions/{id}/end`) |
| Parent WP | WP-1.6 — Lease and claim service (Milestone M1) |
| Requirements | FR-SEC-01, FR-SEC-02, FR-SEC-05; G-18 (context) |
| Priority | M |
| Dependencies | MT-1.2-03 (agent token authentication and project scoping), WP-1.3 (project registry) |
| Parent sections | 9.2 (Sessions row), 7.2 (Agent Session entity), 12.2 (authentication and authorization), 20.2, 20.4 |

## Context
Section 9.2's Sessions row — `POST /agent-sessions`; `POST /agent-sessions/{id}/end`,
caller **Bridge** — is required by the bridge micro-tasks (MT-2.2-04 opens the session
on startup and stores the returned session id; MT-2.9-03 calls the end counterpart on
close; MT-2.12-03 uses session open as its connectivity probe), yet no micro-document
in the series owns it: MT-1.2-03's out-of-scope note deferred "Agent sessions
(`POST /agent-sessions`)" to a "WP-1.x sessions slice" that was never created. Per
roadmap rule 7 ("an MT added" → update `overview.md`) this gap is closed by adding
MT-1.6-09 to WP-1.6, the milestone slice that already owns leases and binds them to
sessions. Section 7.2 defines the **Agent Session** entity: `id` (bridge-issued,
unguessable), `project_id`, `token_id`, `agent_label`, `client_name`, `capability`
(`vision` / `text_only` / `unknown`), `transport` (`stdio` / `http`), `started_at`,
`last_seen_at`, `ended_at`. Section 10.3 step 4 (context only) says the backend verifies
the token's project when the session opens; Section 12.2 + ADR-004 make the agent token
project-scoped, so the session's `project_id` comes from the token and never from the
request body. G-18 records the purpose: the bridge issues a unique, unguessable
`session_id` and the backend binds leases to token + session id — the human-readable
`agent_label` is a label only. What the bridge does *after* opening — caching project
context for the session (Section 10.3 step 5) — is the bridge's job (MT-2.2-04,
Section 19.3: no backend logic duplicated client-side); this task ends at the two
endpoints and their row lifecycle.

## Inputs / Prerequisites
* Parent plan Section 9.2 — the Sessions row: two endpoints, caller **Bridge**, the
  standard error envelope, the canonical 19-code catalog, `Idempotency-Key` on every
  mutating endpoint.
* Parent plan Section 7.2 — the Agent Session field list (the exact fields above);
  `capability` values from Section 10.4 (default `unknown`), `transport` values from
  Section 10.2 (the two run modes).
* Parent plan Section 12.2 — agents authenticate with long-lived, revocable,
  **project-scoped** bearer tokens (ADR-004); the bridge presents that token, so the
  session is bound to exactly one project.
* MT-1.2-03 / MT-1.2-05 — agent-token authentication, `HasProjectScope`-family scoping,
  `AUTH_REQUIRED` / `ROLE_NOT_PERMITTED` / `AUTH_FORBIDDEN_PROJECT` refusal shapes.
* MT-0.5-02 / MT-0.5-03 — error envelope and header conventions
  (`X-Correlation-ID`, `Idempotency-Key` — the one canonical spelling each).
* WP-0.3 / FR-SEC-05 — the endpoint must be throttled (`AgentEndpointThrottle`) when
  it lands, per `tests/test_rate_limiting.py`'s Section 9.2 coverage enumeration.

## Scope (in)
* Create the `AgentSession` model in the `agents` app exactly as Section 7.2 lists it
  (one row per session; no fields added, dropped or renamed): `id` primary key
  (bridge-issued, unguessable, opaque — the backend never parses its format),
  `project` FK (Section 7.2 `project_id`), `token_id` (the presenting `ApiToken`'s id),
  `agent_label`, `client_name`, `capability`, `transport`, `started_at`,
  `last_seen_at`, `ended_at` — with the migration and the canonical choice/regex
  constraints where the plan fixes a closed vocabulary.
* Implement `POST /agent-sessions` (caller Bridge): authenticated with a live **agent**
  token; the project is resolved from the token (never the body, Section 9.3 step 1
  reading / ADR-004); validates the closed vocabularies (`capability` defaults to
  `unknown` per Section 10.4, `transport` is one of Section 10.2's two modes);
  `201` returns the created session (Section 7.2 fields; `ended_at` null); a duplicate
  `id` answers `VALIDATION_ERROR` (the catalog has no id-collision code and a 20th is
  forbidden — Section 20.4 item 5; retries are the `Idempotency-Key`'s job).
* Implement `POST /agent-sessions/{id}/end` (caller Bridge): same agent-token
  authentication and project scope (a session row of another project answers
  `AUTH_FORBIDDEN_PROJECT`); sets `ended_at`; `200` returns the row; ending an
  already-ended session replays the stored outcome (`200`, no second write — the
  bridge's best-effort shutdown call must be safe); an unknown id answers the same
  `VALIDATION_ERROR`/400 mapping the core handler documents for resources with no
  catalog code of their own (the projects reading — Section 20.4 item 5).
* Authorization refusals per Section 12.2: anonymous → `AUTH_REQUIRED` (401); an
  owner-session or device credential → `ROLE_NOT_PERMITTED` (403 — Sessions row caller
  is Bridge, and Section 12.2 grants no session capability to those actors); an agent
  token of another project → `AUTH_FORBIDDEN_PROJECT` (403) before any other logic.
* `Idempotency-Key` handling on both mutating endpoints via the shared WP-1.1/WP-0.5
  store (NFR-12; ADR-012): same key + same request replays the original outcome, so a
  retried open never creates a second row.
* `AgentEndpointThrottle` on both views (Section 9.2 caller Bridge; FR-SEC-05) and the
  corresponding `present` flips in `tests/test_rate_limiting.py`'s enumeration.
* Drift-guard replacements: remove the two `agent-sessions` entries from
  `DEFERRED_ENDPOINTS` in `tests/test_authorization_matrix.py` and replace them with
  real-route authorization cases (anonymous 401 / owner+device 403 / agent 201) so no
  landed route is ever untested (MT-1.2-07's risk note).
* Endpoint and service tests: open happy path binds project from the token (a body
  `project_id` can never widen scope — ADR-004/G-07), duplicate id refused, end sets
  `ended_at`, double-end idempotent, cross-project end refused, revoked token fails on
  its very next request; OpenAPI regen includes both paths (Section 20.4 item 4).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* The bridge side: session open on startup, session-end on shutdown, and the cached
  project context `{name, policy summary, rules}` — MT-2.2-04 (Section 19.3: the
  bridge must not duplicate backend logic; the cache is the bridge's).
* The connectivity self-test that *uses* session open — MT-2.12-03.
* Stale-session sweeps (`last_seen_at` aging, crashed bridges that never call end) —
  the sweeper family (WP-1.7 records its dependency; no sweep is invented here).
* `GET /agent-sessions` (Owner-facing session list) — MT-4.9-01 records that Section
  9.2 defines no read endpoint yet.
* Claim/lease binding to the session id (`worker_session_id`) — MT-1.6-01/07; the
  session registry is not a claim precondition (recorded reading, not a hidden one).
* Section 9.6 `agent.session_started` / `agent.session_ended` Event rows — the
  in-transaction event writer lands with WP-1.9 (MT-1.9-02's helper is the single
  event mechanism; this task invents no second one) and the emission is wired there.
* Capability negotiation / capability-table lookup (Section 10.4) — the endpoint
  stores what the bridge declares; resolution is the bridge's (WP-2.2).
* Rate-limit *tuning* beyond wiring the existing documented `agent` scope.

## Target paths
* `backend/apps/agents/` (model, migration, service, serializers, views, urls)
* `backend/config/urls.py` (mount `apps.agents.urls` under `/api/v1`)
* `backend/tests/` (endpoint and authorization tests)
* `backend/tests/test_authorization_matrix.py` (deferred-route replacement rows)
* `backend/tests/test_rate_limiting.py` (`present` flips for the two Sessions routes)
* `schemas/openapi.yaml` (regenerated once with the WP-1.6 batch)
* WP changelog entry

## Acceptance criteria
- [ ] `AgentSession` matches the Section 7.2 field list exactly; migration applies
  cleanly and `makemigrations --check` stays green (Section 20.4 item 2).
- [ ] `POST /agent-sessions` with a live agent token creates the row with
  `project_id`/`token_id` taken from the token, `capability` defaulting to
  `unknown`, and returns `201` with the Section 7.2 fields (Section 12.2, ADR-004,
  Section 10.4).
- [ ] A body-supplied `project_id` never influences the stored project (ADR-004;
  G-07) — same acceptance shape as the task routes.
- [ ] Anonymous → `AUTH_REQUIRED`; owner-session/device → `ROLE_NOT_PERMITTED`;
  other-project agent token on end → `AUTH_FORBIDDEN_PROJECT`; only catalog codes
  (Section 9.2; Section 20.4 item 5).
- [ ] `POST /agent-sessions/{id}/end` sets `ended_at` exactly once; a second end is
  a `200` replay with no write; an unknown id answers the core handler's documented
  no-catalog-code mapping.
- [ ] Both mutating endpoints honor `Idempotency-Key` (NFR-12; ADR-012) and carry
  `AgentEndpointThrottle` (FR-SEC-05); the rate-limit enumeration rows are flipped.
- [ ] Both paths appear in the generated OpenAPI document; schema diff reviewed with
  the WP-1.6 batch (Section 20.4 item 4).
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k agent_session -q` (open/end happy paths, scope binding,
duplicate id, double-end idempotency, cross-project and anonymous refusals, revoked
token) plus `pytest backend/tests/test_authorization_matrix.py
backend/tests/test_rate_limiting.py -q` (the replaced drift guards); full suite
(`pytest backend/tests -q`) stays green.

## Attachments
* [Section 9.2 — REST API surface (Sessions row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Agent Session entity](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Authentication and authorization](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The session `id` is bridge-issued and unguessable (G-18) but the endpoint cannot
  *prove* unguessability — it validates shape/length only; the security boundary is
  the project-scoped token, not the id's secrecy (recorded, not hidden).
* Two "session" concepts (the backend `agent_session_id` vs. an MCP protocol
  handshake) will confuse readers — MT-2.2-04's risk note repeats it; keep naming
  consistent (`agent_session_id`) in serializers and OpenAPI.
* Ending sessions belongs to the bridge's best-effort shutdown: if the bridge crashes,
  rows stay open — staleness handling must arrive with a sweeper WPs record the
  dependency here rather than silently growing a background job.
* `last_seen_at` has no writer beyond `started_at` until later WPs add session-scoped
  calls; do not invent a heartbeat (OQ-04's liveness question stays closed).
