# MT-2.2-05 — Abort on Project Mismatch with a Clear Message

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.2-05 |
| Title | Abort on project mismatch with a clear message |
| Parent WP | WP-2.2 — Manifest discovery and session binding (Milestone M2) |
| Requirements | FR-SEC-01 (server-verified binding), FR-MCP-02 (repo-bound session), FR-SEC-04 |
| Priority | M |
| Dependencies | MT-2.2-01 (manifest project id), MT-2.2-04 (session open / backend verification), MT-1.2-07 (project enforcement precedent) |
| Parent sections | 10.3 (step 3, binding rule), 12.2/12.3 (project scope), 19.1 (WP-2.2 acceptance, second half), 20.4, 20.5 |

## Context
The binding rule in Section 10.3 is explicit: the backend "verifies that the token's
project matches the manifest's `project_id` — **mismatch aborts**." WP-2.2's
acceptance states the test: "repo subfolder binds correctly; wrong-project token
aborts with clear message." Two sides must cooperate: the backend rejects a token
scoped to another project (server-side verification, FR-SEC-01 — the authoritative
check, exercised when MT-2.2-04's session open returns `AUTH_FORBIDDEN_PROJECT` or
equivalent), and the bridge converts that rejection (and any locally detectable
mismatch) into an unambiguous startup abort the user can act on — naming the
manifest's project, the token's effective project where known, and the remedy (re-run
init or point the config at the right token) without leaking either value. This is
the failure half of per-repo binding (FR-MCP-02): discovery binds the right project
or refuses to run.

## Inputs / Prerequisites
* MT-2.2-01 — manifest and its `project_id`; MT-2.2-02 — manifest validated.
* MT-2.2-04 — session open; the backend's mismatch rejection arrives there
  (server-side authority per FR-SEC-01).
* MT-1.2-07 — backend-side project enforcement behavior and the
  `AUTH_FORBIDDEN_PROJECT` semantics (consistent message expectations).
* Parent plan Section 10.3 — the binding sentence this implements; Section 12.2/12.3
  — token project scope and cross-project denial.
* MT-2.1-03 — structured logging for the abort record; MT-2.1-04 — entry-point
  non-zero exit.

## Scope (in)
* A single abort path invoked whenever binding fails, producing: a human-readable
  message (clear-message requirement of WP-2.2 acceptance) that states manifest
  project id, states that the credential does not match it (including the backend's
  canonical code when the rejection came from the server — `AUTH_FORBIDDEN_PROJECT`),
  and names the remedies (point config at the token issued for this repo's project,
  or re-run `orchestrator init` in the right repo); non-zero entry-point exit;
  structured log with correlation id (MT-2.1-03), **no token value, no
  Authorization header** (FR-SEC-04; Section 17).
* Backend-driven mismatch (the common case): map the session-open rejection from
  MT-2.2-04 into this abort — one user-facing message for both detection paths so
  the UX does not fork.
* Optional local cross-check: if the user-level config (or init metadata) records
  which project the stored token was issued for, compare before the network call and
  abort early with the same message; **only** if such metadata exists from
  MT-2.12-02 — never parse or decode the token to extract a project (Section 12.2
  tokens are opaque bearer values to the client).
* Tests: backend-403-at-open → abort message + code + non-zero exit; early local
  mismatch (when metadata available) → same message; matching project → no abort
  (control); message contains no token bytes (assert fixture token not in output);
  changelog note (Section 20.4 item 7).

## Out of scope
* Backend-side verification implementation — FR-SEC-01 lives in M1 (MT-1.2-03 /
  MT-1.2-07); this task consumes its rejection.
* Multi-project tokens or cross-project access grants — Section 12.3 does not define
  them; binding is one token ↔ one project (raise `OQ-15+` if a real use case for
  multi-project agent tokens emerges later).
* Changing the manifest, token, or session mechanics — MT-2.2-01 … MT-2.2-04.
* Web/mobile project-switcher UX — WP-4.x.
* Permission errors *within* a correctly bound project (role denials) — those are
  Section 12.3 `ROLE_NOT_PERMITTED`/`SCOPE_VIOLATION` outcomes during tool calls
  (WP-2.4+), not startup binding failures.

## Target paths
* `bridge/` session/binding module — the abort path wired to MT-2.2-04's open call
* `bridge/tests/` (mismatch abort, control, redaction tests; entry-point exit code)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] A token whose project does not match the manifest's `project_id` aborts bridge
  startup with a clear, remedy-bearing message — Section 10.3 binding rule;
  WP-2.2 acceptance second half verbatim (FR-MCP-02).
- [ ] The abort surfaces `AUTH_FORBIDDEN_PROJECT` when the backend rejected the open
  (Section 9.2 catalog; Section 20.4 item 5) and exits non-zero (MT-2.1-04).
- [ ] No token value or Authorization header appears in the message or logs
  (FR-SEC-04; Section 17) — asserted against a fixture token.
- [ ] Matching-project control path opens the session normally (no false abort).
- [ ] The bridge never decodes the token to determine its project (opaque bearer per
  Section 12.2) — local pre-check uses init-recorded metadata only, if it exists.
- [ ] Tests, lint and type check green in CI (Section 20.4 item 2); no secrets
  committed (item 3); changelog note added (item 7).

## Test command
`uv run --directory bridge pytest tests/test_project_mismatch.py -v` — backend-403
abort (message/code/exit), early local mismatch, matching control, fixture-token
non-leak assertion; `uv run --directory bridge ruff check .` green; combined with the
WP-2.2 suite: `uv run --directory bridge pytest -q`.

## Attachments
* [Section 10.3 — Binding rule (mismatch aborts)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-2.2 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-SEC-01 — Server-side token verification](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The "clear message" must not defeat the security goal: naming the manifest's
  project id is fine (it is repo-visible), but never echo the token or any derived
  claim — test with a distinctive fixture string.
* Whether the backend's rejection message itself reveals the token's project is the
  backend's call (M1); if it does not, the bridge message must still be actionable
  ("token is not valid for project X") — phrase from the manifest side, not from
  token internals.
* If MT-2.12-02 declines to record issued-project metadata, the early local check
  disappears and every mismatch costs a network round trip — acceptable per plan
  (server is authoritative); record the design outcome in the changelog so WP-2.12
  does not assume a local pre-check exists.
