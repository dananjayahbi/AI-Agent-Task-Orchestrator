# MT-1.1-04 — Generate and Serve the OpenAPI Document, Validated in CI

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.1-04 |
| Title | Generate and serve the OpenAPI document, validated in CI |
| Parent WP | WP-1.1 — Django project skeleton (Milestone M1) |
| Requirements | NFR-11, NFR-07 |
| Priority | M |
| Dependencies | MT-1.1-01 (DRF project), MT-1.1-03 (routes to document), MT-0.3-01 (CI workflow), MT-0.5-02 (error envelope schema), MT-0.5-04 (pagination conventions) |
| Parent sections | 9.2, 18, 19.1 (WP-1.1), 20.4 (item 4), 20.5; ADR-005 |

## Context
WP-1.1's acceptance requires "OpenAPI served and validated in CI", and NFR-11 makes the
typed OpenAPI contract the single source for web and mobile clients. ADR-005 fixes DRF
with schema generation as the mechanism. Section 18 lists contract-layer checks
("OpenAPI schema validation … generated clients compile against it") among quality
gates, and Section 20.4 item 4 requires public contracts to be updated with the schema
diff reviewed. This task stands up the generation pipeline that every later
endpoint-adding micro-task will feed.

## Inputs / Prerequisites
* MT-1.1-01 — DRF-enabled ASGI project (ADR-005) and its routes, including health
  (MT-1.1-03).
* MT-0.5-02 — the canonical error envelope, which becomes a reusable schema in the
  generated document (an explicit obligation recorded there).
* MT-0.5-04 — cursor-based pagination conventions that list responses follow.
* Parent plan Section 9.2 — resource-oriented, OpenAPI-documented surface under
  `/api/v1`; the document must describe this shape as endpoints accumulate.
* Parent plan Section 18 — contract quality gate; Section 20.4 item 4 — schema diff
  reviewed when contracts change.
* MT-0.3-01 — the CI workflow that gains the schema-validation step.

## Scope (in)
* Configure DRF schema generation (ADR-005) to produce the OpenAPI document covering
  the `/api/v1` surface implemented so far (health/Ops routes included).
* Serve the generated document from the backend (URL declared in Section 9.2's spirit
  — the document itself is the contract; pick and document the serving path).
* Publish the generated document as a committed snapshot under `schemas/` per
  Appendix A (`schemas/` holds the OpenAPI snapshot).
* Add a CI step (extending the MT-0.3-01 workflow) that regenerates the document and
  fails when it drifts from the committed snapshot without a reviewed diff
  (Section 18 contract gate, Section 20.4 item 4).
* Represent the Section 9.2 error envelope as a reusable schema referenced by error
  responses, and the MT-0.5-04 pagination shape for list endpoints that exist.
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Generated clients for web/mobile — consumed by WP-4.x/WP-5.x; this task only
  publishes and validates the contract.
* Endpoints not yet implemented (auth, projects, tasks) — they extend this document as
  their own micro-tasks land.
* MCP tool schemas and manifest schema — WP-2.x and MT-1.3-05 respectively.
* Bridge contract tests against the document — WP-2.3.

## Target paths
* `backend/` — schema generation configuration and serving route
* `schemas/` — committed OpenAPI snapshot (Appendix A)
* `.github/workflows/` — schema validation step added to the existing CI workflow
* `backend/tests/` — contract tests (envelope schema present)
* WP changelog entry

## Acceptance criteria
- [ ] The OpenAPI document is generated from the DRF project and served by the backend
  (WP-1.1 deliverable).
- [ ] The document is committed under `schemas/` and CI fails on unreviewed drift
  (Section 18 contract gate; Section 20.4 item 4).
- [ ] The Section 9.2 error envelope appears as a reusable schema used by non-2xx
  responses (obligation recorded in MT-0.5-02).
- [ ] Pagination follows the MT-0.5-04 conventions for any list endpoint present.
- [ ] Error codes referenced in the document exist in the Section 9.2 catalog
  (Section 20.4 item 5).
- [ ] Lint, type check and tests green in CI (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Regenerate the document locally and diff against the snapshot (zero diff on a clean
tree); run `pytest backend/tests -k contract` to assert the envelope schema is present;
push a change that alters a route without updating the snapshot and confirm the CI
schema-diff job fails.

## Attachments
* [Section 9.2 — REST API surface](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and Quality Strategy (contract layer)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-005 — DRF with generated OpenAPI](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Which DRF schema extension is used is not named in the plan (ADR-005 says "DRF with
  schema generation") — choose one mature option, record it in the changelog, and pin
  it; swapping generators later is a contract-breaking event.
* The document's serving path is not fixed by Section 9.2 — decide once and record it,
  because the bridge (WP-2.3) and both clients will hardcode or discover it.
