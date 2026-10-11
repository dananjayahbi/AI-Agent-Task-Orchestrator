# MT-1.14-05 — Implement Format Error Handling (ATTACHMENT_NOT_READY, Unsupported Format)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.14-05 |
| Title | Implement format error handling (ATTACHMENT_NOT_READY, unsupported format) |
| Parent WP | WP-1.14 — Attachment retrieval API (Milestone M1) |
| Requirements | FR-ATT-04; NFR-04 (aligned error codes), G-07 |
| Priority | M |
| Dependencies | MT-1.14-02 (endpoint), MT-1.14-03 (page validation), MT-1.12-07 (status/retry states) |
| Parent sections | 9.2 (error catalog), 9.5, 19.1 (WP-1.14 acceptance), 20.4 (item 5), 20.5 |

## Context
WP-1.14's acceptance has two halves: all four format preferences per the Section 9.5
table (MT-1.14-02) and **"`ATTACHMENT_NOT_READY` while processing"**. Section 9.5
requires the same behavior at upload time — "status is processing; retrieving content
during processing returns 409 ATTACHMENT_NOT_READY" — and FR-ATT-04's supporting
clause makes unsupported-format failures explicit. The two codes are already in the
Section 9.2 catalog of 19 canonical codes (with their HTTP mappings), and Section
20.4 item 5 forbids codes outside that catalog. This micro-task completes WP-1.14's
error slice: exact status/code pairing for not-ready and unsupported-format cases,
`VALIDATION_ERROR` for bad parameters, all asserted in tests so the retrieval API's
failure surface is contract-locked.

## Inputs / Prerequisites
* MT-1.14-02 — content endpoint and format resolution (the call sites for these
  errors).
* MT-1.14-03 — page parameter validation (`VALIDATION_ERROR` interplay: a bad page
  on an otherwise-ready attachment).
* MT-1.12-07 — status values (`processing`, `ready`, `failed`) the endpoint branches
  on; `failed` attachments reuse the reason-carrying failure path (Section 9.5
  stage 5) rather than a new code.
* Parent plan Section 9.2 — catalog entry and HTTP status mapping; MT-0.5-02 — error
  envelope; MT-0.5-03 — header conventions on error responses.
* Parent plan Section 9.5 — "409 ATTACHMENT_NOT_READY" during processing.

## Scope (in)
* `ATTACHMENT_NOT_READY` (HTTP 409 per the catalog) whenever content is requested for
  an attachment in `processing` — both `auto` and every explicit format — with the
  standard envelope (MT-0.5-02) and a human-readable message consistent with
  Section 9.5's stage-5 message discipline.
* `ATTACHMENT_UNSUPPORTED_FORMAT` whenever a valid format preference cannot be
  satisfied for the attachment's type per the Section 9.5 table — at minimum:
  `image_base64` on a non-image (table wording) and `markdown`/`text_ocr` on content
  types that have no extracted/OCR representation; each case documented in the
  OpenAPI description.
* `VALIDATION_ERROR` for unknown `format` values, non-integer/out-of-range `page`
  and unknown query parameters (MT-0.5-04) — in scope here as the consolidated
  error-matrix slice so MT-1.14-02's behavior tests and these assertions do not
  diverge.
* `AUTH_FORBIDDEN_PROJECT` for cross-project access stays the catalog's project
  error (asserted in the matrix; implementation owned by MT-1.2-07's enforcement).
* Attachments in `failed` status: no new code — return the Section 9.5 reason-bearing
  failure using an existing catalog code (`ATTACHMENT_UNSUPPORTED_FORMAT` is wrong
  here); decide and document which catalog code covers `failed`-status reads, raising
  a new OQ (`OQ-15+`) if none fits, rather than inventing one (Section 20.4 item 5).
* Tests: one assertion per error branch (status code, catalog `code`, envelope
  shape); assert NO unknown codes appear anywhere in the retrieval path; OpenAPI
  updated with reviewed diff (Section 20.4 item 4); changelog note (item 7).

## Out of scope
* The happy-path format behaviors — MT-1.14-02; pagination metadata — MT-1.14-03;
  the banner — MT-1.14-04.
* The upload-time 409 and pipeline failure reasons — WP-1.12 (MT-1.12-07); this task
  consumes their status values at read time.
* Error codes outside the catalog for any other subsystem — Section 20.4 item 5
  applies globally, not just here.
* Bridge-side mapping of these errors to MCP tool results — WP-2.5.

## Target paths
* `backend/apps/attachments/` (error branches in the content view)
* `backend/tests/attachments/test_content_errors.py` (error matrix)
* `schemas/` — OpenAPI snapshot updated with the documented error responses
  (MT-1.1-04 pipeline)
* WP changelog entry

## Acceptance criteria
- [ ] Content retrieval during `processing` returns HTTP 409 with catalog code
  `ATTACHMENT_NOT_READY` in the MT-0.5-02 envelope — WP-1.14 acceptance, second half
  (Section 9.5; FR-ATT-04).
- [ ] Unsupported format/type combinations return `ATTACHMENT_UNSUPPORTED_FORMAT` per
  the Section 9.5 table; bad parameters return `VALIDATION_ERROR`.
- [ ] Every code asserted in tests exists in the Section 9.2 catalog with its
  documented HTTP status (Section 20.4 item 5); no ad-hoc codes anywhere in the
  retrieval path.
- [ ] Error responses carry the MT-0.5-03 header conventions and are never banner-
  prefixed (banner applies to text payloads only — MT-1.14-04).
- [ ] Error responses documented in OpenAPI with reviewed schema diff (item 4).
- [ ] Tests, lint and type check green in CI (item 2); changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_content_errors.py -v` — 409 while processing
(each format), unsupported-format matrix, validation errors, cross-project denial,
envelope/header shape; grep-style assertion that no code outside the catalog appears;
full suite green.

## Attachments
* [Section 9.2 — Canonical error catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.5 — Retrieval table and processing-time 409](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.14 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan pins the 409 only for "while processing" (Section 9.5) — confirm the
  catalog's HTTP mapping for `ATTACHMENT_NOT_READY` matches 409 before coding; any
  mismatch between the table's prose and the catalog's status column is a plan
  inconsistency to surface as a new OQ (`OQ-15+`), not a silent choice.
* `failed`-status reads have no named code in the plan (see Scope) — the documented
  decision (or the new OQ) must land in the changelog before WP-2.5 and WP-4.x build
  clients against it.
* Over-broad `ATTACHMENT_UNSUPPORTED_FORMAT` catch-alls can mask real pipeline bugs
  (e.g., a `ready` text attachment missing its markdown extraction) — log the branch
  with the reason (Section 17, NFR-10) so silent data loss is visible.
