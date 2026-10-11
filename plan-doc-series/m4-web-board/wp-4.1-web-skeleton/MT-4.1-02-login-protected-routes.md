# MT-4.1-02 — Implement Login and Protected Routes

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.1-02 |
| Title | Implement login and protected routes |
| Parent WP | WP-4.1 — Web app skeleton (Milestone M4) |
| Requirements | FR-WEB-01; FR-SEC-01/FR-SEC-02 (session auth), G-07 (project denial) |
| Priority | M |
| Dependencies | MT-4.1-01 (scaffold + route structure), MT-1.2-01 (backend session login/CSRF/cookies), MT-1.2-07 (authorization matrix), ADR-001/ADR-012 |
| Parent sections | 12.2 (session auth for web), 13.1 (login flow), 13.2 (client behavior), 23 (ADR-001, ADR-012), 19.1 (WP-4.1 second slice), 20.4, 20.5; OQ-09 |

## Context
Section 12.2 draws the auth line by client: "Web app uses username/password session
auth (CSRF-protected, HTTP-only cookies)" — the browser never holds a bearer token
(that is the bridge's model); MT-1.2-01 built the backend half (login endpoint,
HTTP-only session cookie, CSRF, logout). Section 13.1's login flow and Section 13.2's
client behavior define the web side: a login screen, session-checked navigation, and
handling of 401/403 from the API (redirect to login; friendly denial for project
access — G-07). WP-4.1's acceptance: **"login works"** — minimal but end-to-end:
credentials in, cookie set, protected pages render, logout clears. ADR-001 (FastAPI
backend) and ADR-012 (Supabase posture) bound what the app may assume — the session
lives in the backend, not in a third-party auth UI. OQ-09 (password strength/TOTP)
remains open: implement the plan's stated baseline only (strong-password guidance is
a default-message concern; TOTP is out until OQ-09 resolves).

## Inputs / Prerequisites
* MT-4.1-01 — scaffold, route placeholders, reserved typed-client seam (login goes
  through the generated client when MT-4.1-03 lands; sequence within the WP allows
  auth to use the client once generated — coordinate order in the changelog).
* MT-1.2-01 — backend login/logout/session endpoints, CSRF header mechanics,
  HTTP-only cookie behavior (the contract to consume; field names from the OpenAPI
  document, MT-1.1-04).
* MT-1.2-07 — authorization matrix: role gates the UI should reflect (hide what the
  user cannot do; server remains authoritative).
* Parent plan Section 12.2 — web session auth model; Section 13.1/13.2 — login flow
  and client error behavior; Section 9.2 — canonical codes the API returns
  (`AUTH_REQUIRED`, `AUTH_FORBIDDEN_PROJECT`, `VALIDATION_ERROR`).
* OQ-09 — strong passwords optional TOTP (defer TOTP; note the open question).

## Scope (in)
* A login page (Section 13.1) collecting username/password, submitting to the
  backend's session login endpoint through the typed client, with CSRF handling per
  MT-1.2-01's contract (HTTP-only cookie set by the response — the app stores no
  token itself).
* Route protection in the App Router scaffold: middleware and/or layout-level
  session check gating every non-login route from Section 13.1 (Board, task detail,
  Projects, Settings); unauthenticated visitors redirect to login with a return path;
  authenticated users landing on `/login` redirect to the Board.
* Logout control in the app chrome calling the backend logout endpoint and clearing
  client-side session state (the cookie is HTTP-only — the app re-verifies session
  via the backend, e.g. a whoami/me endpoint if MT-1.2-01 exposes one; otherwise
  treat any `AUTH_REQUIRED` response as the session-expired signal and redirect —
  pick one strategy, document it in the changelog).
* Error handling per Section 13.2: `AUTH_REQUIRED` (401) → silent redirect to login;
  `AUTH_FORBIDDEN_PROJECT` (403) → friendly project-access-denied state (G-07, no
  internal detail leak); `VALIDATION_ERROR` → inline field messages — all mapped
  from the canonical code, never raw server strings (the friendly-message table
  itself is MT-4.1-04's; here wire the routing behavior).
* Role-aware UI affordances: hide actions the Section 12.3 matrix would deny
  (cosmetic only — every action still verified server-side; MT-1.2-07 is truth).
* Tests: unauthenticated redirect for each protected route; login happy path against
  a mocked/stubbed backend; logout clears and redirects; 401-mid-session redirect;
  403 denial state; no token/secret in client state or logs; changelog note
  (Section 20.4 item 7).

## Out of scope
* Backend auth endpoints, cookies, CSRF implementation — MT-1.2-01 (consume only).
* OIDC/SSO login UI — WP-1.3's flag-gated path (Section 12.2); if `AUTH_MODE=oidc`
  changes the web flow, that is a later WP's UI work — note the seam.
* TOTP/2FA UI — OQ-09 unresolved; do not build speculative controls.
* Permission enforcement in actions — server-side (MT-1.2-07); the UI merely hides.
* The friendly error-code message table and theming — MT-4.1-04.
* Typed client generation itself — MT-4.1-03 (login uses it once present).

## Target paths
* `web/` — login route, middleware/layout protection, logout control, session state
  (App Router segments from MT-4.1-01's structure)
* `web/tests/` (or the scaffold's test location — auth flow tests with a stubbed
  backend)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] Login with valid credentials sets the backend session and lands the user on
  the Board; the app holds no bearer token (Section 12.2 web model; WP-4.1
  acceptance "login works") (FR-WEB-01; FR-SEC-01).
- [ ] Every Section 13.1 route except login is unreachable unauthenticated
  (redirect with return path); authenticated `/login` bounces to Board.
- [ ] Logout calls the backend endpoint and forces a login redirect; session expiry
  mid-session redirects silently (`AUTH_REQUIRED` handling per Section 13.2).
- [ ] `AUTH_FORBIDDEN_PROJECT` renders the friendly denial state (G-07) without
  internal details; canonical codes drive routing (Section 9.2; Section 20.4 item 5).
- [ ] CSRF/cookie mechanics exactly as MT-1.2-01 defines — no custom token storage
  (FR-SEC-02 posture; ADR-012 boundary).
- [ ] Tests, lint, typecheck green in CI (Section 20.4 item 2); no secrets committed
  (item 3); changelog note added (item 7).

## Test command
`npm --prefix web run lint && npm --prefix web run typecheck` plus the web test
runner on the auth suite (e.g. `npm --prefix web test -- auth`, matching the
scaffold's runner choice recorded in the changelog) — protected-route redirects,
login/logout, 401/403 handling against a stubbed backend.

## Attachments
* [Section 12.2 — Web session authentication](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.1 / 13.2 — Login flow and client behavior](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-4.1 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Cookie SameSite/secure attributes interact with local dev origins — mismatches
  produce the classic "login works in prod, 401s in dev" bug; mirror MT-1.2-01's
  documented dev configuration and record it in the changelog rather than weakening
  protections ad hoc.
* Protecting routes in the client cannot be the only gate (middleware + layout
  checks are UX; the API is authoritative) — make sure tests assert that hitting an
  API route directly without a session returns `AUTH_REQUIRED` from the backend
  (integration assertion), so nobody mistakes UI gating for security.
* Sequence risk inside WP-4.1: if MT-4.1-02 lands before MT-4.1-03's client
  generation, hand-written fetches would violate NFR-11 — order the slices (client
  first, or a temporary narrow login call clearly replaced in the same WP) and state
  the chosen order in the changelog.
