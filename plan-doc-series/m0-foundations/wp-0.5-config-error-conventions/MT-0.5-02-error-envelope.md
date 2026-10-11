# MT-0.5-02 — Publish the Canonical Error Envelope and Error-Code Catalog

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.5-02 |
| Title | Publish the canonical error envelope and error-code catalog from parent plan 9.2 |
| Parent WP | WP-0.5 — Configuration, secrets and error conventions (Milestone M0) |
| Requirements | NFR-11, NFR-12 |
| Priority | M |
| Dependencies | MT-0.4-01 (WP-0.4 complete; error-related decisions settled) |
| Parent sections | 9.2, 12.1, 19.1 (WP-0.5), 20.4 (item 5), 20.5 |

## Context
Section 9.2 fixes the standard error envelope for all non-2xx responses and the
canonical error-code catalog, and Section 20.4 item 5 makes "error codes exist in the
catalog" a global definition-of-done check for every micro-task. WP-0.5's slice "error
codes catalog" publishes these as a conventions reference so backend, bridge, web and
mobile all map errors identically — the bridge especially needs canonical codes to
translate API failures into tool errors (WP-2.3).

## Inputs / Prerequisites
* Parent plan Section 9.2 — the error envelope JSON shape and the full canonical code
  list (`AUTH_REQUIRED` … `SERVER_ERROR`, 19 codes), plus the REST surface each code
  can originate from.
* Parent plan Section 20.4 item 5 — global DoD: error codes used must exist in the
  catalog.
* WP-0.4 decisions — nothing in Section 22 changes the catalog, but confirm during the
  session notes review.
* ADR-005 (DRF + OpenAPI) — the envelope must be expressible in the OpenAPI document
  generated in WP-1.1.

## Scope (in)
* Publish the error-conventions section of the WP-0.5 conventions document: the
  envelope fields (code, message, retryable, details, correlation_id) referenced from
  Section 9.2 by pointer, not re-derived.
* List all 19 canonical error codes as the authoritative catalog, noting that new codes
  may only be added here first (Section 20.4 item 5 discipline).
* Define the rules the catalog implies: codes are stable API contract; messages are
  human-readable and not parsed by clients; `retryable` drives client/bridge retry
  behavior (connects to NFR-12 and ADR-012).
* State the OpenAPI obligation: the envelope becomes a reusable schema in the generated
  OpenAPI document when the backend lands (WP-1.1), and schema diffing guards changes
  (NFR-11).
* Reference the document from backend, bridge, web and mobile package docs
  (WP-0.5 acceptance).
* Add a WP changelog note.

## Out of scope
* HTTP status mapping per endpoint — defined by the OpenAPI contract in WP-1.1, not
  invented here.
* Implementing the envelope in Django exception handlers — WP-1.1/WP-1.15.
* Bridge error-to-tool-error mapping — WP-2.3 (consumes this catalog).
* Web/mobile error UI handling — WP-4.x / WP-5.x.
* Correlation-id field semantics inside the envelope — MT-0.5-03.

## Target paths
* `docs/plan/conventions/error-envelope.md` (envelope + canonical code catalog section
  of the WP-0.5 conventions document)
* `backend/`, `bridge/`, `web/`, `mobile/` package docs or configs (reference added)
* WP changelog entry

## Acceptance criteria
- [ ] The conventions document states the envelope shape by reference to Section 9.2
  with its five fields.
- [ ] All 19 canonical codes from Section 9.2 appear in the catalog, with none added,
  dropped or renamed.
- [ ] The "add a code here first" rule is documented as part of the global DoD.
- [ ] The document is referenced from backend, bridge, web and mobile package docs
  (WP-0.5 acceptance).
- [ ] No invented codes or envelope fields beyond Section 9.2 (Section 20.5
  traceability).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Grep the conventions document for each of the 19 canonical codes (e.g. search for
`TASK_ALREADY_CLAIMED`, `SERVER_ERROR`, and the rest) and confirm the count matches
Section 9.2 exactly; confirm each package doc contains a link to the conventions
document.

## Attachments
* [Section 9.2 — REST API surface and error envelope](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 20.4 — Global definition of done](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Copy drift: re-typing the catalog invites typos — verify against Section 9.2 line by
  line; the plan stays authoritative (Section 0).
* Some codes (e.g. `RATE_LIMITED`, `VERSION_CONFLICT`) have no implementation until
  later WPs; the catalog must not be pruned to only "currently used" codes.
