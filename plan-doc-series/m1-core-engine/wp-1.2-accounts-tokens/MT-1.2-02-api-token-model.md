# MT-1.2-02 — Create the API Token Model with Hashed Storage and Expiry Fields

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.2-02 |
| Title | Create the API token model with hashed storage and expiry fields |
| Parent WP | WP-1.2 — Accounts, tokens and permissions (Milestone M1) |
| Requirements | FR-SEC-01, FR-SEC-02, FR-SEC-04; ADR-004 |
| Priority | M |
| Dependencies | MT-1.2-01 (user model exists; session auth consumes this model), MT-1.1-05 |
| Parent sections | 7.1, 7.2, 7.4, 12.1, 19.1 (WP-1.2), 20.4, 20.5; ADR-004 |

## Context
WP-1.2's slice "token model and hashing" is the data foundation for all three token
kinds. Section 7.2 fixes the API Token entity: `id`, `kind`
(`owner_session`/`agent`/`device`), `hash` (never plaintext), `project_id` (required
for `agent`), `scopes`, `expires_at`, `revoked_at`, `last_used_at`. The threat model
(Section 12.1) lists token theft with mitigation "project-scoped, revocable, hashed at
rest, expiring" — every one of those adjectives is a field or invariant of this model.
Per Section 20.3, a migration is created for this model alone, with no unrelated logic.

## Inputs / Prerequisites
* MT-1.2-01 — the user model; `owner_session` tokens reference it (Section 7.1: API
  Token N:1 User via kind/scope).
* Parent plan Section 7.2 — API Token fields, verbatim.
* Parent plan Section 7.4 — integrity constraints (validate against plan; ids and
  enums enforced at DB level where the plan requires).
* Parent plan Section 7.3 — identifier rules apply to PID/Task id; token ids are
  internal (UUID-style acceptable — do not borrow the PID pattern).
* ADR-004 — tokens are scoped to exactly one project (for `agent` kind); the model
  must make cross-project tokens impossible to represent incorrectly.

## Scope (in)
* Create the API Token model with exactly the Section 7.2 fields: `kind` constrained to
  the three canonical kinds, `hash` as the only secret representation (plaintext is
  never persisted — Section 7.2 "never store plaintext"), nullable `project_id`
  required by validation whenever `kind = agent` (Section 7.2), `scopes`, `expires_at`,
  `revoked_at`, `last_used_at`.
* Create this migration alone (Section 20.3: never combine a migration with unrelated
  logic).
* Define the canonical validity predicate used everywhere: a token is usable iff not
  revoked (`revoked_at` null), not expired (`expires_at` null or in the future), and —
  for `agent` — its `project_id` matches the resource's project. This predicate is the
  single source for authentication checks in MT-1.2-03/05.
* Model-level tests for each invariant (including: `agent` kind without `project_id`
  is rejected).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Hashing algorithm selection for tokens — decide here only if Section 9.x/12.x pins
  one; otherwise record the algorithm choice in the changelog as a documented default
  (fast hash for lookup-by-hash, per standard practice for bearer tokens) and keep it
  consistent in MT-1.2-03.
* Issuance/revocation endpoints and token plaintext delivery — MT-1.2-03.
* Device-specific fields (`platform`, `push_token`, `biometric_bound`) — the Device
  entity is separate (Section 7.2); MT-1.2-04.
* Permission/scope evaluation logic — MT-1.2-05.
* Rotation/expiry sweeper jobs — not in the plan; expired tokens simply fail the
  validity predicate.

## Target paths
* `backend/apps/accounts/` — API Token model
* `backend/` — migration for the token model only
* `backend/tests/` — model invariant tests
* WP changelog entry

## Acceptance criteria
- [ ] The model carries every Section 7.2 API Token field with the canonical names and
  enum values; no field added or dropped (Section 20.5 traceability).
- [ ] `kind = agent` requires `project_id`; a cross-project or project-less agent token
  cannot be created (ADR-004, FR-SEC-01).
- [ ] Only `hash` is stored — a test proves no plaintext token value is readable from
  the model instance/database (Section 7.2; FR-SEC-04 spirit).
- [ ] The validity predicate (revoked/expired/scope) exists once and is tested for all
  three kinds (FR-SEC-02 revocable; Section 12.1 "expiring").
- [ ] A standalone migration applies and reverses cleanly (Section 20.3; Section 18
  migration check).
- [ ] Lint, type check and tests green (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k token` covering: plaintext never persisted, agent kind
enforces `project_id`, each invalid state (revoked, expired) fails the validity
predicate, and `python manage.py makemigrations --check` reports no unapplied model
changes (Section 18 migration gate).

## Attachments
* [Section 7.2 — Entities and key fields (API Token)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.1 — Threat model summary (token theft)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-004 — Agent tokens scoped to exactly one project](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* This model is security-critical: any path that logs or returns `hash` leaks every
  token. Add an explicit test that `hash` never appears in API representations.
* The plan does not name the hash algorithm — pick one, record it in the changelog,
  and never allow plaintext or a reversible encoding to stand in for it.
