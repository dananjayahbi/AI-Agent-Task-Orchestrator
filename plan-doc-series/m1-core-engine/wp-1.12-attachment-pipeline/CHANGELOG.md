# WP-1.12 — Attachment pipeline: parse, OCR, chunk, tokens: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-1.12-01 (pipeline entry: type detection + checksum)** —
  `apps/attachments/pipeline.py` is the Section 9.5 stage-1 orchestrator
  composed as `run_pipeline`: load the stored object, re-derive sha256
  against the record (mismatch → permanent `failed` with a human-readable
  integrity reason — trust neither side, MT risk note), re-detect the type
  from **content** (never the filename) and fail on any disagreement with
  the recorded sniff, then dispatch images → 02, PDF → 03,
  DOCX/Markdown/plain → 04 off the Section 9.5 allowlist verbatim.
  Status `uploaded → processing` happens through the CAS
  `begin_processing` with exactly one `attachment.processing` event
  written in-transaction (MT-1.9-02 `write_event`; Section 20.4 item 6);
  re-delivery of an already-terminal row is de-duplicated away — no
  stages, no duplicate events (idempotent re-entry, tested). The MT-1.11-03
  enqueue seam is completed process-wide: `AttachmentsConfig.ready()`
  installs `enqueue_attachment_job` (post-commit `.delay`) in every
  broker-facing process, while the hermetic unit layer keeps the
  documented no-op (`DJANGO_SETTINGS_MODULE` guard — Section 18), and
  `apps/attachments/tasks.py` re-exports the task so
  `autodiscover_tasks` binds `attachments.process_attachment`. Retry is
  deliberately *not* here: it sits behind one seam function
  (`_retry_or_fail`) so MT-1.12-07 owns policy in one place (recorded
  per the MT risk note). Tests: `tests/attachments/test_pipeline_entry.py`
  (15 cases — checksum mismatch, type disagreement, dispatch table and
  allowlist rejection, status/event pairing, idempotent re-entry,
  soft-delete and unknown-id no-ops, seam wiring both layers).
- **MT-1.12-02 (image normalization + OCR)** —
  `apps/attachments/pipeline_images.py`: long edge capped at
  `ORCHESTRATOR_ATTACHMENT_IMAGE_MAX_EDGE_PX` (**2048 px**, aspect ratio
  preserved by construction), EXIF orientation applied *before* stripping
  so nothing is lost, re-encoded as metadata-free PNG on the **derived**
  copy only (original untouched, Section 9.5; proven by test), 50-megapixel
  in-process ceiling (Section 12.1 recorded limit), then OCR through the
  Section 6.6 pluggable interface in `apps/attachments/ocr.py` —
  `OcrEngine` protocol, `TesseractOcrEngine` subprocess over the CLI
  (`ORCHESTRATOR_OCR_ENGINE` default **`tesseract`**,
  `ORCHESTRATOR_OCR_TESSERACT_CMD` default **`tesseract`**, 30 s/page
  timeout; a missing binary is a human-readable permanent reason, never a
  silent empty transcript; unknown engine fails fast — Section 9.10).
  Layout captions call the description provider whose default is
  **disabled** (`ORCHESTRATOR_DESCRIPTION_PROVIDER`, OQ-07) so the stage
  completes OCR-only with zero WP-1.13 dependency; provider failures
  degrade to `""` (Section 9.5 contract, logged type-only). Normalized
  images live in `derived.py`'s registry under the per-attachment
  `derived_key` (re-run replaces, never duplicates; soft-delete, retention
  purge and `drop_derived_data` all remove them). Tests:
  `tests/attachments/test_image_pipeline.py` (14 — bounds/aspect,
  metadata stripping proof, engine selection and fail-fast, real Tesseract
  on the screenshot fixture with honest skip, provider-disabled path,
  ceilings, reprocess-replaces).
- **MT-1.12-03 (PDF text layer, OCR fallback for scanned pages)** —
  `apps/attachments/pipeline_pdf.py`: embedded text layer first; a page
  is treated as scanned **only when its layer yields no non-whitespace
  character** (the documented threshold — a one-character layer wins over
  OCR; recorded per the MT risk note, no silent every-page OCR), its
  embedded images are re-encoded to PNG and run through the shared
  engine; mixed PDFs OCR only the empty pages. Page boundaries persist as
  one string per page joined by the form-feed `PAGE_SEPARATOR` (WP-1.14
  paginates on it), so `page_number`/`total_pages` are derivable
  (Section 19 acceptance, data side). Worker-safety ceilings — 2000
  pages, 5,000,000 extracted chars, cooperative 60 s
  `ORCHESTRATOR_ATTACHMENT_PARSE_TIMEOUT_SECONDS` budget (expiry is
  transient → retried with backoff), encryption, zero pages, and every
  parser exception mapped to a human-readable permanent reason: malformed
  input fails the stage, never the worker (Section 12.1 in-process limits;
  OS-level sandboxing remains the plan's post-v1 Could). Tests:
  `tests/attachments/test_pdf_pipeline.py` (11 — text/scanned/mixed with
  OCR-invocation assertions, fixture-validates-image-only, real OCR,
  page boundaries, ceilings, malformed/empty/deadline paths).
- **MT-1.12-04 (DOCX and Markdown extraction)** —
  `apps/attachments/pipeline_documents.py`: the DOCX container opens
  read-only with a **declared**-uncompressed ceiling of 64 MiB checked
  before reading (zip-bomb guard, Section 12.1), then
  `word/document.xml` streams in document order to markdown-flavoured
  text (headings → `#` prefixes by style, numbering → `- ` items, tables
  → pipe rows, the rest → paragraphs). Markdown/plain text decode as
  UTF-8 with CRLF/CR → LF and leading-BOM normalization and pass through
  otherwise unchanged (acceptance: content preserved); non-UTF-8 fails
  permanently. All parser failures (bad zip/CRC, malformed XML, missing
  body) become human-readable reasons — the worker survives hostile
  input (Section 12.1; tested). Extracted text shares the 5,000,000-char
  ceiling. Tests: `tests/attachments/test_document_extraction.py` (9 —
  structure in order, determinism, normalization/BOM, plain pass-through,
  zip-without-part, malformed XML, zip ceiling, non-UTF-8).
- **MT-1.12-05 (page/chunk splitting + token estimation)** —
  `AttachmentChunk` model + migration
  `0002_attachmentchunk` (sequence, nullable `page_number`, text,
  per-chunk `token_estimate`; unique `(attachment, sequence)`; check
  constraints; sensitive-content help text — Section 12.4).
  `apps/attachments/chunking.py` splits page-oriented outputs (PDF, image
  OCR) into contiguous numbered pages `1..N` with `page_count = total`
  and further into token-bounded chunks at
  `ORCHESTRATOR_ATTACHMENT_CHUNK_MAX_TOKENS` (**512**) via a hierarchical
  blank-line → line → word split with a final character slice, so **no
  text is ever dropped** (coverage invariant asserted). Estimation is the
  deterministic documented default
  `ORCHESTRATOR_ATTACHMENT_TOKEN_ESTIMATOR=chars_div_4`
  (`ceil(chars/4)`; unknown values fail fast — a model-accurate tokenizer
  would be a new OQ, recorded per the risk note); the roll-up
  `token_estimate` equals the sum of chunks by construction (FR-ATT-03
  descriptor field). Re-running deletes and rebuilds the rows in one
  transaction — deterministic, replace-not-duplicate. Tests:
  `tests/attachments/test_chunking.py` (11 — estimator default and
  fail-fast, bounds (incl. hard-split single token), coverage invariant,
  large-PDF numbering `1..12`, roll-up equality, deterministic re-run,
  page-vs-chunk path selection, persistent bound override).
- **MT-1.12-06 (short summary per document)** —
  `apps/attachments/summarize.py`: `SummaryProvider` protocol with the
  Section 22 OQ-07 default **disabled** (`ORCHESTRATOR_ATTACHMENT_SUMMARY_PROVIDER`
  — no generative provider invented before the owner decision) backed by
  a deterministic extractive head-of-document fallback, so the pipeline
  completes fully offline. Input is bounded by
  `ORCHESTRATOR_ATTACHMENT_SUMMARY_BUDGET_TOKENS` (**512**) over the
  chunk sequence; output by `ORCHESTRATOR_ATTACHMENT_SUMMARY_MAX_TOKENS`
  (**120**) — "short" is this documented bound, recorded here because the
  plan says short, not how short (MT risk note). Provider failures (and
  over-long provider output) degrade to the fallback, logged type-only —
  cost/failure never fails the pipeline (Section 9.5 degradation by
  analogy). Images summarise from their OCR transcript (layout captions
  arrive with WP-1.13; not waited for). The result persists to
  `description` → the descriptor's `short_description` (FR-ATT-03).
  P10 is enforced by construction — the extractive fallback only quotes —
  and by tests: the injection fixture ("ignore previous instructions…")
  is summarised *as data*, never obeyed, on both the fallback and provider
  paths. Tests: `tests/attachments/test_summary.py` (15 — every document
  kind, image transcript input, descriptor exposure, fallback default,
  fail-fast/degradation, budget and output bounds, empty input, injection
  handling).
- **MT-1.12-07 (status transitions + retry/backoff)** —
  `apps/attachments/status.py` is the four-value FR-ATT-07 machine with
  the explicit `LEGAL_TRANSITIONS` table (`uploaded → processing →
  ready | failed`; terminal states absorbing) and per-transition tests.
  Every transition is **compare-and-set** — a single conditional `UPDATE`
  guarded on the current status (row lock on entry) so two workers or a
  late retry racing a manual outcome cannot both win — with the event row
  written **inside the same transaction** via the MT-1.9-02 helper:
  exactly one `attachment.processing` and exactly one terminal
  `attachment.ready`/`attachment.failed` per attachment (Section 9.6;
  Section 20.4 item 6); soft-deleted rows never emit; stale completions
  lose the CAS and write nothing (tested). Failure reasons are truncated
  to 1000 chars, never contain attachment content (Section 12.4), and are
  exposed on the descriptor as `failure_reason` — the serializer's one
  documented addition (FR-ATT-07 "visible"; OpenAPI follow-up below).
  Retry wiring lives only in `pipeline.py`: `PermanentPipelineError` lands
  `failed` at once; `TransientPipelineError` and unexpected exceptions
  (reason = type name only) re-enter through `_retry_or_fail` —
  exponential backoff `ORCHESTRATOR_ATTACHMENT_RETRY_BACKOFF_SECONDS`
  (**60 s**) × 2^(n−1) up to `ORCHESTRATOR_ATTACHMENT_RETRY_MAX_ATTEMPTS`
  (**3**) total, then `failed` with the reason (Section 9.9; documented
  choices, not plan facts). Tests:
  `tests/attachments/test_processing_status.py` (14 — transition matrix
  and only-the-four-statuses, exactly-once event pairs, resume-silently,
  stale/soft-delete guards, transient retry → ready, exhaustion → failed
  with reason, backoff and cap from configuration, permanent-never-retries,
  descriptor reason exposure).
- **MT-1.12-08 (sample-corpus tests)** —
  `tests/attachments/fixtures/corpus/` holds exactly the Section 19 set —
  screenshot (PNG), scanned PDF (validated image-only *inside* the suite
  so the OCR assertions cannot pass vacuously), text PDF, DOCX, Markdown
  — plus `large.pdf` (12 pages) for numbering; all generated by
  `tests/attachments/fixtures/build_fixtures.py` (self-generated,
  license-clean provenance per Section 20.4 item 3; each < 500 KB).
  `tests/attachments/test_sample_corpus.py` (10 cases) drives every
  member through the real multipart endpoint and asserts, via the public
  descriptor API: all six end `ready` with token count, summary and
  exactly-one event pair; a structurally broken PDF ends `failed` with a
  non-empty human-readable reason; kind-specific derived data (normalized
  artifact + transcript, text-layer-without-OCR, OCR fallback used,
  DOCX/markdown extraction, contiguous `1..12` pages with
  `page_count = 12`); OCR needles assert only where the real engine ran —
  **Tesseract v5.4.0 is present on this host, so the real path is
  asserted, not stubbed**. The "real worker" item is closed by
  `tests/integration/test_attachment_pipeline_worker.py` (new): it
  spawns `python -m celery -A config.celery worker --pool solo` — the
  Compose worker service's command — against real Redis and real
  Postgres, uploads through the real post-commit `delay()` seam, and
  observes terminal status plus `attachment-pipeline`-authored events
  **written by the worker process** (the test process never runs a
  stage); it auto-skips on the SQLite unit layer with the exact command
  in its reason. Original-agent run record: the `wp112-e2e` Compose
  stack (compose.yaml + compose.dev.yaml, `orchestrator-backend:dev`
  image) came up with the worker registering `attachments.process_attachment`
  but the outage preceded any task; this finisher completed the run on
  the protocol stack (`docker start wp16-pg wp16-redis`, port 5434,
  `--ds apps.core.settings.dev`) — **4 passed** (real-worker test + the
  three WP-1.11 Postgres counter races).
- **Finisher verification (post-502)** — all eight MTs audited
  acceptance-criterion by criterion against the surviving files (every
  pipeline module, suite, migration, settings row, `.env.example` entry
  and `configuration.md` row was present; the only gaps were this
  changelog and the unconsumed real-worker run above). Two defects
  fixed: (1) `tests/attachments/test_descriptor_listing.py`'s
  newest-first assertion was clock-flaky on this host — the Windows wall
  clock ticks coarsely (20 k consecutive `now()` reads yielded 4 unique
  values), so two uploads inside one tick tie on `created_at` and the
  documented `(-created_at, -id)` tiebreak legitimately outranks
  insertion order; the test now pins the first row 5 s older (assertion
  unchanged, precondition explicit). (2) The WP-1.11 Postgres race suite
  failed standalone under the dev layer because the test process never
  bound the project Celery app, so `shared_task` published to a default
  AMQP endpoint and every upload worker errored with connection-refused —
  one `config.celery` import (the `config/__init__.py` contract;
  same precedent as `test_sweeper_chaos_postgres.py`) makes it publish
  to the configured broker: 3/3 standalone green. Final battery on this
  host: `ruff check` ✓, `ruff format --check` ✓ (45 territory files),
  `mypy` ✓ (47 territory files), `manage.py check` ✓,
  `makemigrations --check` ✓ ("No changes detected"), targeted pytest
  **199 passed** (`tests/attachments`) + **4 passed**
  (`tests/integration` attachment suites, `--ds apps.core.settings.dev`).
  Documented defaults (Section 20.4 item 3) are tabulated in
  `docs/plan/conventions/configuration.md` and mirrored in
  `infra/compose/.env.example`.

**Follow-ups (not done here):**

- `schemas/openapi.yaml` must be regenerated to publish the descriptor's
  `failure_reason` field — the audit/merge finisher is the sole
  OpenAPI regenerator in this wave (serializer help text already flags
  it).
- WP-1.13: real description providers (`anthropic`-compatible vision /
  local model) replace the disabled default and start writing
  `layout_caption`; OQ-07 remains an owner decision.
- If a model-accurate tokenizer is ever demanded, raise it as a new OQ
  first (MT-1.12-05 risk note) — `chars_div_4` is the recorded choice,
  not a plan fact.
- The wp112-e2e Compose stack left running by the original agent is
  unowned infrastructure; stop or reuse at the operator's discretion.
