# MT-1.12-02 — Implement Image Normalization and OCR Stage

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.12-02 |
| Title | Implement image normalization and OCR stage |
| Parent WP | WP-1.12 — Attachment pipeline: parse, OCR, chunk, tokens (Milestone M1) |
| Requirements | FR-ATT-02 |
| Priority | M |
| Dependencies | MT-1.12-01 (pipeline entry and dispatch) |
| Parent sections | 9.5, 9.10, 19.1 (WP-1.12), 20.4, 20.5 |

## Context
Section 9.5, images stage: "normalize resolution (cap long edge, keep aspect ratio),
strip metadata, run OCR, generate a layout caption (component list, text positions)
through the description provider." The description provider is a **later WP**
(WP-1.13, OQ-07: disabled by default) — this task does normalization, metadata
stripping and OCR only; the layout caption is produced when WP-1.13 lands. The OCR
engine is an environment-driven setting (Section 9.10).

## Inputs / Prerequisites
* MT-1.12-01 — dispatch to this stage for image types (`image/png`, `image/jpeg`,
  `image/webp` per Section 9.5).
* Parent plan Section 9.5 — exact normalization rules.
* Parent plan Section 9.10 — OCR engine setting with documented default.
* Worker service (MT-1.7-01) with the media volume mounted (Section 16.1) so stored
  images are readable.

## Scope (in)
* Normalization: cap the long edge at a configurable limit, preserve aspect ratio,
  strip all metadata (EXIF etc.), store the normalized image as derived data.
* OCR stage: run the configured OCR engine over the normalized image; persist the
  transcript as derived data.
* Deterministic behavior under re-processing: derived data is re-creatable
  (Section 9.5), so a repeat run replaces rather than duplicates.
* Tests: normalization caps long edge and keeps aspect ratio; metadata is absent
  from the normalized output; OCR transcript extracted from a sample screenshot
  fixture; OCR engine selection follows configuration.

## Out of scope
* Layout caption / description provider — WP-1.13 (Section 9.5 defers it; OQ-07
  default disabled). Degradation to OCR-only must remain possible.
* Chunking, token estimation, summaries — MT-1.12-05/06.
* PDF and document stages — MT-1.12-03/04.
* Status transitions and retries — MT-1.12-07.
* Mobile/web retrieval formats (`image_base64`, `text_ocr`) — WP-1.14.

## Target paths
* `backend/apps/attachments/pipeline_images.py`
* `backend/tests/attachments/test_image_pipeline.py`
* `backend/tests/attachments/fixtures/` (sample screenshot)
* Environment template entry: OCR engine default (Section 9.10)
* WP changelog entry

## Acceptance criteria
- [ ] Normalized images have the long edge capped at the configured limit with aspect
  ratio preserved (Section 9.5).
- [ ] Metadata is stripped from the normalized output (Section 9.5).
- [ ] An OCR transcript is produced with the configured engine and stored as derived
  data (FR-ATT-02).
- [ ] With the description provider disabled (OQ-07 default), the stage completes
  successfully OCR-only — no dependency on WP-1.13 code (Section 9.5).
- [ ] OCR setting has a documented default (Section 9.10; Section 20.4 item 3);
  changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_image_pipeline.py -v` — normalization bounds,
metadata stripping, OCR transcript on the screenshot fixture, provider-disabled path.

## Attachments
* [Section 9.5 — Attachment processing (images stage)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.10 — Configuration (OCR engine)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.12 deliverables](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* OCR engine choice/accuracy is configuration-dependent (Section 9.10); the test
  fixture must work with the default engine — if no offline-capable default exists
  in the environment, raise a new OQ (`OQ-15+`) rather than pinning a cloud service
  implicitly.
* Stripping metadata happens on the **derived** copy; the original is retained
  (Section 9.5) — confirm tests never mutate the stored original.
