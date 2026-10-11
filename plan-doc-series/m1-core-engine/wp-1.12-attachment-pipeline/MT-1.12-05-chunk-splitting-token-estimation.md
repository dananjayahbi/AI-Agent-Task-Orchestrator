# MT-1.12-05 — Implement Page/Chunk Splitting and Token Estimation

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.12-05 |
| Title | Implement page/chunk splitting and token estimation |
| Parent WP | WP-1.12 — Attachment pipeline: parse, OCR, chunk, tokens (Milestone M1) |
| Requirements | FR-ATT-02, FR-ATT-07 |
| Priority | M |
| Dependencies | MT-1.12-02, MT-1.12-03, MT-1.12-04 (extraction stages producing text) |
| Parent sections | 9.5, 19.1 (WP-1.12), 20.4, 20.5 |

## Context
Section 9.5 documents stage: extracted text is "split into pages or token-bounded
chunks, estimate tokens." Section 19 (WP-1.12) deliverables include the **chunk
model**; acceptance includes "large PDF yields numbered pages." The retrieval API
later serves one page or chunk per call with `page_number`, `total_pages` and a
token count so agents can budget context (Section 9.5) — this task produces exactly
that data.

## Inputs / Prerequisites
* MT-1.12-03 — PDF text with preserved page boundaries (pages path).
* MT-1.12-04 — DOCX/Markdown extracted text (chunks path).
* MT-1.12-02 — OCR transcripts (page-aligned text for images).
* FR-ATT-03 — token count appears in attachment descriptors.
* Parent plan Section 9.5 — splitting rule and estimation requirement.

## Scope (in)
* A chunk model (per Section 19 WP-1.12 deliverables) storing: sequence position,
  page number (when page-based), text, and estimated token count; persisted as
  derived data on the attachment.
* Splitting rules: page-oriented outputs (PDF, image OCR) keep page boundaries as
  numbered units (`page_number`, `total_pages` derivable); long pages/chunks are
  further split into token-bounded chunks with a configurable bound and documented
  default.
* Token estimation: a deterministic estimator with a documented default method
  (Section 9.10-style configurability); estimates stored per chunk and rolled up to
  the attachment-level token count exposed in descriptors (FR-ATT-03).
* Tests: page numbering on a large PDF fixture (`1..N` contiguous, `total_pages`
  correct), chunk token bounds respected, roll-up token count matches the sum of
  chunks, deterministic output on re-run.

## Out of scope
* Extraction itself — MT-1.12-02/03/04.
* Summaries — MT-1.12-06.
* Status transitions/retry — MT-1.12-07.
* Serving pages/chunks (`content` endpoint, `page_number` response fields) —
  WP-1.14 (this task produces the data).
* Exact tokenizer parity with any specific model — the plan says "estimate"; the
  method is a documented choice, not an invented contract.

## Target paths
* `backend/apps/attachments/models.py` (chunk model + migration)
* `backend/apps/attachments/chunking.py`
* `backend/tests/attachments/test_chunking.py`
* WP changelog entry

## Acceptance criteria
- [ ] A chunk model exists and derived chunks/token counts are persisted (Section 19
  WP-1.12 deliverable).
- [ ] A large PDF fixture yields contiguous numbered pages with correct
  `total_pages` data (Section 19 WP-1.12 acceptance).
- [ ] Token-bounded chunk splitting respects the configured bound; every chunk's
  estimated token count is stored and the attachment roll-up equals the sum
  (FR-ATT-03 field fed).
- [ ] Re-running the stage produces identical derived data (re-creatable,
  Section 9.5).
- [ ] Splitting/estimation settings have documented defaults (Section 20.4 item 3);
  changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_chunking.py -v` — page numbering on the large
PDF fixture, chunk bounds, roll-up totals, determinism on re-run.

## Attachments
* [Section 9.5 — Attachment processing (splitting and token estimation)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.12 deliverables and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-ATT-03 — Descriptor token count](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "Token-bounded" implies a tokenizer choice; the plan does not fix one (Section 9.10
  lists no tokenizer setting). Pick a documented default estimator and record it —
  if a model-accurate tokenizer is demanded, raise a new OQ (`OQ-15+`) first.
* Splitting must never drop text: add a coverage assertion (sum of chunk text equals
  extracted text modulo separators) so silent truncation fails tests.
