# MT-1.12-08 — Write Sample-Corpus Tests (Screenshot, Scanned PDF, Text PDF, DOCX, Markdown)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.12-08 |
| Title | Write sample-corpus tests (screenshot, scanned PDF, text PDF, DOCX, Markdown) |
| Parent WP | WP-1.12 — Attachment pipeline: parse, OCR, chunk, tokens (Milestone M1) |
| Requirements | FR-ATT-02, FR-ATT-07 |
| Priority | M |
| Dependencies | MT-1.12-07 (status machine and retries complete) |
| Parent sections | 19.1 (WP-1.12), 9.5, 18, 20.4, 20.5 |

## Context
Section 19 (WP-1.12) acceptance: "sample set (screenshot, scanned PDF, text PDF,
DOCX, Markdown) all reach `ready` or a clear `failed` reason; large PDF yields
numbered pages." Section 20.4 item 1: acceptance criteria demonstrably met by the
named test command. This closing task builds the corpus fixtures and the
end-to-end pipeline test that proves the whole WP against the plan's acceptance.

## Inputs / Prerequisites
* MT-1.12-01 … MT-1.12-07 — the complete pipeline.
* MT-1.11-03 — upload path to enter the pipeline the way real clients do.
* Parent plan Section 9.5 — expected derived data per kind (OCR transcript, pages,
  chunks, token counts, summary).
* Local Compose worker (MT-1.7-01) for at least one integration run.

## Scope (in)
* A committed, license-clean sample corpus under the attachments test fixtures:
  screenshot (PNG), scanned PDF, text PDF, DOCX, Markdown — plus a large multi-page
  PDF for numbering.
* An end-to-end test per corpus member: upload → pipeline → final status; assert
  `ready` (or, for deliberately broken inputs, `failed` with a human-readable
  reason) and the kind-specific derived data:
  * screenshot: normalized image + OCR transcript + summary;
  * text PDF: extracted text without OCR; scanned PDF: OCR fallback used;
  * DOCX/Markdown: extracted/normalized text;
  * all: chunks with token counts, attachment-level token roll-up, summary;
  * large PDF: contiguous numbered pages with correct `total_pages`.
* One Compose-level run of the suite exercising the real worker (Section 18 layering:
  integration against real services).
* Results feed the WP-1.12 acceptance statement verifiable by a single command.

## Out of scope
* The corpus itself becoming test data for other WPs (WP-1.14 retrieval tests may
  reference it, but those tests belong there).
* Performance/load testing of the pipeline — WP-6.3.
* Fixing failures discovered — file follow-up work; do not weaken assertions.
* Description-provider-enabled corpus runs — WP-1.13.

## Target paths
* `backend/tests/attachments/fixtures/corpus/` (the five-plus sample files)
* `backend/tests/attachments/test_sample_corpus.py`
* WP changelog entry

## Acceptance criteria
- [ ] The corpus contains exactly the Section 19 WP-1.12 sample set (screenshot,
  scanned PDF, text PDF, DOCX, Markdown) plus a large PDF for page numbering.
- [ ] Every corpus member ends `ready`, or `failed` with a non-empty human-readable
  reason for deliberately broken inputs (Section 19 WP-1.12 acceptance).
- [ ] The large PDF yields contiguous numbered pages with correct `total_pages`
  (Section 19 WP-1.12 acceptance; Section 9.5 pagination data).
- [ ] Each kind's derived data expectations (OCR transcript, extracted text, chunks,
  token counts, summary) are asserted (FR-ATT-02).
- [ ] The suite runs green in CI with the real worker at least once, satisfying
  Section 20.4 items 1-2; changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_sample_corpus.py -v` — full corpus matrix:
status outcomes, derived data per kind, large-PDF page numbering.

## Attachments
* [Section 19.1 — WP-1.12 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.5 — Attachment processing](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and quality strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Fixture OCR quality varies by engine (MT-1.12-02 risk) — assert transcript
  substrings known to be legible in the fixture rather than exact full-text matches,
  so the test proves OCR ran without being engine-fragile.
* The scanned-PDF fixture must genuinely be image-only; a text-layer PDF labeled
  "scanned" would make the OCR-fallback assertion pass vacuously — validate the
  fixture property in the test setup.
* Binary fixtures in Git: keep them small and license-clean; note provenance in the
  changelog (Section 20.4 item 3 — no licensed material committed).
