# MT-2.5-04 — Implement text/OCR packaging with untrusted banner for text-only sessions

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.5-04 |
| Title | Implement text/OCR packaging with untrusted banner for text-only sessions |
| Parent WP | WP-2.5 — Tool: `read_task_attachment` with capability negotiation (Milestone M2) |
| Requirements | FR-ATT-05, FR-ATT-06 |
| Priority | M |
| Dependencies | MT-2.5-01 (resolver), MT-2.5-03 (image branch contrast), WP-1.12 (OCR and description artifacts), WP-1.14 (content endpoint) |
| Parent sections | 9.5, 10.4, 10.5, 19 (WP-2.5), 20.4, 20.5 |

## Context
Section 9.5: for `auto`, a text-only session reading an image gets OCR plus
description; `text_ocr` returns the OCR transcript plus layout description; documents
return extracted markdown paginated; and "all text outputs are prefixed with an
untrusted-content banner (P10)". P10 (Section 6.1) marks attachment and repo content
as data, never instructions (reinforced by the Section 12.1 prompt-injection row).
WP-2.5's acceptance: a "text-only session receives OCR plus description" and "every
text output carries the untrusted banner". This task implements the text packaging
branch the resolver routes to for `unknown`/text-safe sessions.

## Inputs / Prerequisites
* Parent plan Section 9.5 — `auto` text-only row, `text_ocr` row, `markdown` row, and
  the banner rule.
* Parent plan P10 (Section 6.1) and Section 12.1 prompt-injection row.
* Parent plan Section 10.4 — resolver output (including the step-4 note on how to
  request the image explicitly).
* Parent plan Section 10.5 — `ATTACHMENT_NOT_READY` and tool error discipline.
* WP-1.12 — OCR transcript, layout description, extracted markdown artifacts, and the
  description provider's OCR-only degradation.

## Scope (in)
* Text packaging branch: text-only/`unknown` sessions reading an image get the OCR
  transcript plus layout description (and the resolver's note on requesting the image
  explicitly); `text_ocr` returns the same for any session; documents return
  extracted markdown (pagination handled in MT-2.5-05).
* The untrusted-content banner prefixed to **every** text output this tool produces —
  `auto` text path, `text_ocr`, `markdown` — with one canonical banner string
  referenced by convention, not reworded per call site.
* Degraded descriptions: when the description provider failed or is disabled, the
  packaging still returns OCR-only output with the banner (Section 9.5 degradation).
* `ATTACHMENT_NOT_READY` passthrough while `processing_status` is not `ready`;
  permanent pipeline failures surface the human-readable reason from Section 9.5.
* Unit tests: banner present on every text output shape; OCR+description on the
  text-only `auto` path; OCR-only degradation; missing OCR → `ATTACHMENT_NOT_READY`.

## Out of scope
* Resolver logic — MT-2.5-01; image blocks — MT-2.5-03; pagination — MT-2.5-05.
* Producing OCR/description/markdown artifacts and the description provider —
  WP-1.12, WP-1.13.
* Backend content endpoint — WP-1.14.
* Scanning or sanitizing attachment text — the plan marks it untrusted by banner
  (P10), it is never executed.

## Target paths
* `bridge/` — attachment packaging module (text branch, banner constant)
* `bridge/tests/` — text packaging and banner tests
* WP changelog entry

## Acceptance criteria
- [ ] A text-only session reading an image via `auto` receives OCR plus description
  (WP-2.5 acceptance, FR-ATT-05).
- [ ] Every text output from `read_task_attachment` (`auto` text path, `text_ocr`,
  `markdown`) is prefixed with the untrusted-content banner (WP-2.5 acceptance,
  FR-ATT-06, P10).
- [ ] The step-4 note on how to request the image explicitly accompanies
  default-resolved text-safe output (Section 10.4).
- [ ] Description-provider failure degrades to OCR-only instead of failing the read
  (Section 9.5).
- [ ] Errors use only Section 9.2 catalog codes (Section 20.4 item 5); lint/type/tests
  green (item 2); changelog note added (item 7).

## Test command
`uv run pytest bridge/tests/ -k attachment_text_packaging -q` — assert the banner
prefix on every text output fixture, OCR+description for the text-only `auto` path,
OCR-only degradation, and `ATTACHMENT_NOT_READY` while processing; then the full
bridge suite stays green.

## Attachments
* [Section 9.5 — Attachment processing (retrieval behavior)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.1 — Threat model (prompt injection via attachments)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Banner drift: multiple packaging call sites invite slightly different banner text —
  keep one canonical string (single constant) so "every text output carries the
  banner" stays testable.
* The plan specifies the banner's existence and placement (prefix), not its exact
  wording — choose wording that states the content is untrusted data, record it once,
  and do not invent additional envelope fields around it.
* Empty OCR (image with no readable text) must still return a result with the banner
  and description fallback rather than an error — cover it in tests so a future
  "empty = failure" "fix" is caught.
