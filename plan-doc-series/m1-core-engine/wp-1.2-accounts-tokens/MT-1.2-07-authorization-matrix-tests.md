# MT-1.2-07 — Write Authorization-Matrix Tests Incl. Cross-Project Rejection

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.2-07 |
| Title | Write authorization-matrix tests incl. cross-project rejection |
| Parent WP | WP-1.2 — Accounts, tokens and permissions (Milestone M1) |
| Requirements | FR-SEC-01, FR-SEC-02, FR-SEC-05, NFR-07; ADR-004, G-07 |
| Priority | M |
| Dependencies | MT-1.2-01, MT-1.2-02, MT-1.2-03, MT-1.2-04, MT-1.2-05, MT-1.2-06 (the whole WP under test), MT-1.1-04 (OpenAPI for endpoint enumeration) |
| Parent sections | 12.2, 18 (Security layer), 19.1 (WP-1.2 acceptance), 20.4, 20.5; ADR-004 |

## Context
WP-1.2's acceptance is a behavioral statement: "an agent token for PID00001 receives
`AUTH_FORBIDDEN_PROJECT` on any PID00002 resource; revoked tokens fail immediately."
Section 19.1 lists "authorization matrix (Section 12.2) as tests" among the WP's
deliverables, and Section 18 maps "authorization matrix tests; token scoping" to the
Security test layer. This micro-task is the executable proof of the whole WP: every
matrix row, the cross-project rejection, revocation immediacy, and rate limiting are
asserted against the running API — the Zero-Bleed guarantee (GOAL-2) made testable.

## Inputs / Prerequisites
* MT-1.2-01 through MT-1.2-06 — all endpoints, models, permission classes and
  throttling under test.
* MT-1.1-04 — OpenAPI document enumerates the endpoints the tests must cover
  (prevents "forgot to protect a new route" drift).
* Parent plan Section 12.2 — the matrix: rows = capabilities, columns = Owner, coder,
  auditor, decomposer, Merge Executor, Device.
* Parent plan Section 18 — Security layer: "authorization matrix tests; token
  scoping; … Section 12.1 mapped to tests".
* Parent plan Section 19.1 — WP-1.2 acceptance criteria (both halves).
* Parent plan Section 9.2 — canonical codes the tests may assert: `AUTH_REQUIRED`,
  `AUTH_FORBIDDEN_PROJECT`, `ROLE_NOT_PERMITTED`, `RATE_LIMITED`.

## Scope (in)
* Write integration tests that exercise the API with real authentication for each
  actor kind: owner session, agent token (per role/scopes), device token.
* Cover every Section 12.2 matrix row that maps to an endpoint existing at this point;
  structure the suite as a data-driven matrix so a new row/endpoint forces a test
  update (traceability, Section 20.5).
* WP-1.2 acceptance tests, explicitly:
  * Agent token issued for PID00001 → any request addressing a PID00002 resource
    returns `AUTH_FORBIDDEN_PROJECT` (cross-project rejection).
  * Revoked agent/device/owner token fails on its next request — no cache lag
    ("revoked tokens fail immediately").
* Negative tests: missing token (`AUTH_REQUIRED`), valid token wrong role
  (`ROLE_NOT_PERMITTED`), body-supplied project id different from token scope ignored
  (project always resolved from token, Section 9.3 step 1).
* Rate-limit test: agent/device endpoint burst returns `RATE_LIMITED`
  (FR-SEC-05, MT-1.2-06).
* Ensure the suite runs in the CI test job (MT-0.3-02) as part of the Security layer.
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Claim/transition/lease actor guards (T4 coder, T11 auditor) — WP-1.5/WP-1.6 tests;
  this suite covers only what exists after WP-1.2.
* Path traversal, upload abuse, secrets scanning — Section 18 security items owned by
  other WPs (uploads WP-1.11, scans MT-0.3-04).
* Promoting the suite into the consolidated WP-1.15 hardening suite — that WP adopts
  it; do not duplicate it there later.

## Target paths
* `backend/tests/` — authorization-matrix test module (data-driven per Section 12.2
  row)
* WP changelog entry

## Acceptance criteria
- [ ] A test exists for every Section 12.2 matrix row backed by a current endpoint;
  the suite fails if a row has no case (Section 12.2 "as tests"; Section 20.5).
- [ ] WP-1.2 acceptance demonstrably met: PID00001 agent token on a PID00002 resource
  returns `AUTH_FORBIDDEN_PROJECT`; revoked tokens fail immediately
  (Section 19.1).
- [ ] Missing-auth and wrong-role cases return `AUTH_REQUIRED` / `ROLE_NOT_PERMITTED`
  only — no invented codes (Section 20.4 item 5).
- [ ] Body-supplied `project_id` cannot widen a token's scope (ADR-004; G-07 defense
  in depth).
- [ ] A rate-limit case asserts `RATE_LIMITED` on an agent/device endpoint
  (FR-SEC-05).
- [ ] Suite runs green in CI with the test job (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests/test_authorization_matrix.py -v`; then run the full CI test
job (MT-0.3-02) to confirm the suite is wired in.

## Attachments
* [Section 12.2 — Authorization matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and Quality Strategy (Security)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.2 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Matrix rows for endpoints that do not exist yet (claim, verdict, merge queue) cannot
  be tested here — mark them explicitly as deferred in the suite's coverage notes so
  WP-1.5/1.6/3.x can pick them up; an untested row must never be silently "green".
* Tests must use two real projects (PID00001/PID00002) created through the WP-1.3 API
  when it exists; until then create rows directly in fixtures — switch to API-created
  projects once WP-1.3 lands to avoid fixture drift (dependency note for scheduling).
