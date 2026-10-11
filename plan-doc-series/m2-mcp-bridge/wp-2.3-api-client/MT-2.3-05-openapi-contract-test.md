# MT-2.3-05 — Write the contract test against the OpenAPI schema

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.3-05 |
| Title | Write the contract test against the OpenAPI schema |
| Parent WP | WP-2.3 — Backend API client (Milestone M2) |
| Requirements | NFR-11 (OpenAPI as single source), NFR-04; ADR-005 (DRF with generated OpenAPI as the contract) |
| Priority | M |
| Dependencies | MT-2.3-01..04 (client behavior complete); WP-1.1 (generated OpenAPI document) |
| Parent sections | 10.11, 18 (Contract row), 19 (WP-2.3), 20.4, 20.5 |

## Context
Section 18 lists contract testing as a first-class layer: "OpenAPI schema validation;
MCP tool schemas; manifest schema; generated clients compile against it — prevents
web/mobile/bridge drift." ADR-005 makes the generated OpenAPI document the contract,
and NFR-11 makes it the single source for typed clients. WP-2.3's last slice proves
the bridge client's requests and response handling match that contract, so backend
changes that break the bridge are caught in CI rather than in a live agent session.

## Inputs / Prerequisites
* Parent plan Section 9.2 — endpoint surface, error envelope, cursor pagination,
  idempotency header; the OpenAPI document generated from it in WP-1.1 (ADR-005).
* Parent plan Section 18 — Contract test layer and quality gates.
* Parent plan Section 10.11 — API version header compatibility check.
* MT-2.3-01..04 — the completed client under test.
* WP-0.5 conventions document — envelope and pagination conventions the schema must
  reflect.

## Scope (in)
* A contract test module that validates representative client requests and responses
  against the generated OpenAPI document: path/method correctness, required headers
  (auth, API version, idempotency on mutating calls), request body shapes, response
  schemas, and the Section 9.2 error envelope for non-2xx samples.
* Coverage of every endpoint the bridge client calls (sessions, work listing, claim,
  release, checkpoints, resolution, attachments read, project context, manifest).
* A failing-test path: if the OpenAPI document and the client disagree, the test
  names the endpoint and field so the drift is unambiguous.
* CI wiring so the contract test runs with the bridge suite (Section 18 quality
  gates).

## Out of scope
* Generating or editing the OpenAPI document — WP-1.1 (ADR-005).
* Web and mobile generated-client compile checks — WP-4.1, WP-5.5.
* MCP tool-schema contract checks — WP-2.4/WP-2.11 (Section 18 contract row).
* Manifest schema validation — WP-2.2.
* End-to-end scenarios — Section 18 e2e layer.

## Target paths
* `bridge/tests/` (contract test module)
* `schemas/` (read-only reference to the generated OpenAPI document, if the pipeline
  materializes it there)
* CI pipeline config (test invocation added)
* WP changelog entry

## Acceptance criteria
- [ ] The contract test validates each bridge-used endpoint against the ADR-005
  OpenAPI document and passes against the current backend (Section 18 contract row).
- [ ] Error-envelope samples for at least `AUTH_REQUIRED`, `TASK_ALREADY_CLAIMED`
  and `SERVER_ERROR` validate against the schema and preserve the canonical code
  (Section 9.2, Section 20.4 item 5).
- [ ] A deliberate client/schema mismatch (test fixture) makes the suite fail with a
  message naming the endpoint and field.
- [ ] The test runs in CI alongside lint, type check and unit tests
  (Section 20.4 item 2).
- [ ] No schema change is required by this task; if one is found, it is raised for
  review under Section 20.4 item 4 rather than edited unilaterally.
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the bridge contract suite, e.g. `uv run pytest bridge/tests/ -k contract`, and
confirm it passes against the OpenAPI document produced by WP-1.1.

## Attachments
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 23 — ADR-005](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The OpenAPI document may not exist yet if WP-1.1 lags — the test must fail with a
  clear "schema missing" message, not be skipped silently, or drift protection
  evaporates.
* Over-matching on optional response fields will cause false failures as the backend
  evolves; assert required structure, not exhaustive field lists.
