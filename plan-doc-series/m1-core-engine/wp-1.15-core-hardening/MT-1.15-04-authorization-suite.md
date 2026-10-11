# MT-1.15-04 — Consolidate the Authorization Test Suite

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.15-04 |
| Title | Consolidate the authorization test suite |
| Parent WP | WP-1.15 — Core engine hardening (Milestone M1) |
| Requirements | NFR-04 (aligned errors), FR-SEC-01 (token verification), G-07 (privacy) |
| Priority | M |
| Dependencies | MT-1.2-01 (session auth), MT-1.2-04 (project scoping), MT-1.2-07 (authorization matrix tests — do not duplicate), MT-1.13-05 / MT-1.14-05 (attachment access paths), MT-1.15-01 (suite wiring pattern) |
| Parent sections | 9.2 (endpoint permissions), 12.2 (authn), 12.3 (authorization matrix), 19.1 (WP-1.15 fourth slice), 19.6, 20.4, 20.5 |

## Context
WP-1.15's fourth slice is "authorization": not new enforcement, but a consolidated
proof that every enforcement layer agrees with the plan's two contracts — the endpoint
permission column of Section 9.2 and the role/project authorization matrix of
Section 12.3 (Owner, ProjectMember(Developer/QA), Auditor, Admin; coder-only
workflows; cross-project denial). MT-1.2-07 already delivered matrix-driven tests
(`test_authorization_matrix.py`, token-missing/malformed/expired/wrong-key cases,
project-scoping table, `AUTH_FORBIDDEN_PROJECT` vs `AUTH_REQUIRED` derivation) and its
doc says "The WP-1.15 suite adopts it rather than duplicating it." Section 19.6's
single-implementation rule reinforces adoption over copy. This micro-task folds that
test file into the WP-1.15 CI gate, closes documented follow-ups (e.g. the MT-1.2-01
feature-flag follow-up when `AUTH_MODE=oidc`), and asserts the newer attachment
endpoints (WP-1.12/1.13/1.14) sit in the matrix.

## Inputs / Prerequisites
* MT-1.2-01 — session auth and the feature-flag follow-up (OIDC flag interactions).
* MT-1.2-04 — project scoping of claims; MT-1.2-07 — the matrix test file to adopt.
* MT-1.14-02 / MT-1.14-05 — attachment content endpoints whose permission rows must
  be in the matrix (Owner / agent-read-own-project; `AUTH_FORBIDDEN_PROJECT`).
* Parent plan Section 9.2 — endpoint permission table (the enumeration source).
* Parent plan Section 12.2 / 12.3 — authentication modes and the role matrix.
* Parent plan Section 18 — test strategy; Section 19.6 — no duplicate test logic.

## Scope (in)
* Adopt `test_authorization_matrix.py` (and its fixtures) into the WP-1.15 suite/CI
  gate; extract nothing that already exists — the suite entry points at the existing
  files.
* Extend the matrix enumeration to cover every Section 9.2 endpoint introduced since
  MT-1.2-07, notably the attachment endpoints from WP-1.12/1.13/1.14 (`Owner` and
  agent-read-own-project rows; auditor read-only rows) — the matrix must stay
  exhaustive against the OpenAPI surface so a new endpoint without a row fails the
  suite (Section 19.6 engineering rule).
* Close the MT-1.2-01 follow-up: token behavior when the auth feature flag is
  (re)configured — add the flag-interaction cases the follow-up named, or record
  precisely why they belong to the OIDC WP instead.
* Keep the negative-path assertions MT-1.2-07 established: missing/malformed/expired/
  wrong-key tokens → `AUTH_REQUIRED`; valid token, wrong project →
  `AUTH_FORBIDDEN_PROJECT`; role below required → `ROLE_NOT_PERMITTED` /
  `SCOPE_VIOLATION` per the matrix (Section 9.2 catalog; Section 20.4 item 5).
* Wire into the WP-1.15 CI gate; changelog note (Section 20.4 item 7).

## Out of scope
* Implementing enforcement — MT-1.2-01 / MT-1.2-04 / MT-1.2-07 own the code; this
  task consolidates and extends proof only.
* OIDC implementation and its full matrix — WP-1.3 (Section 19; flag-interaction
  cases here are limited to what MT-1.2-01's follow-up named).
* Claim/sweeper/idempotency/coverage slices — MT-1.15-01 / 02 / 03 / 05.
* Rate limiting / `RATE_LIMITED` behavior — NFR-06, monitored separately (Section 17).

## Target paths
* `backend/tests/auth/test_authorization_matrix.py` (extended enumeration + flag cases)
* WP-1.15 suite entry / CI job wiring (pointing at `backend/tests/auth/`)
* WP-1.15 changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] The consolidated authorization suite runs green in CI as part of the WP-1.15
  gate — WP-1.15 fourth slice (Section 19.1).
- [ ] The matrix enumerates every Section 9.2 endpoint × the Section 12.3 roles,
  including the WP-1.12/1.13/1.14 attachment endpoints; a missing row fails the test
  (Section 19.6; G-07 cross-project denial).
- [ ] Negative paths assert catalog codes `AUTH_REQUIRED`,
  `AUTH_FORBIDDEN_PROJECT`, `ROLE_NOT_PERMITTED` / `SCOPE_VIOLATION` with correct
  HTTP statuses (Section 9.2; Section 20.4 item 5).
- [ ] MT-1.2-07's tests are adopted, not duplicated; the MT-1.2-01 flag follow-up is
  closed or explicitly deferred with rationale (Section 19.6).
- [ ] No secrets or environment-specific paths committed; sessions/tokens in fixtures
  are test-only (Section 20.4 item 3).
- [ ] Changelog note added (item 7).

## Test command
`pytest backend/tests/auth/test_authorization_matrix.py -v`; combined WP-1.15 gate:
`pytest backend/tests/concurrency backend/tests/idsempotency backend/tests/auth -q`
green.

## Attachments
* [Section 12.3 — Authorization matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — Endpoint permission columns](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.15 fourth slice](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* An "exhaustive against OpenAPI" enumeration is only as fresh as the schema — tie
  the matrix test to the generated OpenAPI document (MT-1.1-04) so adding an endpoint
  without a permission row breaks the suite rather than passing silently.
* The `AUDITOR_SAME_AS_CODER` catalog code belongs to a workflow rule, not a matrix
  row — if the matrix suite asserts it, keep it in the coder-workflow test
  (MT-1.2-07 territory) to avoid confusing authorization with workflow validation.
* Feature-flag interaction testing can drift into WP-1.3's OIDC scope; if the
  follow-up cases require an OIDC issuer to construct, defer them with an explicit
  changelog note instead of stubbing fake OIDC behavior.
