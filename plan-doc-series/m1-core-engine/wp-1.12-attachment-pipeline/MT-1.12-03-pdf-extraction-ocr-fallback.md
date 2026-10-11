# MT-1.12-03 — Implement PDF Text Extraction with OCR Fallback for Scanned Pages

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.12-03 |
| Title | Implement PDF text extraction with OCR fallback for scanned pages |
| Parent WP | WP-1.12 — Attachment pipeline: parse, OCR, chunk, tokens (Milestone M1) |
| Requirements | FR-ATT-02 |
| Priority | M |
| Dependencies | MT-1.12-01 (pipeline entry and dispatch), MT-1.12-02 (OCR engine reuse) |
| Parent sections | 9.5, 19.1 (WP-1.12), 12.1, 20.4, 20.5 |

## Context
Section 9.5, documents stage: "PDF text layer first, OCR fallback for scanned pages."
Section 12.1: malicious uploads (weaponized PDF) are mitigated by type sniffing, size
limits and **sandboxed parsing in the worker**. Section 19 (WP-1.12) acceptance
includes a text PDF and a scanned PDF in the sample set both reaching `ready` or a
clear `failed` reason, and a large PDF yielding numbered pages (page materialization
for MT-1.12-05).

## Inputs / Prerequisites
* MT-1.12-01 — dispatch for `application/pdf`.
* MT-1.12-02 — the configured OCR engine, reused for scanned pages.
* Parent plan Section 9.5 — extraction order (text layer, then OCR fallback).
* Sandbox requirements Section 12.1 — parsing runs in the worker with limits.

## Scope (in)
* Per-page PDF text extraction from the embedded text layer when present.
* Page-level detection of scanned (image-only) pages, with OCR fallback applied
  only to those pages (Section 9.5 order: text layer first).
* Page-structured output: text stored per page so MT-1.12-05 can produce numbered
  pages (`page_number`, `total_pages` are retrieval concerns — WP-1.14 — but page
  boundaries exist in the derived data).
* Worker-safety limits: process the PDF under resource limits appropriate to the
  worker (Section 12.1 "sandboxed parsing in the worker"); a malformed/hostile PDF
  fails this stage with a human-readable reason, never crashes the worker.
* Tests: text PDF (text layer used, OCR not invoked), scanned PDF (OCR invoked for
  image-only pages), mixed PDF (only scanned pages OCR'd), malformed PDF failure
  path.

## Out of scope
* The OCR engine implementation — MT-1.12-02 owns engine selection.
* Page/chunk splitting into token-bounded chunks and token estimation — MT-1.12-05.
* Summaries — MT-1.12-06.
* Retry/backoff and final status — MT-1.12-07.
* Retrieval pagination of pages — WP-1.14.
* DOCX/Markdown — MT-1.12-04.

## Target paths
* `backend/apps/attachments/pipeline_pdf.py`
* `backend/tests/attachments/test_pdf_pipeline.py`
* `backend/tests/attachments/fixtures/` (text PDF, scanned PDF, mixed PDF)
* WP changelog entry

## Acceptance criteria
- [ ] A text-layer PDF yields its embedded text without invoking OCR (Section 9.5
  order).
- [ ] A scanned (image-only) page falls back to OCR; a mixed PDF OCRs only the
  scanned pages (Section 9.5).
- [ ] Page boundaries are preserved in derived data so pages can be numbered
  (Section 19 WP-1.12: large PDF yields numbered pages — data side).
- [ ] A malformed/hostile PDF produces a human-readable failure reason and the worker
  survives (Section 12.1; Section 9.5 stage 5).
- [ ] Lint, type check and tests green (Section 20.4 item 2); changelog note added
  (item 7).

## Test command
`pytest backend/tests/attachments/test_pdf_pipeline.py -v` — text-layer, scanned,
mixed and malformed PDF fixtures with OCR-invocation assertions.

## Attachments
* [Section 9.5 — Attachment processing (documents stage)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.1 — Threat model (weaponized PDF)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.12 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "Sandboxed parsing" in Section 12.1 is not specified as a separate container for
  v1 — implement the strongest in-process limits available (time/memory caps) and
  record the assumption; if OS-level sandboxing is required, that is a parent-plan
  open point (Section 12.3 lists per-project sandboxes as post-v1 Could).
* Scanned-page detection heuristics (no text layer vs. sparse text) can misclassify;
  document the threshold in the changelog note — do not silently OCR every page
  (cost) or skip fallback (wrong text).
