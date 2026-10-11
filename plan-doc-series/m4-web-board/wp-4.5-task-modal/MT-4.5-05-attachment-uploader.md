# MT-4.5-05 — Implement the attachment uploader with progress and processing status

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.5-05 |
| Title | Implement the attachment uploader with progress and processing status |
| Parent WP | WP-4.5 — Task creation/edit modal and attachment uploader (Milestone M4) |
| Requirements | FR-WEB-03, FR-ATT-07 |
| Priority | M |
| Dependencies | MT-4.5-01 (modal scaffold), WP-1.11 (upload endpoint), WP-1.12 (pipeline, processing_status), WP-4.3 (SSE stream hook and cache patching) |
| Parent sections | 13.2, 9.5, 9.6, 9.2, 19 (WP-4.5), 20.4, 20.5 |

## Context
Section 13.2's modal includes an "attachment dropzone with per-file processing
status". FR-ATT-07: "Processing status (`uploaded`, `processing`, `ready`, `failed`)
is visible, and tasks can be published only when attachments are `ready` or
explicitly overridden" — the readiness half is MT-4.5-06; visibility and progress are
here. Section 9.5 fixes the limits (25 MB per file; 10 attachments per task; 100 MB
total; type allowlist `image/png`, `image/jpeg`, `image/webp`, `application/pdf`,
DOCX, `text/markdown`, `text/plain`; MIME verified by content sniffing) and the
pipeline's statuses and events. Section 9.6's catalog carries
`attachment.processing|ready|failed` — WP-4.5's deliverable is "uploader with status
via stream events".

## Inputs / Prerequisites
* Parent plan Section 13.2 — dropzone with per-file processing status.
* Parent plan Section 9.5 — limits, allowlist, pipeline stages, status semantics.
* Parent plan Section 9.6 — `attachment.processing|ready|failed` events; Section 9.2
  — `POST /tasks/{id}/attachments` (multipart), `DELETE /attachments/{id}`.
* WP-1.11 — upload endpoint and pre-validation; WP-1.12 — pipeline setting
  `processing_status` and emitting events.
* WP-4.3 (MT-4.3-04/05) — SSE stream hook and cache patching for live status.
* Catalog codes: `ATTACHMENT_NOT_READY`, `ATTACHMENT_UNSUPPORTED_FORMAT`,
  `VALIDATION_ERROR`.

## Scope (in)
* A dropzone in the task modal: drag-and-drop and file-picker upload to
  `POST /tasks/{id}/attachments` (multipart) through the typed client, with
  per-file upload progress.
* Client-side pre-checks mirroring Section 9.5 (allowlist types, 25 MB per file,
  10-per-task and 100 MB total) for instant feedback, with the server remaining the
  authority (content sniffing happens server-side — never trust the client MIME).
* Per-file processing status UI: `uploaded` → `processing` → `ready` / `failed`,
  driven by the SSE `attachment.processing|ready|failed` events (Section 9.6)
  applied through the WP-4.3 cache patching — no polling loop invented.
* `failed` files show the pipeline's human-readable reason (Section 9.5) with a
  dismiss/remove affordance (`DELETE /attachments/{id}`); server rejections
  (oversize, disallowed type) map to friendly canonical messages.
* Draft-task context: uploads attach to the task being created/edited; if the task
  does not exist yet, uploads start after create (the endpoint requires a task id) —
  sequence explicitly, no phantom uploads.
* Component tests: drop and picker upload; progress rendering; status transitions
  from simulated stream events; oversize/type rejection messages; failed-reason
  display; remove; no-polling assertion (status only via events).

## Out of scope
* Publish gating on readiness — MT-4.5-06 (T2).
* The pipeline itself (OCR, description, normalization) — WP-1.12/WP-1.13.
* The upload backend and its security checks — WP-1.11 (traversal, sniffing, limits).
* Attachment viewing (OCR/description tabs) — WP-4.6.
* The `ATTACHMENT_NOT_READY` read-path tool behavior — WP-2.5.

## Target paths
* `web/` — dropzone, progress and status components; stream-event wiring
* `web/tests/` — uploader component tests
* WP changelog entry

## Acceptance criteria
- [ ] Files upload via the multipart endpoint with visible per-file progress
  (Section 13.2, FR-WEB-03).
- [ ] Per-file status shows the exact Section 9.5/FR-ATT-07 values — `uploaded`,
  `processing`, `ready`, `failed` — updated from `attachment.processing|ready|failed`
  stream events, not polling (Sections 9.6, WP-4.5 deliverable).
- [ ] Client pre-checks mirror the Section 9.5 limits/allowlist for instant feedback;
  server rejections map to canonical messages (`VALIDATION_ERROR`,
  `ATTACHMENT_UNSUPPORTED_FORMAT`) (Section 13.3).
- [ ] `failed` status surfaces the pipeline's human-readable reason and allows
  removal via `DELETE /attachments/{id}` (Section 9.5).
- [ ] Only catalog error codes used (Section 20.4 item 5); lint/type/tests green
  (item 2); changelog note added (item 7).

## Test command
`npm test -- -t attachment-uploader` — assert drop/picker upload with progress,
status transitions from simulated stream events (no polling), limit/type rejection
messages, failed-reason display, and removal; then the full web suite stays green.

## Attachments
* [Section 9.5 — Attachment processing](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.6 — Realtime gateway and event model](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Status must come from stream events — a polling fallback would mask reconnect
  bugs and violate the WP deliverable; if the stream is down, show a "status
  unknown, reconnecting" state driven by the existing stream status indicator.
* Client limit checks are UX only: the server enforces sniffing and sizes
  (WP-1.11); do not disable server errors the client happened to allow.
* Uploads of a not-yet-created task need an explicit sequence (create draft first,
  then upload); half-completed creates must not leave orphaned uploads — test the
  cancel-during-create path.
