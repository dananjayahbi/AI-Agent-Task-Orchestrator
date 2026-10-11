# MT-1.6-07 — Implement Claim and Release REST Endpoints

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.6-07 |
| Title | Implement claim and release REST endpoints |
| Parent WP | WP-1.6 — Lease and claim service (Milestone M1) |
| Requirements | FR-LEA-01, FR-LEA-06, NFR-11, NFR-12, ADR-005, ADR-012 |
| Priority | M |
| Dependencies | MT-1.6-01, MT-1.6-04, MT-1.6-05, MT-1.6-06 (services complete); MT-1.5-04 |
| Parent sections | 9.2 (Agent work endpoints), 10.5 (`claim_task` / `release_task`), 19 (WP-1.6), 20.4, 20.5 |

## Context
Section 9.2 places three Agent-facing endpoints in the v1 surface:
`GET /projects/{pid}/work` (available tasks, `role`, filters), `POST /tasks/{id}/claim`
and `POST /tasks/{id}/release`. This task exposes the MT-1.6-01/02/04 services over
HTTP with the plan-wide contracts: project resolved from the token (never the body),
canonical error envelope, idempotency-key header on mutating calls, and an OpenAPI
document that stays schema-diffed (ADR-005, NFR-11). The bridge's `claim_task` and
`release_task` tools (WP-2.4/WP-10.5 catalog) call exactly these endpoints.

## Inputs / Prerequisites
* MT-1.6-01 (claim), MT-1.6-02 (next-available selection), MT-1.6-04 (release),
  MT-1.6-05 (fencing), MT-1.6-06 (limit) — service layer complete.
* Parent plan Section 9.2 — endpoint table rows "Agent work" and the standard error
  envelope; caller = Agent (project-scoped token, Section 12.2).
* Section 8.6 — the claim response returns the lease record JSON shape;
  Section 10.6 — claim carries the rules block.
* WP-0.5 conventions — error envelope (MT-0.5-02), correlation/idempotency headers
  (MT-0.5-03).
* WP-1.1 — DRF + generated OpenAPI (ADR-005).

## Scope (in)
* Implement `POST /tasks/{id}/claim`: agent auth via project-scoped token; body/params
  per the claim contract (session id, role, worker label); 200 returns task details,
  lease record (Section 8.6 shape, including `lease_generation`) and rules block;
  errors `TASK_ALREADY_CLAIMED`, `TASK_NOT_FOUND`, `AUTH_FORBIDDEN_PROJECT`,
  `TASK_STATE_CONFLICT`, `DEPENDENCY_UNMET`, `CONCURRENCY_LIMIT_REACHED`,
  `VERSION_CONFLICT` from the catalog with the Section 9.2 envelope.
* Implement `POST /tasks/{id}/release`: owner-session check via MT-1.6-04; 200
  returns the updated task; `LEASE_NOT_OWNED` / `LEASE_EXPIRED` /
  `TASK_STATE_CONFLICT` on refusals.
* Implement `GET /projects/{pid}/work`: available (`pending`) tasks with `role` and
  filters, priority-then-creation ordering (MT-1.6-02), project from token.
* Idempotency-key handling on both mutating endpoints (Section 9.2, ADR-012,
  NFR-12); correlation id in every response envelope (WP-0.5-03).
* Update the generated OpenAPI document; schema diff reviewed (Section 20.4 item 4).
* Permission tests: cross-project token → `AUTH_FORBIDDEN_PROJECT`; owner session
  allowed on release override; anonymous → `AUTH_REQUIRED`.
* Add a WP changelog note.

## Out of scope
* The bridge tools and their schemas — WP-2.4 (they call these endpoints).
* Rate limiting implementation — WP-1.2.
* Checkpoint endpoints — WP-1.8; submission endpoints — WP-2.6.
* Auditor claim endpoints (T11) — WP-3.3.
* Web UI consumers — WP-4.x (agents panel reads, does not claim).

## Target paths
* `backend/apps/leases/` (serializers, views, permission wiring for the three
  endpoints)
* `schemas/openapi` generated snapshot (contract update)
* `backend/tests/` (endpoint and permission tests)
* WP changelog entry

## Acceptance criteria
- [ ] All three Section 9.2 Agent-work endpoints exist with the documented callers
  and paths, and appear in the generated OpenAPI document (ADR-005, NFR-11).
- [ ] Claim 200 body contains task details, the Section 8.6 lease JSON (including
  `lease_generation`) and the rules block (Section 10.6).
- [ ] Every non-2xx response uses the Section 9.2 envelope with a catalog code
  (Section 20.4 item 5); cross-project access returns `AUTH_FORBIDDEN_PROJECT`
  (Section 12.2, WP-1.2 acceptance pattern).
- [ ] Mutating endpoints accept and honor the idempotency key: a retried identical
  claim returns the original outcome without a second lease (NFR-12, ADR-012).
- [ ] OpenAPI schema diff reviewed; no contract change lands unreviewed
  (Section 20.4 item 4).
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k claim_release_endpoints -q` (API tests covering success
shapes, all catalog error paths, idempotent retry and the authorization matrix) and
regenerate/validate the OpenAPI snapshot per the WP-0.3 contract job; full suite
stays green.

## Attachments
* [Section 9.2 — REST API surface](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Tool catalog (`claim_task`, `release_task`)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Endpoint contracts are consumed by the bridge (WP-2.4) and conformance tests
  (WP-2.11) — freeze shapes in the OpenAPI snapshot here; any divergence between
  Section 9.2 and implementation needs an OQ, not a silent extension.
* Idempotency-key storage/replay semantics come from WP-0.5-03 — reuse them
  verbatim; a second mechanism would violate NFR-12's uniformity.
* Response latency: claim must meet NFR-02 (p95 under 300 ms locally) — measure in
  WP-1.15, but avoid extra round trips inside the claim transaction here.
