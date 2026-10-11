# MT-1.12-04 — Implement DOCX and Markdown Extraction

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.12-04 |
| Title | Implement DOCX and Markdown extraction |
| Parent WP | WP-1.12 — Attachment pipeline: parse, OCR, chunk, tokens (Milestone M1) |
| Requirements | FR-ATT-02 |
| Priority | M |
| Dependencies | MT-1.12-01 (pipeline entry and dispatch) |
| Parent sections | 9.5, 19.1 (WP-1.12), 12.1, 20.4, 20.5 |

## Context
Section 9.5 documents stage: "extract text/markdown" for documents; the allowlist
covers DOCX, `text/markdown` and `text/plain`. Section 12.1: parsing of untrusted
uploads happens sandboxed in the worker. Section 19 (WP-1.12) acceptance: DOCX and
Markdown samples in the sample corpus reach `ready` or a clear `failed` reason.

## Inputs / Prerequisites
* MT-1.12-01 — dispatch for DOCX (`application/vnd.openxmlformats-officedocument.
  wordprocessingml.document`) and `text/markdown`.
* Parent plan Section 9.5 — documents stage behavior.
* Section 12.1 — worker-side parsing safety for untrusted files.

## Scope (in)
* DOCX extraction: read the document body in document order and produce
  markdown-flavored text (headings, lists, paragraphs, tables where representable),
  preserving enough structure for chunking and summaries downstream.
* Markdown extraction: the stored file is already text — normalize encoding/line
  endings and carry it through as the extracted markdown (no content transformation
  beyond normalization).
* `text/plain` handling: pass through as text (allowlisted in Section 9.5; trivial
  path, implemented alongside Markdown).
* Hostile-input safety: oversized/embedded-expansion DOCX fails with a human-readable
  reason without crashing the worker (Section 12.1).
* Tests: DOCX fixture (structure preserved), Markdown fixture (normalized,
  unchanged content), plain-text pass-through, malformed DOCX failure path.

## Out of scope
* Page structure for DOCX (Section 9.5 speaks of "pages **or** token-bounded
  chunks" — DOCX proceeds to chunk splitting in MT-1.12-05).
* Chunking, token estimation — MT-1.12-05.
* Summaries — MT-1.12-06.
* Status/retry — MT-1.12-07.
* PDF — MT-1.12-03.
* Retrieval formats — WP-1.14.

## Target paths
* `backend/apps/attachments/pipeline_documents.py`
* `backend/tests/attachments/test_document_extraction.py`
* `backend/tests/attachments/fixtures/` (DOCX, Markdown samples)
* WP changelog entry

## Acceptance criteria
- [ ] A DOCX fixture extracts text in document order with structural elements
  represented as markdown (FR-ATT-02 "parse").
- [ ] A Markdown fixture passes through normalized (line endings/encoding) with
  content unchanged.
- [ ] `text/plain` is accepted and passed through (Section 9.5 allowlist).
- [ ] A malformed/hostile DOCX fails with a human-readable reason; the worker
  survives (Section 12.1; Section 9.5 stage 5).
- [ ] Lint, type check and tests green (Section 20.4 item 2); changelog note added
  (item 7).

## Test command
`pytest backend/tests/attachments/test_document_extraction.py -v` — DOCX structure
extraction, Markdown normalization, plain-text pass-through, malformed-input safety.

## Attachments
* [Section 9.5 — Attachment processing (documents stage)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.1 — Threat model (malicious uploads)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.12 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* DOCX is a zip container — parsing must guard against zip-bomb style expansion
  (Section 12.1); enforce a decompressed-size ceiling and fail with a clear reason.
* Markdown is untrusted content (P10): extraction must not interpret/execute anything
  — the untrusted-content banner belongs to the retrieval API (WP-1.14), not here;
  keep raw text as-is.
