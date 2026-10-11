# MT-2.9-04 — Write the two-connections cross-project isolation test

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.9-04 |
| Title | Write the two-connections cross-project isolation test |
| Parent WP | WP-2.9 — HTTP/SSE transport with per-connection binding (Milestone M2) |
| Requirements | FR-MCP-06, FR-MCP-01; NFR-04 |
| Priority | M |
| Dependencies | MT-2.9-01..03 (server, binding, lifecycle complete); WP-2.2, WP-2.4 (sessions and tools under test) |
| Parent sections | 10.2, 10.3, 18 (E2E/Integration rows), 19 (WP-2.9), 20.4, 20.5 |

## Context
WP-2.9's acceptance criterion is a behavioral guarantee: "two simultaneous
connections for different projects never share state." Section 18's e2e list includes
a "cross-project access attempt" scenario, and FR-MCP-06 requires local rejection of
cross-project requests backed by backend token scoping. This final slice of WP-2.9
proves the guarantee: two live HTTP/SSE connections bound to two different projects
run interleaved tool traffic, and every observable — cached context, tool results,
session identity — stays on its own side of the boundary, while a deliberate
cross-project attempt fails with a catalog code.

## Inputs / Prerequisites
* MT-2.9-01..03 — the HTTP/SSE server, binding and lifecycle under test.
* Parent plan Section 9.2 — endpoints exercised: `POST /agent-sessions`,
  `GET /projects/{pid}/work`, `POST /tasks/{id}/claim` (via tools).
* Parent plan Section 18 — e2e row: cross-project access attempt; integration row:
  multi-connection scenarios.
* Two project fixtures with two project-scoped agent tokens (test doubles or seeded
  backend, per Section 18 test environments).
* WP-2.4 tools — `get_project_context`, `get_available_tasks`, `claim_task` as the
  observation probes.

## Scope (in)
* An integration/e2e test opening two simultaneous HTTP/SSE connections: connection
  A bound to project 1 (URL path + token), connection B to project 2.
* Interleaved traffic proving isolation: `get_project_context` on each returns its
  own project's name/rules; `get_available_tasks` on each returns only its own
  project's tasks; a claim on A's task is invisible to B's listings.
* Negative path: an attempt to point connection A at project 2's URL (or token)
  is rejected locally with `AUTH_FORBIDDEN_PROJECT`/mismatch handling per
  MT-2.9-02, and a tool call carrying project-2 data on connection A yields a
  structured rejection — the FR-MCP-06 two-barrier demonstration.
* Session identity check: the backend sessions opened for A and B are distinct
  (via mocked/observable session endpoints in the test harness).
* Teardown check: closing A (MT-2.9-03 cleanup) leaves B fully functional.

## Out of scope
* Implementing server/binding/lifecycle — MT-2.9-01..03 (this task only tests them).
* Backend token scoping internals — WP-1.x (observed through behavior only).
* STDIO mode isolation — WP-2.2 tests.
* Real agent clients driving the connections — WP-2.11 conformance.

## Target paths
* `bridge/tests/` (isolation integration/e2e test)
* CI pipeline config (invocation alongside integration tests, if not auto-discovered)
* WP changelog entry

## Acceptance criteria
- [ ] Two simultaneous connections on different projects complete interleaved tool
  calls with zero state crossover — context, listings and claim visibility asserted
  per project (WP-2.9 acceptance).
- [ ] A cross-project attempt is rejected locally with a Section 9.2 code
  (`AUTH_FORBIDDEN_PROJECT` or mismatch rejection per MT-2.9-02) before any
  cross-project data is returned (FR-MCP-06 first barrier).
- [ ] Closing connection A does not disrupt connection B (lifecycle cleanup,
  MT-2.9-03).
- [ ] The test runs against the real multi-connection server (not a mocked
  transport), in CI (Section 20.4 item 2, Section 18 e2e row).
- [ ] Only catalog codes appear; no fabricated codes (Section 20.4 item 5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the isolation test, e.g. `uv run pytest bridge/tests/ -k cross_project_isolation`
(or the e2e runner entry for this scenario); it requires the integration backend per
Section 18.

## Attachments
* [Section 19 — WP-2.9 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Tests that use two projects but sequential traffic prove nothing — the test must
  interleave the connections; keep the timing genuinely concurrent (barrier/latch,
  not `sleep` ordering).
* If isolation fails, the defect is likely module-level state inherited from WP-2.2
  or WP-2.4; record the failing surface in the changelog so the fix lands in the
  owning module, not in the test.
