# MT-2.2-02 — Validate the Manifest Against the Published Schema and Version

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.2-02 |
| Title | Validate the manifest against the published schema and version |
| Parent WP | WP-2.2 — Manifest discovery and session binding (Milestone M2) |
| Requirements | FR-MCP-02, FR-SEC-01 (auth boundary precondition) |
| Priority | M |
| Dependencies | MT-2.2-01 (discovered manifest), MT-1.1-04 (OpenAPI/schema pipeline conventions), WP-2.12 (writer producing valid manifests) |
| Parent sections | 10.3 (step 2 + version compatibility at startup), 10.11 (API version header), 19.1 (WP-2.2 second slice), 20.4, 20.5; Appendix B (B-01) |

## Context
Section 10.3's step 2: the manifest is "validated against a published schema and
version compatibility checked." Its startup note adds the second check: "API version
compatibility checked at startup via header." Section 10.11 ties compatibility to an
API version header; Appendix B B-01 records "client-backend API contract versioning"
as a known gap with a fast-follow ADR — meaning the version field and comparison rule
exist in the manifest flow but the full contract-versioning scheme is deferred. WP-2.2
lists "schema validation and version check" as its second slice: a manifest that
fails either check must abort before any token or session work (MT-2.2-03 … 05 sit
downstream of this gate). Correctness matters symmetrically: a *too-strict* validator
breaks WP-2.12-generated manifests, a *too-loose* one lets a future/foreign manifest
drive a session the backend will reject mid-flight.

## Inputs / Prerequisites
* MT-2.2-01 — manifest path and parsed JSON handed to validation.
* MT-1.1-04 — the repo's schema publication/CI conventions (the manifest schema
  should follow the same "published artifact, diff-reviewed" discipline as the
  OpenAPI document).
* WP-2.12 — writes manifests; its output is the conformance fixture this validator
  must accept.
* Parent plan Section 10.3 — the two checks; Section 10.11 — API version header;
  glossary `orchestrator.json` (filename and role).
* Parent plan Appendix B B-01 — deferred contract-versioning ADR (scope boundary for
  this task).

## Scope (in)
* Structural validation of the discovered manifest against the published
  `orchestrator.json` schema: required fields per Section 10.3's binding needs —
  project id, API/manifest version, and whatever fields the session flow
  (MT-2.2-04) and mismatch check (MT-2.2-05) consume; reject unknown major-version
  and malformed documents.
* Version compatibility check as a discrete, testable step: parse the declared
  version, compare against the bridge's supported range (Section 10.3 "version
  compatibility checked"; Section 10.11's startup check), and abort with a clear
  message on incompatibility — distinguishable from a structural error in the message
  so users know whether to fix the file or upgrade the bridge.
* Fail-fast placement: validation runs immediately after discovery (Section 10.3
  step ordering) and before token loading/session open — no credentials touched on
  an invalid manifest (FR-SEC-01 hygiene).
* Errors use the bridge's structured logging (MT-2.1-03) plus a non-zero exit /
  raised boundary error from the entry point (MT-2.1-04); no invented HTTP codes —
  this is a local CLI failure, not an API response (Section 9.2 catalog applies only
  to backend responses).
* The schema itself is checked into the repo as the single source for both this
  validator and MT-2.12-01's writer (one schema, two consumers — Section 19.6);
  schema changes go through diff review (Section 20.4 item 4).
* Tests: valid WP-2.12-produced manifest passes; missing required field; wrong type;
  unsupported version; newer-minor/older-major boundary cases per the chosen range;
  changelog note (item 7) recording the range rule and pointing at B-01.

## Out of scope
* Locating the manifest — MT-2.2-01; token and session steps — MT-2.2-03 / 04;
  project id comparison — MT-2.2-05.
* Authoring or fetching the "published schema" from a remote registry — the plan says
  published (schema shipped with the bridge / repo `schemas/`), not fetched at
  runtime; do not add network schema fetches.
* The full client-backend API contract-versioning scheme — Appendix B B-01 fast-follow
  ADR (raise `OQ-15+` only if this task cannot define a safe version range without
  it).
* Backend-side manifest schema endpoints — M1 API WPs.

## Target paths
* `bridge/` manifest-validation module (adjacent to MT-2.2-01's discovery module)
* The `orchestrator.json` schema file (shared with WP-2.12's writer; follow the
  Section 1.1.1 schema conventions / `schemas/` location)
* `bridge/tests/` (valid, malformed, version-boundary fixtures; conformance with a
  WP-2.12-generated manifest)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] Every discovered manifest is validated against the published schema before any
  token or session work — Section 10.3 step 2 (FR-MCP-02); invalid manifests abort
  fail-fast (FR-SEC-01 precondition).
- [ ] Version compatibility is checked separately with a clear, distinguishable
  error for "malformed file" vs "unsupported version" — Section 10.3; Section 10.11.
- [ ] One schema file is the shared source for validator and WP-2.12's writer; schema
  diff reviewed (Section 19.6; Section 20.4 item 4).
- [ ] A manifest written by MT-2.12-01 passes validation (round-trip conformance
  test) — WP-2.2/WP-2.12 coupling proven.
- [ ] Version range rule recorded in the changelog with an Appendix B B-01 reference
  (item 7); tests, lint and type check green in CI (item 2); no secrets (item 3).

## Test command
`uv run --directory bridge pytest tests/test_manifest_validation.py -v` — valid
fixture, missing field, wrong type, version boundary cases, error-message
discrimination, WP-2.12 round-trip; `uv run --directory bridge ruff check .` green.

## Attachments
* [Section 10.3 — Validation and version compatibility](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.11 — Startup API version check](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Appendix B — B-01 contract versioning gap](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan does not enumerate the manifest's fields in one authoritative list —
  Section 10.3's narrative (project id, version) plus whatever WP-2.12's writer emits
  is the de facto contract. Freeze the field set in the shared schema early and note
  any field this task adds beyond the narrative in the changelog; if genuinely
  unspecified (e.g. display name, agent id), raise a new OQ (`OQ-15+`).
* Version-range semantics (semver? integer?) are unstated — pick the simplest rule
  consistent with the API version header (Section 10.11), document it, and let
  B-01's ADR supersede it rather than pre-building a compatibility matrix.
* A validator shared with the writer can mask writer bugs (same schema, same
  misunderstanding) — keep at least one hand-written "known-good" fixture from the
  plan's Section 10.3 example, independent of the writer.
