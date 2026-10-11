# MT-1.14-02 — Implement Format-Preference Resolution (auto, image_base64, text_ocr, markdown)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.14-02 |
| Title | Implement format-preference resolution (auto, image_base64, text_ocr, markdown) |
| Parent WP | WP-1.14 — Attachment retrieval API (Milestone M1) |
| Requirements | FR-ATT-04, FR-ATT-05 |
| Priority | M |
| Dependencies | MT-1.14-01 (descriptor shape), MT-1.12-08 (content ready), MT-1.13-05 (descriptions may be absent) |
| Parent sections | 9.2, 9.5 (retrieval table), 10.4, 19.1 (WP-1.14 acceptance), 20.4, 20.5 |

## Context
Section 9.2 defines the endpoint: `GET /attachments/{id}/content?format=&page=` (caller
Owner / Agent read). Section 9.5's retrieval table is the behavior contract for all
four `format_preference` values: `auto` (vision session + image → image block;
text-only session + image → OCR plus description; document → markdown, paginated),
`image_base64` (normalized image; error for non-images or text-only sessions unless
forced), `text_ocr` (OCR transcript plus layout description), `markdown` (extracted
markdown page). WP-1.14's acceptance is that "all four format preferences behave per
table in Section 9.5". FR-ATT-04 requires retrieval in exactly these four formats with
pagination; FR-ATT-05 ties `auto` to session capability. Section 10.4's resolution
order puts an explicit `format_preference` first and defaults unknown capability to
text-safe — the guidance for everything the backend cannot know.

## Inputs / Prerequisites
* MT-1.14-01 — descriptor shape; content itself is fetched on demand (FR-ATT-03's
  lazy model).
* MT-1.12-08 — sample corpus of processed attachments (screenshot, scanned PDF, text
  PDF, DOCX, Markdown) to exercise every format branch.
* MT-1.13-05 — OCR-only degradation: `text_ocr` and `auto` text-safe must work with
  an empty description field.
* Parent plan Section 9.5 — the retrieval table (authoritative behaviors).
* Parent plan Section 10.4 — capability resolution order and the text-safe default;
  the bridge passes explicit formats after resolving capability (WP-2.5).
* Parent plan Section 9.2 — endpoint path, `format` and `page` parameters, callers.

## Scope (in)
* Implement `GET /attachments/{id}/content` with the `format` parameter accepting
  exactly `auto`, `image_base64`, `text_ocr`, `markdown` (FR-ATT-04), defaulting to
  `auto` when omitted.
* Implement per the Section 9.5 table:
  * `image_base64` → the normalized image (Section 9.5 stage 2 output); for
    non-image attachments return `ATTACHMENT_UNSUPPORTED_FORMAT` (Section 9.2
    catalog); text-only-session rejection is a capability concern resolved bridge-side
    (Section 10.4 step 1 — explicit format is authoritative), so the backend serves
    the image whenever explicitly requested.
  * `text_ocr` → OCR transcript plus layout description; tolerate an absent
    description (MT-1.13-05) by returning the transcript alone.
  * `markdown` → the extracted markdown for documents (Section 9.5 stage 3).
  * `auto` → documents resolve to `markdown` (paginated); images resolve to the
    text-safe result (OCR plus description) unless the request context carries a
    vision-capable session (Section 10.4 step 4 default: `unknown` → text-safe;
    MCP image-block wrapping for vision sessions is WP-2.5, which passes the resolved
    format explicitly).
* Authorization unchanged: Owner and agent-read-own-project per Section 9.2 /
  Section 12.2; cross-project returns `AUTH_FORBIDDEN_PROJECT`.
* Parameter validation uses catalog codes only (`VALIDATION_ERROR` for an unknown
  `format` value) — no invented codes (Section 20.4 item 5).
* Tests per format on the MT-1.12-08 corpus; OpenAPI updated with reviewed diff
  (item 4); changelog note (item 7).

## Out of scope
* `page` parameter semantics, `page_number` / `total_pages` / token counts in the
  response — MT-1.14-03.
* The untrusted-content banner prefix — MT-1.14-04.
* `ATTACHMENT_NOT_READY` handling and the unsupported-format error cases beyond the
  table — MT-1.14-05 (basic non-image `image_base64` rejection lands here as the
  table demands; its full error-matrix tests are consolidated there).
* Capability negotiation, capability table, MCP image content blocks — Section 10.4 /
  WP-2.5.
* Descriptor-only task payloads — MT-1.14-01.

## Target paths
* `backend/apps/attachments/` (content view: format resolution)
* `backend/tests/attachments/` (four-format behavior tests on the sample corpus)
* `schemas/` — OpenAPI snapshot updated (MT-1.1-04 pipeline)
* WP changelog entry

## Acceptance criteria
- [ ] All four format preferences behave per the Section 9.5 table on the sample
  corpus — WP-1.14 acceptance, first half (FR-ATT-04).
- [ ] `image_base64` returns the normalized image for images and
  `ATTACHMENT_UNSUPPORTED_FORMAT` for non-images (Section 9.5 table; Section 9.2
  catalog).
- [ ] `text_ocr` succeeds with and without a stored layout description
  (MT-1.13-05 degraded case).
- [ ] `auto` defaults to the text-safe result when no vision capability is present
  (Section 10.4 step 4) and to markdown for documents.
- [ ] Authorization: cross-project access returns `AUTH_FORBIDDEN_PROJECT`
  (Section 12.2).
- [ ] OpenAPI updated, schema diff reviewed (item 4); codes from the catalog (item 5);
  tests green in CI (item 2); changelog note (item 7).

## Test command
`pytest backend/tests/attachments/test_content_formats.py -v` — one case per table
row on the MT-1.12-08 corpus (image × {auto, image_base64, text_ocr}, PDF/DOCX/
Markdown × {auto, markdown}), unknown format value, cross-project rejection; full
suite green.

## Attachments
* [Section 9.5 — Retrieval behavior table](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.4 — Capability negotiation](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — REST API surface (Attachments)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* `auto` + image is inherently capability-dependent; the backend cannot see the MCP
  client's capability on a plain token-authenticated call — the plan's answer is
  Section 10.4's order (explicit format from the bridge first, text-safe default
  otherwise). Do not invent a capability request parameter here; if a backend-side
  capability signal turns out necessary for web/mobile `auto`, raise a new OQ
  (`OQ-15+`) before adding a parameter.
* Section 9.5 says `image_base64` "rejects if session is text-only unless forced" —
  session association exists only for bridge calls; enforce text-safety in WP-2.5's
  capability resolver, and document in the changelog that the REST endpoint serves
  explicit requests.
* Whether `markdown` on an image (or `text_ocr` on a pure-markdown file) is an error
  or a conversion is not spelled out per cell — treat unsupported combinations as
  `ATTACHMENT_UNSUPPORTED_FORMAT` and let MT-1.14-05 lock the matrix.
