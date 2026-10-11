# MT-1.2-05 — Implement Permission Classes Enforcing the Authorization Matrix (Section 12.2)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.2-05 |
| Title | Implement permission classes enforcing the authorization matrix (Section 12.2) |
| Parent WP | WP-1.2 — Accounts, tokens and permissions (Milestone M1) |
| Requirements | FR-SEC-01, FR-SEC-02, NFR-07; ADR-004, G-07 |
| Priority | M |
| Dependencies | MT-1.2-01 (owner session), MT-1.2-02 (token model/validity), MT-1.2-03 (agent tokens), MT-1.2-04 (device tokens), MT-1.1-04 (endpoints to protect) |
| Parent sections | 12.2, 6.4, 12.1, 9.2, 19.1 (WP-1.2), 20.4, 20.5; ADR-004, ADR-006 |

## Context
WP-1.2's deliverable "authorization matrix (Section 12.2) as tests" is only as strong
as the permission classes it tests. Section 12.2's matrix maps each capability
(manage projects/policy, create draft tasks, publish, claim pending, claim
to_be_audited, submit resolution, submit verdict, review decisions, merge queue, read
events) across Owner, coder, auditor, decomposer, Merge Executor and Device. Section
12.1 requires that "the Django token is always still required" and that project
scoping is enforced server-side (ADR-004): resolving the caller's project **from the
token, not from the request body** (Section 9.3 step 1 — the same discipline applies
everywhere).

## Inputs / Prerequisites
* MT-1.2-01/02/03/04 — the three authentication paths and the token validity
  predicate.
* Parent plan Section 12.2 — the matrix itself; each row becomes a permission rule.
* Parent plan Section 6.4 — trust boundaries (web, bridge/agents, mobile, edge).
* Parent plan Section 9.2 — per-endpoint caller column (Owner / Agent / Auditor /
  Bridge / Mobile / Infrastructure).
* Parent plan Section 12.1 — threat model rows: cross-project leakage, token theft.
* Error catalog Section 9.2: `AUTH_REQUIRED`, `AUTH_FORBIDDEN_PROJECT`,
  `ROLE_NOT_PERMITTED` are the only auth failures this task may emit.

## Scope (in)
* Implement authentication resolution for all three token kinds (owner session, agent,
  device) plus the unauthenticated infrastructure endpoints (`/health/*` per
  MT-1.1-03).
* Implement permission classes covering every Section 12.2 matrix row that has a
  backend endpoint today or in this milestone's WP sequence (projects, policy, tasks,
  tokens, devices, events read), keyed on token kind and role:
  * Owner-only: manage projects/policy, token management, review decisions.
  * Agent (coder/auditor/decomposer/merge-executor roles per token `scopes`/kind):
    only their permitted rows; agents never subscribe to events (Section 9.6).
  * Cross-project access: any request where the token's `project_id` differs from the
    addressed project's `PID` returns `AUTH_FORBIDDEN_PROJECT` (WP-1.2 acceptance).
  * Unauthenticated access to a protected endpoint returns `AUTH_REQUIRED`; wrong-role
    access returns `ROLE_NOT_PERMITTED`.
* Resolve the project scope from the token, never from a request-body field
  (Section 9.3 step 1 discipline; ADR-004).
* Wire the classes onto the endpoints that exist (health, auth, tokens, devices; plus
  projects/tasks endpoints as they land in WP-1.3/1.4 — coordinate so each WP's
  endpoints arrive protected; do not implement those endpoints here).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* The test suite proving the matrix — MT-1.2-07 (this task provides the classes it
  exercises).
* Lease/claim role checks (coder vs auditor claim guards) — WP-1.5/WP-1.6 refine
  transition/claim-time actor validation; here only the coarse matrix rows exist.
* Edge/Cloudflare policy — WP-3.x (Section 15.3, ADR-006 layered defense).
* Rate limiting — MT-1.2-06.
* Audit-trail writes for denials — audit/event rows for auth actions come with
  WP-1.9's write-in-transaction helper; record a hook note if a denial must emit later.

## Target paths
* `backend/apps/accounts/` — authentication backends and permission classes
* `backend/` — wiring of permission classes onto existing endpoint routes
* `backend/tests/` — unit tests per permission class
* WP changelog entry

## Acceptance criteria
- [ ] Every row of the Section 12.2 matrix that maps to an existing endpoint is
  enforced by a named permission class, with no matrix row silently dropped
  (Section 20.5 traceability: cite each row in the test/doc comments).
- [ ] Project scope comes from the token; supplying another project's `PID` in the
  body/URL with a mismatched token yields `AUTH_FORBIDDEN_PROJECT` (FR-SEC-01,
  ADR-004, G-07; WP-1.2 acceptance).
- [ ] Missing/invalid/expired/revoked credentials yield `AUTH_REQUIRED`; wrong role
  yields `ROLE_NOT_PERMITTED` — no other codes, none invented
  (Section 20.4 item 5).
- [ ] Unauthenticated `/health/live` and `/health/ready` still work (MT-1.1-03
  preserved).
- [ ] Agents cannot read events (Section 9.6 authorization per connection) for any
  events endpoint present.
- [ ] Tests, lint, type check green (item 2); OpenAPI snapshot unchanged unless new
  401/403 responses were added — then diff reviewed (item 4).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k "permission or authz"` for the per-class unit tests; full
matrix integration tests run in MT-1.2-07.

## Attachments
* [Section 12.2 — Authentication and authorization matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 6.4 — Trust boundaries](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-004 — Agent tokens scoped to exactly one project](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The matrix's "Merge Executor" and "Decomposer" rows have no distinct token kind in
  Section 7.2 (kinds are owner_session/agent/device) — roles ride on agent tokens'
  `scopes`. Confirm this reading against Section 12.2 and record it; if scopes are
  undefined for a role, raise it rather than inventing a fourth kind (Section 20.1
  item 5: no hidden decisions).
* Permission mistakes are silent security holes — this task must not ship without
  MT-1.2-07's cross-project test; treat them as one delivery unit if review so decides.
