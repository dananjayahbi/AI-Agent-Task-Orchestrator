# MT-1.2-01 — Implement Owner Session Authentication (login/logout/refresh)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.2-01 |
| Title | Implement owner session authentication (login/logout/refresh) |
| Parent WP | WP-1.2 — Accounts, tokens and permissions (Milestone M1) |
| Requirements | FR-SEC-02, NFR-07; OQ-09 |
| Priority | M |
| Dependencies | MT-1.1-05 (WP-1.1 complete: project, OpenAPI, container), MT-1.1-04 (endpoints documented in contract) |
| Parent sections | 9.2 (Auth row), 12.2, 7.2, 19.1 (WP-1.2), 20.4, 20.5; ADR-006 |

## Context
WP-1.2's first slice is owner session auth. Section 12.2 fixes the mechanism for the
owner on web: username/password session with CSRF protection using secure, HTTP-only
cookies, with optional TOTP as a Could. Section 9.2 defines the three Auth endpoints
(`POST /auth/login`, `POST /auth/logout`, `POST /auth/refresh`) with the Owner as
caller. FR-SEC-02 requires distinct, revocable token kinds — owner sessions are the
`owner_session` kind of the API Token model (Section 7.2), so login issues a session
token that logout and expiry can revoke. OQ-09's recommended default (strong password
plus optional TOTP) governs scope decisions.

## Inputs / Prerequisites
* MT-1.1-05 — runnable backend; MT-1.1-04 — endpoints must appear in the OpenAPI
  document as they land (Section 20.4 item 4).
* Parent plan Section 12.2 — owner authentication: username/password session, CSRF,
  secure HTTP-only cookies; optional TOTP (Could).
* Parent plan Section 9.2 — Auth endpoints and their Owner-only caller.
* Parent plan Section 7.2 — API Token entity: `kind` includes `owner_session`; `hash`
  never stores plaintext; `expires_at`, `revoked_at`, `last_used_at`.
* Parent plan Section 9.10 — token lifetimes are a configuration group with documented
  defaults.
* OQ-09 — strong password plus optional TOTP in v1 (decided in WP-0.4; confirm the
  recorded decision before building).

## Scope (in)
* Create the user model backing the owner account (WP-1.2 deliverable: "user model"),
  with password hashing — plaintext passwords never stored (NFR-07 ASVS baseline).
* Implement `POST /auth/login`: verify credentials, start a session with CSRF
  protection via secure, HTTP-only cookies (Section 12.2), and record the session as an
  `owner_session` API Token (hashed per Section 7.2) with `expires_at` from the
  Section 9.10 token-lifetime settings.
* Implement `POST /auth/logout`: revoke the current session token immediately
  (FR-SEC-02 revocable).
* Implement `POST /auth/refresh`: extend/renew the session per the documented lifetime
  rules; refresh must not resurrect a revoked or expired token.
* Failures use only Section 9.2 catalog codes (`AUTH_REQUIRED`, `VALIDATION_ERROR`,
  `RATE_LIMITED` — the latter via MT-1.2-06 if throttled).
* Document the endpoints in the OpenAPI document (Section 20.4 item 4).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* TOTP enforcement — only if the recorded OQ-09 decision requires it in v1; otherwise
  a later hardening item (Section 12.2 marks it Could).
* Agent and device tokens — MT-1.2-02/03/04.
* Permission classes and the authorization matrix — MT-1.2-05.
* Rate limiting configuration — MT-1.2-06.
* Cloudflare edge access policy — WP-3.x (Section 15.3); the Django session is always
  still required (Section 12.2).
* Web login UI — WP-4.x.

## Target paths
* `backend/apps/accounts/` — user model, session auth views/serializers, token wiring
* `backend/tests/` — login/logout/refresh tests
* `schemas/` — OpenAPI snapshot updated (MT-1.1-04 pipeline)
* WP changelog entry

## Acceptance criteria
- [ ] Login/logout/refresh endpoints exist per Section 9.2 and behave as Section 12.2
  specifies: CSRF-protected, secure HTTP-only cookie session.
- [ ] Passwords and session tokens are stored hashed — no plaintext secret in the
  database (Section 7.2; NFR-07).
- [ ] Logout revokes the session immediately; refresh after logout/expiry fails with a
  catalog code (FR-SEC-02).
- [ ] Session lifetime comes from Section 9.10 settings with a documented default.
- [ ] OpenAPI snapshot updated and schema diff reviewed (Section 20.4 item 4).
- [ ] All error codes used exist in the Section 9.2 catalog (Section 20.4 item 5).
- [ ] Tests, lint and type check green in CI (Section 20.4 item 2); no secrets
  committed (item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k "auth or session"` covering: successful login sets a
CSRF-protected cookie, logout revokes (subsequent authenticated request returns
`AUTH_REQUIRED`), refresh of a revoked session fails, and passwords/tokens are not
stored in plaintext.

## Attachments
* [Section 12.2 — Authentication and authorization](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — REST API surface (Auth endpoints)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [OQ-09 — Owner authentication strength](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* OQ-09 was to be decided in WP-0.4 — re-read the recorded decision; if TOTP is in for
  v1, this task grows and may need splitting (Section 20.3 sizing).
* Session vs. stateless-token tradeoff for `refresh` is not detailed in the plan —
  follow Section 12.2 literally (session + revocable `owner_session` token) and record
  the chosen storage mechanics in the changelog rather than inventing a second auth
  path.
