# MT-1.14-03 — Implement Pagination Metadata for Retrieved Content

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.14-03 |
| Title | Implement pagination metadata for retrieved content |
| Parent WP | WP-1.14 — Attachment retrieval API (Milestone M1) |
| Requirements | FR-ATT-04 |
| Priority | M |
| Dependencies | MT-1.14-02 (content endpoint and formats), MT-1.12-08 (chunked markdown and token counts) |
| Parent sections | 9.2, 9.5 (pagination clause), 19.1 (WP-1.14 slices), 20.4, 20.5; Appendix B (B-02) |

## Context
Section 9.5's retrieval table ends with the pagination clause for `auto` on documents:
"Paged output returns `page_number`, `total_pages`, and token count." Section 9.2
specifies the endpoint's `format` **and** `page` parameters. WP-1.14's third slice is
"pagination with page number, total page count, token counts". FR-ATT-04 names
pagination as one of the four retrieval requirements (retrieval in four formats **with
pagination**). The plan deliberately distinguishes cursor pagination for *collections*
(MT-0.5-04: cursors for offset pagination, `400` on unknown parameters) from *page*
pagination for large extracted documents (9.5: page numbers plus token counts —
Appendix B B-02 explicitly flags page-number pagination for long documents as a
separate concern from cursor discipline). This micro-task implements the document page
contract on the content endpoint.

## Inputs / Prerequisites
* MT-1.14-02 — the content endpoint and four formats; `page` is the third parameter
  of the same route (Section 9.2).
* MT-1.12-08 — stage 3 paginated extraction with token counts per page (the data this
  metadata describes).
* Parent plan Section 9.5 — `page_number`, `total_pages`, token count return clause.
* Parent plan Section 9.2 — `page` query parameter.
* MT-0.5-04 — cursor conventions apply to collection endpoints only; unknown query
  parameters still return `VALIDATION_ERROR` (Section 9.2 catalog).
* Appendix B B-02 — "page-number pagination is not applied to long documents (deferred
  concern)" — i.e., documents ARE paginated by page number; cursors are for lists.

## Scope (in)
* Implement the `page` query parameter on `GET /attachments/{id}/content`, defaulting
  to page 1 for paginated formats (`markdown`, `auto` on documents per Section 9.5).
* Return `page_number`, `total_pages` and the page's token count alongside content
  for paginated responses, exactly the three fields Section 9.5 names; non-paginated
  responses (`image_base64`, `text_ocr` on a single transcript) do not fabricate page
  metadata — document this asymmetry in the OpenAPI description.
* Out-of-range page behavior: define explicitly as `VALIDATION_ERROR` (Section 9.2
  catalog; Section 20.4 item 5 — no invented code such as a "page not found" code).
* One-based page numbering with `total_pages = 1` for single-page documents (the
  natural reading of the table; note it in the changelog so WP-2.5 and web clients
  share the convention).
* Validation: unknown query parameters rejected with `VALIDATION_ERROR`
  (MT-0.5-04 discipline); non-integer `page` likewise.
* Tests: multi-page document walk (`page=1 … total_pages`), out-of-range, missing
  `page` defaults to 1, token count present and plausible per page, single-page
  document, non-paginated formats carry no page fields; OpenAPI updated with reviewed
  diff (Section 20.4 item 4); changelog note (item 7).

## Out of scope
* Cursor pagination for collections — MT-0.5-04 (already delivered).
* Producing the page splits/token counts — WP-1.12 stage 3 (this task only surfaces
  the metadata).
* Format resolution behavior itself — MT-1.14-02.
* The untrusted banner — MT-1.14-04.
* Bridge-side paging loops for `read_attachment` (WP-2.5 decides how an agent walks
  pages).
* Web/mobile page navigation UI — WP-4.x / WP-5.x.

## Target paths
* `backend/apps/attachments/` (content view: `page` parameter and metadata block)
* `backend/tests/attachments/` (pagination tests on a multi-page document from the
  MT-1.12-08 corpus)
* `schemas/` — OpenAPI snapshot updated (MT-1.1-04 pipeline)
* WP changelog entry

## Acceptance criteria
- [ ] Paginated retrieval returns `page_number`, `total_pages` and token count —
  Section 9.5 pagination clause; WP-1.14 third slice (FR-ATT-04).
- [ ] `page` defaults to 1; out-of-range and non-integer values return
  `VALIDATION_ERROR` from the Section 9.2 catalog (Section 20.4 item 5).
- [ ] Non-paginated formats omit page metadata without breaking their response shape
  (Section 9.5 table read literally).
- [ ] Single-page documents report `total_pages = 1` (changelog note records the
  convention).
- [ ] Unknown query parameters rejected per MT-0.5-04 conventions.
- [ ] OpenAPI updated, schema diff reviewed (item 4); tests, lint and type check green
  in CI (item 2); changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_content_pagination.py -v` — page walk, default
page, out-of-range, token-count presence, single-page, non-paginated formats, unknown
parameter rejection; full `pytest backend/tests -q` stays green.

## Attachments
* [Section 9.5 — Pagination clause](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — REST API surface (`page` parameter)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Appendix B — Known design gaps (B-02)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Token count units are whatever WP-1.12 stage 3 records — do not recompute or
  redefine them at the API layer; assert only their presence and consistency with the
  stored page metadata.
* Page-number responses and cursor collections must not share serialization helpers
  in a way that leaks cursor fields (`next_cursor`, `has_more`) into page responses —
  the two pagination families are deliberately distinct (MT-0.5-04 vs. Section 9.5).
* Token-count pagination for images (`image_base64` in `auto`) is not covered by the
  table; if WP-2.5 needs it for vision token budgeting, raise a new OQ (`OQ-15+`)
  rather than extending the response shape unilaterally.
