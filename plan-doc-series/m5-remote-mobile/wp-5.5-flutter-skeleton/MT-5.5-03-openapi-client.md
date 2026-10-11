# MT-5.5-03 — Generate the typed API client from the shared OpenAPI schema

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.5-03 |
| Title | Generate the typed API client from the shared OpenAPI schema |
| Parent WP | WP-5.5 — Flutter skeleton and API client (Milestone M5) |
| Requirements | NFR-11 (OpenAPI as the single source for web and mobile clients); ADR-005 |
| Priority | M |
| Dependencies | MT-5.5-01 (scaffold), MT-5.5-02 (resolved base URL), WP-1.1 (generated OpenAPI document), WP-4.1 (web-side precedent) |
| Parent sections | 13.3 (client discipline mirrored), 14.3, 18 (Contract row), 19 (WP-5.5), 20.4, 20.5 |

## Context
NFR-11 names the rule: the typed OpenAPI contract is the single source for web and
mobile clients — mobile must consume the same generated schema the web app does
(ADR-005: DRF with generated OpenAPI as the contract; Section 14.3: "generated API
client from the same OpenAPI schema"). WP-5.5's deliverable "client generation" is
this slice: a reproducible generation step producing Dart types and request/response
models for every endpoint the mobile app uses, plus the contract check that fails CI
when the schema and generated code drift (Section 18 contract layer: "generated
clients compile against it").

## Inputs / Prerequisites
* Parent plan ADR-005 — generated OpenAPI document is the contract (Section 23).
* Parent plan Section 9.2 — endpoint surface the client must cover (auth, devices,
  projects, tasks, work, checkpoints, resolutions, reviews, events stream,
  dashboard).
* Parent plan Section 14.3 — generated client from the same OpenAPI schema.
* Parent plan Section 18 — Contract row; WP-0.3 CI pipeline.
* WP-1.1 — the backend's generated OpenAPI document; MT-5.5-02 — base-URL config
  the client is constructed from.

## Scope (in)
* A pinned code-generation setup (generator, version, config) producing a Dart
  client from the backend's OpenAPI document, committed under `mobile/` with a
  documented regeneration command runnable locally and in CI.
* Client construction wired to the MT-5.5-02 resolved config (base URL injected, no
  committed endpoints — Section 20.4 item 3).
* Uniform handling of the Section 9.2 error envelope: non-2xx responses deserialize
  into a typed error carrying `code`, `message`, `retryable`, `details`,
  `correlation_id`, exposed through one client-level error mapping point (so later
  screens map codes to friendly messages per Section 13.3's mobile equivalent).
* Idempotency-header support for mutating calls in the generated/wrapped client
  surface (Section 9.2, NFR-12) — as a client option the app's mutation layer sets.
* CI checks: regeneration is deterministic (regenerate and diff must be clean) and
  the client compiles (`flutter analyze`) — drift fails the pipeline (Section 18
  contract row).

## Out of scope
* Hand-written repository/business logic on top of the client — per-feature WPs
  (5.6-5.8).
* The OpenAPI document itself — WP-1.1.
* Web client generation — WP-4.1.
* Login/device-registration flows using the client — MT-5.5-06; SSE — MT-5.5-05
  (events stream is transport, not the REST client).
* Backend endpoint changes — any gap found is reported, not worked around.

## Target paths
* `mobile/` (generator config; generated client sources)
* `mobile/` docs or README (regeneration command)
* CI pipeline config (regenerate-and-diff + analyze checks)
* WP changelog entry

## Acceptance criteria
- [ ] The client is generated from the backend's ADR-005 OpenAPI document — no
  hand-authored endpoint models — and a documented command reproduces it exactly
  (NFR-11, Section 14.3).
- [ ] Regeneration determinism is CI-enforced: diff-after-regenerate fails on
  drift (Section 18 contract row).
- [ ] Error envelope deserializes into the five Section 9.2 fields at one mapping
  point; a fixture non-2xx response proves `code` survives intact (Section 9.2,
  Section 20.4 item 5).
- [ ] Mutating calls can carry an idempotency key header as the contract defines
  (Section 9.2, NFR-12).
- [ ] The client is constructed from resolved flavor config with no committed
  endpoints (MT-5.5-02, Section 20.4 item 3).
- [ ] `flutter analyze` and tests green in CI (Section 20.4 item 2); changelog note
  added (item 7).

## Test command
From `mobile/`, run regeneration + diff (documented command) then
`flutter analyze` and `flutter test`; the CI job repeats regenerate-and-diff to
enforce contract drift detection.

## Attachments
* [Section 23 — ADR-005](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan does not prescribe a Dart generator — pick a maintained one, pin its
  version, and record the choice in the changelog; unpinned generators produce
  noisy diffs that teams learn to ignore.
* If the schema lags mobile needs (endpoint gaps), resist local model patches —
  they break NFR-11; report the gap for the backend WP instead.
