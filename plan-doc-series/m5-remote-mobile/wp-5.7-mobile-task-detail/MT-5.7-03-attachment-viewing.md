# MT-5.7-03 — Implement attachment viewing (image, OCR, document pages)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.7-03 |
| Title | Implement attachment viewing (image, OCR, document pages) |
| Parent WP | WP-5.7 — Task detail and live checkpoint stream (Milestone M5) |
| Requirements | FR-MOB-03, FR-ATT |
| Priority | M |
| Dependencies | MT-5.7-01 (detail screen attachment region); WP-1.14 complete (retrieval API); WP-1.13 complete (processing pipeline) |
| Parent sections | 14.1 (attachments view), 9.5 (formats, pagination, untrusted banner), 9.2 (attachments endpoints), 7.2 (Task Attachment), 19 (WP-5.7), 20.4, 20.5; P10 |

## Context
Section 14.1's Task detail row includes "attachments (view)"; Section 19 WP-5.7 lists
"attachments viewing" with the screen areas image, OCR and document pages. The
retrieval contract is Section 9.5's format table: `auto` (vision session + image →
image block; document → markdown paginated), `image_base64`, `text_ocr` (OCR
transcript plus layout description), `markdown` (extracted page), with `page_number`,
`total_pages` and token counts for budgeting — and every text output prefixed with
the untrusted-content banner (Section 9.5; Principle P10). Errors are
`ATTACHMENT_NOT_READY` / `ATTACHMENT_UNSUPPORTED_FORMAT` (Section 9.2 catalog).

## Inputs / Prerequisites
* Parent plan Section 9.5 — format preference table, pagination fields, untrusted
  banner, limits (25 MB, allowlist).
* Parent plan Section 9.2 — `GET /tasks/{id}/attachments`,
  `GET /attachments/{id}`, `GET /attachments/{id}/content?format=&page=`.
* Parent plan Section 7.2 — Task Attachment fields (`processing_status`,
  `page_count`, `description`, `layout_caption`, `failure_detail`).
* WP-1.14 — implemented endpoints; MT-5.7-01 — the screen region to fill.

## Scope (in)
* An attachment viewer reachable from the detail screen: attachment list with
  `processing_status` badges; tapping opens the viewer for that attachment.
* **Image view:** normalized image via `auto`/`image_base64` with pinch-zoom
  basics; **OCR tab** showing `text_ocr` content (transcript + layout description);
  **description** display (`description`/`layout_caption`) where present (hidden when
  the description provider is disabled — OQ-07 default).
* **Document view:** page-by-page `markdown` rendering with `page_number`/
  `total_pages` navigation and token-count awareness (Section 9.5 pagination) —
  pages navigable (mirrors WP-4.6 acceptance intent).
* Untrusted-content banner on all text-derived content; markdown rendered inertly —
  no script execution (Section 9.5; Principle P10).
* States: `processing` (with live refresh on `attachment.processing|ready|failed`
  events when foregrounded, Section 9.6), `failed` with `failure_detail`, not-ready
  and unsupported-format errors mapped from the catalog (Section 20.4 item 5),
  loading/offline (Section 14.2: mutating actions offline-blocked; viewing may use
  cache if present).
* Widget/integration tests: image + tabs, OCR content, document pagination, status
  states, banner presence, both catalog error paths, unsupported format.
* A WP changelog note.

## Out of scope
* Upload from mobile — not in v1 (Section 2.2 review/monitoring scope; OQ-12 defers
  task creation — attachments upload belongs to web WP-4.5).
* OCR/description generation — WP-1.13 worker pipeline.
* Agent-side attachment reads — WP-2.5.
* Web viewer — WP-4.6 (MT-4.6-04).

## Target paths
* `mobile/` (attachment list entry and viewer screens)
* `mobile/` tests (viewer widget/integration tests)
* WP changelog entry

## Acceptance criteria
- [ ] Image, OCR and document-page viewing all work per Section 14.1's areas and
  Section 9.5's format table (image, `text_ocr`, paged `markdown`).
- [ ] Document pages navigate with `page_number`/`total_pages` honored — one
  page/chunk per call, token counts respected (Section 9.5).
- [ ] Untrusted-content banner present on text outputs and rendering is inert
  (Section 9.5; Principle P10).
- [ ] `ATTACHMENT_NOT_READY` and `ATTACHMENT_UNSUPPORTED_FORMAT` map to friendly
  states from the catalog only (Sections 9.2, 20.4 item 5); `processing`/`failed`
  statuses show with `failure_detail` (Section 7.2).
- [ ] Description tab/section hides gracefully when no description exists
  (OQ-07 default disabled).
- [ ] Widget and integration tests green; changelog note added
  (Section 20.4 items 2 and 7).

## Test command
Run the mobile suite filtered to attachments (for example
`flutter test --dart-define=test_filter=attachment` or the project's equivalent) and
confirm image/OCR/document flows, pagination, banner, status states, and both catalog
error paths against the mocked backend (Section 14.3); then the full mobile suite
stays green.

## Attachments
* [Section 9.5 — Attachment processing (retrieval behavior)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 14.1 — Navigation and screens (Task detail row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.7 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The mobile client's session capability (vision vs text-only, Section 10.4) is a
  bridge concern — the app itself always displays images; use explicit `format`
  parameters rather than `auto` if server-side capability guessing would return OCR
  instead of the image (verify against WP-1.14's behavior).
* Large documents on mobile data — Section 9.5's page-per-call is the mitigation;
  prefetch only the visible page (RISK-13 analog).
* Attachment text may be sensitive — Section 12.4 note: nothing beyond ids/titles in
  notifications, and the viewer requires the unlocked session (biometric gate,
  Section 14.2) — do not cache OCR text in logs or insecure storage.
