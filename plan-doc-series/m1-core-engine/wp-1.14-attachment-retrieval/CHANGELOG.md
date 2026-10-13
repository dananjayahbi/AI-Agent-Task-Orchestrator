# WP-1.14 — Attachment retrieval API: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-1.14-01 (descriptor payload in task payloads)** — every
  response that returns a task object now embeds the FR-ATT-03
  attachment descriptor list (the MT risk note's default reading:
  detail, create, PATCH, list, work and claim all carry it — one
  `TaskSerializer` field covers all). The descriptors are built by
  `apps.attachments.services.attachment_payload` — the *same*
  function as the WP-1.11 upload/listing endpoints — so the listing
  and task-payload shapes cannot drift (the G-01 prevention risk
  note; field-set parity is asserted, not reviewed). `token_count`
  and `short_description` stay null before `ready` and tolerate null
  after OCR-only degradation without breaking serialization. No
  content, derived text or storage path appears in a task payload
  (FR-ATT-03 "only attachment descriptors"; asserted). Lists prime
  the rows with `prefetch_related("attachments")` (tasks list; the
  leases work/claim rows each cost one extra query — noted for a
  future prefetch there, non-blocking). The OpenAPI `Task` component
  gains the nested `Attachment` array **once the snapshot regenerates**
  (follow-up below); `read_only` keeps it non-required, so the bridge
  `task_details` sample stays valid either way. Tests:
  `tests/attachments/test_task_descriptor_payload.py` (5 — field-set
  parity with the listing, create/list embedding, no content fields,
  null semantics, component agreement).
- **MT-1.14-02 (format-preference resolution; content endpoint)** —
  `GET /attachments/{id}/content?format=&page=` landed (the Section
  9.2 route, caller cell Owner/Agent-read; cross-project agent tokens
  answer `AUTH_FORBIDDEN_PROJECT`, devices `ROLE_NOT_PERMITTED`,
  anonymous `AUTH_REQUIRED`). New modules: `retrieval.py` (the
  Section 9.5 table as pure logic — `resolve_format` + page assembly,
  testable without HTTP), `serializers_content.py` (strict query
  serializer: unknown parameters rejected per MT-0.5-04), and
  `views_content.py` (the view). Behaviors per the table: `auto`
  resolves **text-safe** by type (documents → paginated `markdown`,
  images → `text_ocr`) — the Section 10.4 step-4 default, since a
  plain REST call cannot see MCP capability (WP-2.5 passes explicit
  formats; recorded, no capability parameter invented); `image_base64`
  serves the derived normalized PNG (missing derived file on a ready
  image = server-side integrity fault → logged 500, never a client
  error); `text_ocr` returns transcript + layout description and
  tolerates an empty description (MT-1.13-05); `markdown` serves
  documents. Unsupported combinations answer the catalog
  `ATTACHMENT_UNSUPPORTED_FORMAT` (415) — `image_base64` on
  non-images, `markdown` on images, `text_ocr` on never-OCR'd types.
  **Recorded deviation:** DRF globally reserves the `?format=` query
  parameter for renderer negotiation and would 404 every preference
  value; the plan fixes the parameter's spelling, so this one view
  opts out of the override (`perform_content_negotiation` negotiates
  on Accept only) — deliberately *not* a global
  `URL_FORMAT_OVERRIDE` rename, which would break the schema route's
  documented `?format=json`. Unknown `format` values answer
  `VALIDATION_ERROR`. Tests:
  `tests/attachments/test_content_formats.py` (15 — every table row
  on processed fixtures: image/PDF/DOCX/Markdown × formats, PDF page
  paging, authorization cells).
- **MT-1.14-03 (pagination metadata)** — the `page` parameter
  (one-based, default 1) with exactly the Section 9.5 triple
  `page_number`/`total_pages`/token count on paginated responses;
  non-paginated formats (`image_base64`, `text_ocr` on a single
  transcript) omit the fields — never fabricated (the documented
  asymmetry, OpenAPI-described). Mechanics (the pagination.md content
  exception — page numbers here, cursors stay for collections):
  page-oriented extractions (PDF, `page_count` set) page by
  **document page**, joining that page's chunks (`"\n\n"`, documented
  choice) with the summed token estimate; token-bounded extractions
  (DOCX/Markdown/plain) serve one **chunk** per call, so "one page or
  chunk per call" holds for both shapes. Token counts are WP-1.12's
  stored numbers — never recomputed at the API layer (risk note).
  Single-page documents report `total_pages = 1`; a processed
  document with no text still yields one empty page. Out-of-range,
  non-integer and sub-1 pages answer `VALIDATION_ERROR` (the closed
  catalog has no page code); unknown query parameters are rejected.
  Tests: `tests/attachments/test_content_pagination.py` (12 — walk,
  defaults, totals, chunk-as-page, document-page paging, invalid
  pages, unknown params, the asymmetry, stray-page tolerance).
- **MT-1.14-04 (untrusted-content banner, P10)** —
  `apps/attachments/banner.py` is the one choke point:
  `mark_untrusted(text)` prefixes the configured banner
  (`ORCHESTRATOR_ATTACHMENT_UNTRUSTED_BANNER`, documented default in
  configuration.md/.env.example — configuration, not hardcoded text;
  plan 20.4 item 3) and is **idempotent** (the duplicate-banner
  guard). Applied at the **content-endpoint boundary only**: every
  delivered text value exactly once — `text_ocr` transcript *and*
  layout description, each markdown page (one banner per page, per
  page of a multi-page document), text-safe `auto`; `image_base64`
  payloads are never touched (binary). The store keeps
  un-decorated text (MT-1.13-04's cache and WP-2.5 read the raw
  value — the single-layer reading the MT risk note demands, so
  cached descriptions cannot double-prefix; repeated retrievals are
  byte-identical). **Decided once** (MT-1.14-04 risk note): the
  descriptor `short_description` in task/list payloads stays the
  **short-metadata exemption** — a bounded summary row-wise banner
  would bloat list views and the exact-value contract was locked by
  WP-1.11's descriptor tests; asserted both ways. Error envelopes
  never carry the banner (text payloads only). Bridge coordination
  note for WP-2.5: the REST payload is already annotated — the bridge
  must not re-banner the same text. Tests:
  `tests/attachments/test_untrusted_banner.py` (8 — helper contract,
  configuration, every text format, per-page banners, no double
  prefixing, image absence, descriptor exemption, error path).
- **MT-1.14-05 (format errors, catalog codes only)** — the retrieval
  failure surface is contract-locked:
  `AttachmentNotReady` (new, `apps/attachments/exceptions.py`) answers
  **409 `ATTACHMENT_NOT_READY`** — the status Section 9.5 pins — for
  *every* non-`ready` status and every format: `uploaded` (pipeline
  not started), `processing` (the plan's named case) and **`failed`**
  (the recorded reading: the closed catalog names no
  attachment-failure code — Section 20.4 item 5 forbids inventing
  one — so `failed` shares the not-ready code and carries the stored
  human-readable reason in the message, keeping FR-ATT-07 visibility
  on the read path; recorded here before WP-2.5/WP-4.x build clients
  against it). `ATTACHMENT_UNSUPPORTED_FORMAT` (415) for the table's
  unsupported cells; `VALIDATION_ERROR` (400) for bad
  `format`/`page`/unknown parameters and malformed or unknown ids
  (the recorded WP-1.11 generic mapping); the envelope/header
  conventions hold (five-field envelope, `retryable` false on all
  these). A source-level AST sweep asserts no ad-hoc wire code can
  appear in the retrieval modules. The **deferred-route drift guard
  retired**: `test_authorization_matrix.py` lost its
  `/api/v1/attachments/1/content` deferred entry and gained
  `test_wp114_landed_content_route_enforces_its_callers` (real
  per-actor cases incl. cross-project denial). Tests:
  `tests/attachments/test_content_errors.py` (8 — not-ready matrix,
  failed-reason visibility, unsupported matrix, parameter matrix,
  authorization cells, envelope shape, catalog sweep).
- **Bridge convergence (sanctioned cross-edit)** —
  `bridge/src/orchestrator_bridge/endpoints.py`: the
  `attachment_content` pending flag retired per that file's documented
  stale-flag rule (the endpoint moved to the declared section;
  `PENDING_BACKEND` is now empty — the `checkpoint_create` and
  `resolution_submit` retires were already recorded) and
  `bridge/tests/test_openapi_contract.py` gained the
  `RESPONSE_SAMPLES["attachment_content"]` entry (resolved format,
  banner-prefixed content, page triple — validated against the
  operation's schema once the snapshot regenerates).

Follow-ups (recorded, not done here — ownership elsewhere):
* `schemas/openapi.yaml` regeneration by the sole OpenAPI regenerator
  (backend audit agent): the document must declare
  `GET /attachments/{id}/content` (and the `Task.attachments` field)
  — the bridge contract test's six failures are exactly the pending-
  flip waiting on that snapshot; no other bridge change is needed.
* The leases work/claim list endpoints could prime
  `prefetch_related("attachments")` like the tasks list (one-line
  efficiency follow-up; correctness unaffected — per-row fallback).
* WP-2.5 must pass explicit `format_preference` for vision sessions
  (Section 10.4 step 1) and must not re-apply the banner to text this
  endpoint already annotated.
