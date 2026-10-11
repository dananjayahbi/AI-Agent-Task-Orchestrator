# MT-1.2-03 — Implement Project-Scoped Agent Token Issuance and Revocation

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.2-03 |
| Title | Implement project-scoped agent token issuance and revocation |
| Parent WP | WP-1.2 — Accounts, tokens and permissions (Milestone M1) |
| Requirements | FR-SEC-01, FR-SEC-02; ADR-004, G-07 |
| Priority | M |
| Dependencies | MT-1.2-02 (API Token model and validity predicate), MT-1.2-01 (owner session authenticates the caller) |
| Parent sections | 9.2 (Tokens row), 12.1, 12.2, 19.1 (WP-1.2), 20.4, 20.5; ADR-004 |

## Context
WP-1.2's acceptance test is: "an agent token for PID00001 receives
`AUTH_FORBIDDEN_PROJECT` on any PID00002 resource; revoked tokens fail immediately."
This micro-task builds the issuance side: the Owner creates long-lived but revocable
project-scoped bearer tokens (Section 12.2) through `POST /tokens/agent`, lists them
via `GET /tokens`, and revokes with `DELETE /tokens/{id}` (Section 9.2, caller Owner).
The plaintext token is shown to the Owner exactly once at creation; only the hash is
stored (Section 7.2). This is the Zero-Bleed backstop of ADR-004/G-07: the backend,
not the bridge, is the authority.

## Inputs / Prerequisites
* MT-1.2-02 — API Token model; `kind = agent` requires `project_id`; validity
  predicate (revoked/expired) already defined.
* MT-1.2-01 — owner session auth; these endpoints are Owner-only (Section 12.2
  "Manage projects/policy" row is Owner-only; token management follows Owner).
* Parent plan Section 9.2 — `POST /tokens/agent` (project-scoped), `DELETE
  /tokens/{id}`, `GET /tokens`; caller Owner.
* Parent plan Section 12.2 — agents hold long-lived but revocable project-scoped
  bearer tokens, created per project by the Owner, stored in the host's user-level
  config (Section 10.3 step 3: environment or user-level config, never the manifest).
* Parent plan Section 7.2 — `last_used_at` is updated by authentication (field exists;
  this task defines where it is written).

## Scope (in)
* Implement `POST /tokens/agent`: Owner-authenticated; body identifies the target
  project (a `PID`); server generates an unguessable bearer token, stores only the
  hash with `kind = agent`, the project id, optional scopes, and `expires_at` per
  Section 9.10 token-lifetime settings; returns the plaintext token exactly once in
  the response.
* Implement `GET /tokens`: Owner lists her tokens (metadata only — never hashes or
  plaintext), filterable by project/kind.
* Implement `DELETE /tokens/{id}`: sets `revoked_at`; the validity predicate makes the
  token fail immediately on its next use (WP-1.2 acceptance half).
* Reject issuance for a nonexistent or non-`active` project with catalog codes
  (`VALIDATION_ERROR` / appropriate catalog code only — no invented codes).
* Update `last_used_at` on successful authentication so token hygiene is visible.
* Document endpoints in the OpenAPI snapshot (Section 20.4 item 4).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Enforcing the token on project resources — that is MT-1.2-05 (permission classes);
  this task only creates/revokes tokens. The cross-project rejection test lives in
  MT-1.2-07.
* Agent sessions (`POST /agent-sessions`) — WP-1.x sessions slice (Section 9.2
  Sessions row; bridge consumes it in WP-2.2).
* Rate limiting on issuance — MT-1.2-06.
* Storing the token in the host config — bridge-side, WP-2.2.
* Device tokens — MT-1.2-04.

## Target paths
* `backend/apps/accounts/` — token issuance/list/revoke endpoints
* `backend/tests/` — issuance, one-time plaintext, immediate revocation tests
* `schemas/` — OpenAPI snapshot updated
* WP changelog entry

## Acceptance criteria
- [ ] `POST /tokens/agent` issues a project-scoped token: response contains plaintext
  once; database stores only the hash (Section 7.2; ADR-004).
- [ ] The issued token row has `kind = agent` and a `project_id` — a token that could
  address two projects is unrepresentable (FR-SEC-01, G-07).
- [ ] `DELETE /tokens/{id}` sets `revoked_at` and the token fails authentication on
  its very next request (WP-1.2 acceptance: "revoked tokens fail immediately").
- [ ] `GET /tokens` returns metadata without any secret material; endpoints are
  Owner-only (Section 12.2).
- [ ] `last_used_at` is maintained on successful use (Section 7.2).
- [ ] OpenAPI snapshot updated (Section 20.4 item 4); error codes from the Section 9.2
  catalog (item 5); tests/lint green (item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k "token"` covering: issuance returns plaintext exactly
once and persists only the hash; `GET /tokens` never includes secrets; a revoked token
receives `AUTH_REQUIRED` on its next authenticated call; non-Owner callers are rejected
with a catalog code.

## Attachments
* [Section 9.2 — REST API surface (Tokens row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Authentication and authorization](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-004 — Agent tokens scoped to exactly one project](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Returning plaintext once is the only chance the Owner gets — if the response shape
  is wrong, the token is unusable and must be reissued; test the response contract
  against the OpenAPI snapshot.
* Revocation must invalidate without cache lag — if any token caching is introduced
  here (not required by the plan), revoked tokens would leak access; prefer per-request
  validation and note the decision.
