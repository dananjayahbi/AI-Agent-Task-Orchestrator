# MT-1.12-01 — Implement Pipeline Type Detection and Checksum Stage

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.12-01 |
| Title | Implement pipeline type detection and checksum stage |
| Parent WP | WP-1.12 — Attachment pipeline: parse, OCR, chunk, tokens (Milestone M1) |
| Requirements | FR-ATT-02, FR-ATT-07 |
| Priority | M |
| Dependencies | MT-1.11-05 (WP-1.11 complete), MT-1.7-01 (Celery worker and beat wired) |
| Parent sections | 9.5, 9.9, 19.1 (WP-1.12), 20.4, 20.5 |

## Context
Section 9.5 pipeline stage 1: "Detect and validate type, compute checksum,
de-duplicate." Section 9.9: the attachment pipeline job runs "on upload" with retry
with backoff. Section 19 (WP-1.12): worker tasks for images and documents depend on
WP-1.11 and WP-1.7 (Celery in place). This task builds the pipeline entry: the
worker-side orchestrator that receives an uploaded attachment, re-establishes its
type and checksum, sets status `processing`, and dispatches to the format-specific
stages that follow.

## Inputs / Prerequisites
* MT-1.11-03 — the enqueue seam on upload (completed here: worker task registered).
* MT-1.11-01/02 — content-addressed storage and validated uploads (checksum already
  computed at validation; the pipeline re-derives it against the stored object).
* MT-1.7-01 — Celery worker service in Compose (Section 9.9).
* Parent plan Section 9.5 — stage list and defaults.
* Section 9.6 — `attachment.processing` is in the event catalog.

## Scope (in)
* The Celery task that starts pipeline processing for an `uploaded` attachment:
  load the stored object, verify the checksum against the record (integrity check),
  detect the final type from content (not the recorded extension), and de-duplicate
  re-processing of an attachment already handled.
* Status transition `uploaded` → `processing` (FR-ATT-07) with an
  `attachment.processing` event written in-transaction via the MT-1.9-02 helper.
* Dispatch table: image types → MT-1.12-02 stage; PDF → MT-1.12-03; DOCX/Markdown →
  MT-1.12-04 (stubs registered now, implemented by those tasks).
* Completing the MT-1.11-03 enqueue seam so uploads actually reach the worker.
* Tests: checksum mismatch handling, type re-detection, idempotent re-entry (no
  duplicate processing), status/event assertions.

## Out of scope
* The image/PDF/document stages themselves — MT-1.12-02/03/04.
* Chunking, token estimation, summaries — MT-1.12-05/06.
* Retry/backoff policy and final status handling — MT-1.12-07 (stub status
  transitions only as needed for this stage's tests).
* Publish gating on `ready` (FR-ATT-07 second half) — belongs to task transition
  logic (WP-1.5/WP-1.4); not changed here.
* ClamAV stage — "Could", not v1 (Section 9.5).

## Target paths
* `backend/apps/attachments/pipeline.py` (entry task and dispatch)
* `backend/apps/attachments/views.py` (complete the enqueue seam)
* `backend/tests/attachments/test_pipeline_entry.py`
* WP changelog entry

## Acceptance criteria
- [ ] An upload enqueues the pipeline worker task and it runs in the Compose worker
  service (Section 9.9 "on upload").
- [ ] The stage verifies the stored object's checksum and re-detects type from
  content; a checksum mismatch fails the attachment with a clear reason rather than
  processing (Section 9.5 stage 1).
- [ ] Status moves `uploaded` → `processing` and exactly one `attachment.processing`
  event is written in-transaction (Section 9.6; Section 20.4 item 6).
- [ ] Re-delivery of the same job does not duplicate processing or events.
- [ ] Lint, type check and tests green (item 2); error codes from the catalog
  (item 5); changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_pipeline_entry.py -v` — entry task behavior,
checksum/type verification, status and event assertions, idempotent re-entry.

## Attachments
* [Section 9.5 — Attachment processing (stage 1)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.9 — Background jobs (attachment pipeline)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.12 deliverables](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Stage ordering vs. retry: this task must not implement backoff itself (MT-1.12-07
  owns it) — register the task so retry can be added in one place; note the seam in
  the changelog.
* Detection in the pipeline could disagree with the upload-time sniffing result
  (MT-1.11-02); a disagreement is a data-integrity signal — fail with a human-
  readable reason, do not silently trust either side.
