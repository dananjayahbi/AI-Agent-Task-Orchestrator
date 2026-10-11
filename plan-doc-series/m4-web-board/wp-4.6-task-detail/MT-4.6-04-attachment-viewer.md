# MT-4.6-04 — Implement the attachment viewer with OCR/description tabs

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.6-04 |
| Title | Implement the attachment viewer with OCR/description tabs |
| Parent WP | WP-4.6 — Task detail: checkpoints, resolutions, attachments (Milestone M4) |
| Requirements | FR-WEB-04, FR-ATT |
| Priority | M |
| Dependencies | MT-4.6-01 (detail shell); WP-1.14 complete (attachment retrieval API); WP-1.13 complete (processing pipeline) |
| Parent sections | 13.2 (Attachment viewer component), 9.2 (attachments endpoints), 9.5 (processing and content formats), 7.2 (Task Attachment), 19 (WP-4.6), 20.4, 20.5; P10 |

## Context
Section 13.2 defines the component: "Attachment viewer: image preview with OCR and
description tabs; document pages; processing status and retry." Section 19 WP-4.6
acceptance: "attachment pages navigable." The retrieval contract is Section 9.2's
`GET /tasks/{id}/attachments`, `GET /attachments/{id}` and
`GET /attachments/{id}/content?format=&page=`, with formats `auto`, `image_base64`,
`text_ocr`, `markdown` (Section 9.5). Task Attachment rows carry `processing_status`
(`uploaded` / `processing` / `ready` / `failed`), `failure_detail`, `page_count`
(Section 7.2), and all text outputs are prefixed with the untrusted-content banner
(Section 9.5; Principle P10).

## Inputs / Prerequisites
* Parent plan Section 13.2 — the viewer's exact feature list.
* Parent plan Section 9.2 — attachment list, metadata and content endpoints.
* Parent plan Section 9.5 — format table (`auto`, `image_base64`, `text_ocr`,
  `markdown`), pagination (`page_number`, `total_pages`, token count), untrusted
  banner, `ATTACHMENT_NOT_READY` / `ATTACHMENT_UNSUPPORTED_FORMAT` errors.
* Parent plan Section 7.2 — Task Attachment fields incl. `processing_status`.
* WP-1.14 — implemented retrieval API to test against.

## Scope (in)
* An attachment viewer in the detail view's attachment region: thumbnail/list of the
  task's attachments with per-file `processing_status`.
* Image preview using the normalized image (`format_preference` `auto`/`image_base64`)
  with two tabs as Section 13.2 requires: **OCR** (`text_ocr`) and **description**
  (`description` / `layout_caption` content when present).
* Document viewing with page navigation: `markdown` format per page using
  `page_number` / `total_pages` — pages must be navigable forward/back (WP-4.6
  acceptance "attachment pages navigable").
* Untrusted-content banner treatment for all text-derived content (Section 9.5,
  Principle P10) — rendered as data, never executed (markdown rendered inertly).
* Processing status display: `uploaded` / `processing` / `ready` / `failed` with
  `failure_detail` shown for failures, refreshing via `attachment.ready|failed`
  events (Section 9.6) while the detail is open.
* Error handling from the catalog only: `ATTACHMENT_NOT_READY`,
  `ATTACHMENT_UNSUPPORTED_FORMAT` mapped to friendly states (Section 9.2,
  20.4 item 5).
* Component tests: image with tabs, document pagination, status states, untrusted
  banner presence, unsupported-format and not-ready error paths.
* A WP changelog note.

## Out of scope
* Upload and its progress UI — WP-4.5 (MT-4.5-05).
* OCR/description generation and retries inside the worker — WP-1.13 (Section 9.5
  pipeline); see Risk notes about the "retry" affordance.
* Attachment deletion — WP-4.5/owner flows.
* Agent-side attachment reading — WP-2.5.
* Mobile attachment viewing — WP-5.7 (MT-5.7-03).

## Target paths
* `web/` (attachment viewer component in task detail)
* `web/` tests (viewer tests with fixture attachments)
* WP changelog entry

## Acceptance criteria
- [ ] Images render a preview with working OCR and description tabs
  (Section 13.2; Section 9.5 `text_ocr` and description content).
- [ ] Document pages navigate forward/back with `page_number`/`total_pages` honored —
  "attachment pages navigable" (Section 19 WP-4.6 acceptance).
- [ ] All four `processing_status` values are displayed, with `failure_detail` on
  `failed` (Section 7.2), updated live on `attachment.ready|failed` (Section 9.6).
- [ ] All text-derived content carries the untrusted-content treatment
  (Section 9.5; Principle P10); markdown is rendered inertly — no executable content.
- [ ] `ATTACHMENT_NOT_READY` and `ATTACHMENT_UNSUPPORTED_FORMAT` map to friendly
  states from the catalog only (Sections 9.2, 20.4 item 5).
- [ ] Loading, empty (no attachments) and error states handled (Section 20.3).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to attachments (for example `npm test -- -t
attachment`) and confirm: image preview with OCR/description tabs, document page
navigation, status state transitions, untrusted banner, and both catalog error paths;
then the full web suite stays green.

## Attachments
* [Section 13.2 — Key components (Attachment viewer)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.5 — Attachment processing (formats and retrieval)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.6 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Section 13.2 says "processing status and retry", but Section 9.2 exposes no manual
  reprocess endpoint and Section 9.5 retries transient failures automatically — the
  viewer's "retry" is therefore a status refresh/refetch; a true reprocess action
  would need an API addition (Section 20.4 item 4) — do not invent it.
* Large PDFs (25 MB cap, Section 9.5) — fetch one page per request and rely on
  Section 9.5 pagination/token estimates; pre-loading whole documents would breach
  Section 13.4 (RISK-13).
* OCR quality varies (RISK-06) — the description tab may be absent when the provider
  is disabled (OQ-07 default) — hide the tab rather than showing an empty error.
