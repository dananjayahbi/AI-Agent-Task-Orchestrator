# MT-2.5-03 — Implement image content-block packaging for vision sessions

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.5-03 |
| Title | Implement image content-block packaging for vision sessions |
| Parent WP | WP-2.5 — Tool: `read_task_attachment` with capability negotiation (Milestone M2) |
| Requirements | FR-ATT-04, FR-ATT-05 |
| Priority | M |
| Dependencies | MT-2.5-01 (resolver), WP-1.12 (normalized images from the pipeline), WP-1.14 (content endpoint) |
| Parent sections | 9.5, 10.4, 10.5, 19 (WP-2.5), 20.4, 20.5 |

## Context
Section 9.5 defines retrieval behavior: for `auto`, a vision session reading an image
gets an image block; `image_base64` returns the normalized image (the pipeline has
already capped resolution and stripped metadata) and errors for non-images, or rejects
a text-only session unless forced. WP-2.5's acceptance requires that a "vision
session receives an image block". This task implements the image packaging branch that
runs after the resolver (MT-2.5-01) decides the session is vision-capable.

## Inputs / Prerequisites
* Parent plan Section 9.5 — retrieval behavior table (`auto`, `image_base64`) and the
  pipeline guarantees (normalized resolution, stripped metadata).
* Parent plan Section 10.4 — resolver output that gates this branch.
* Parent plan Section 10.5 — `read_task_attachment` inputs (`task_id`,
  `attachment_id`, `format_preference`, `page_number`) and error discipline (stable
  code, hint, next action).
* WP-1.12 — image pipeline that produces the normalized image artifacts.
* WP-1.14 — backend `GET /attachments/{id}/content` this tool wraps.
* `ATTACHMENT_NOT_READY`, `ATTACHMENT_UNSUPPORTED_FORMAT` in the Section 9.2 catalog.

## Scope (in)
* Packaging branch: when the resolver yields a vision session and the attachment is an
  image (or `format_preference` is `image_base64` for a vision session), the tool
  result carries the normalized image as an MCP image content block.
* Non-image input under `image_base64` → structured error with a stable catalog code,
  human-readable hint and next action (Section 10.5 tool rules).
* Text-only session under `image_base64` → rejected unless forced, per Section 9.5,
  with a hint pointing to `auto`/`text_ocr`.
* `ATTACHMENT_NOT_READY` passthrough when `processing_status` is not `ready`.
* Unit tests: image path produces an image block; non-image `image_base64` rejected;
  text-only rejection without force; forced path honored.

## Out of scope
* The resolver decision itself — MT-2.5-01.
* OCR/description text packaging and the untrusted banner — MT-2.5-04 (the banner is
  a text-output concern; image blocks follow Section 9.5's `auto` row).
* Pagination — MT-2.5-05.
* Producing normalized images — WP-1.12; serving them — WP-1.14.

## Target paths
* `bridge/` — attachment packaging module (image branch)
* `bridge/tests/` — image packaging tests
* WP changelog entry

## Acceptance criteria
- [ ] A vision session reading an image via `auto` receives an MCP image content
  block (WP-2.5 acceptance, FR-ATT-05).
- [ ] `image_base64` returns the normalized image for vision sessions and rejects
  non-images with a Section 9.2 catalog code plus hint and next action (Section 10.5
  tool rules).
- [ ] A text-only session's `image_base64` request is rejected unless forced
  (Section 9.5), with guidance toward `auto`/`text_ocr`.
- [ ] `ATTACHMENT_NOT_READY` is returned while processing is incomplete.
- [ ] Only catalog error codes are used (Section 20.4 item 5); lint/type/tests green
  (item 2); changelog note added (item 7).

## Test command
`uv run pytest bridge/tests/ -k attachment_image_packaging -q` — assert image block
presence for the vision path, rejection cases with catalog codes and hints, and
`ATTACHMENT_NOT_READY`; then the full bridge suite stays green.

## Attachments
* [Section 9.5 — Attachment processing (retrieval behavior)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Tool catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan does not name a specific catalog code for the text-only/`image_base64`
  rejection — choose from the Section 9.2 catalog (the natural fit is
  `ATTACHMENT_UNSUPPORTED_FORMAT`), record the choice in the changelog, and do not add
  a new code (Section 20.4 item 5).
* Image blocks bypass the text untrusted-banner path by design (Section 9.5 prefixes
  *text* outputs); do not "fix" this by inventing a banner format for images —
  confirm against FR-ATT-06 scope ("untrusted data in tool output") with a risk note
  if a reviewer reads it more broadly.
* Large images can blow up tool-result size; the pipeline's normalization caps are
  the mitigation — do not re-encode in the bridge.
