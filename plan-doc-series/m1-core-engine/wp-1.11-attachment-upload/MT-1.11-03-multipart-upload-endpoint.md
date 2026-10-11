# MT-1.11-03 — Implement the Multipart Attachment Upload Endpoint

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.11-03 |
| Title | Implement the multipart attachment upload endpoint |
| Parent WP | WP-1.11 — Attachment storage and upload API (Milestone M1) |
| Requirements | FR-ATT-01 |
| Priority | M |
| Dependencies | MT-1.11-02 (validation stage) |
| Parent sections | 9.2, 9.5, 9.9, 19.1 (WP-1.11), 20.4, 20.5 |

## Context
Section 9.2: `POST /tasks/{id}/attachments` (multipart), caller Owner (agents read
only), and all mutating endpoints accept an idempotency key header. Section 9.5: on
upload the file is stored and the processing pipeline runs in the worker (Section
9.9: "Attachment pipeline — on upload"). Section 19 (WP-1.11) deliverable: the
upload endpoint. FR-ATT-07: a new attachment starts in `uploaded` status.

## Inputs / Prerequisites
* MT-1.11-02 — validation and de-duplication stage.
* MT-1.11-01 — storage abstraction used to persist accepted bytes.
* Parent plan Section 9.2 — endpoint path, caller, idempotency-key requirement.
* WP-0.5 conventions — error envelope, idempotency header, pagination (for responses
  elsewhere).
* WP-1.4 — task lookup and 404/`TASK_NOT_FOUND` behavior.

## Scope (in)
* `POST /tasks/{id}/attachments` accepting multipart form data from the web/mobile
  uploaders (FR-ATT-01), authenticated as Owner, validating through the MT-1.11-02
  stage, storing via the MT-1.11-01 abstraction, and creating the attachment record
  with `processing_status` = `uploaded` (FR-ATT-07).
* Idempotency-key handling per Section 9.2 (repeat submit returns the original
  result, no duplicate records).
* Response: attachment descriptor (id, filename, size, status — the fields the
  listing task exposes; token count/summary fields arrive with WP-1.12).
* A hook point that enqueues the pipeline job for WP-1.12 — enqueued job itself is
  wired by MT-1.12-01; here the seam exists and is a no-op/skippable.
* OpenAPI schema updated, schema diff reviewed (Section 20.4 item 4).

## Out of scope
* Pipeline stages and the worker job — WP-1.12.
* Descriptor listing endpoint — MT-1.11-04.
* Deletion — MT-1.11-05.
* Upload from mobile capture / FR-MOB-08 — Could (OQ-12: task creation from mobile
  out of v1 scope); the endpoint stays the same, client work is later.
* Agent uploads — Section 9.2 gives agents read access only.

## Target paths
* `backend/apps/attachments/views.py`
* `backend/apps/attachments/urls.py`
* `backend/tests/attachments/test_upload_endpoint.py`
* WP changelog entry

## Acceptance criteria
- [ ] `POST /tasks/{id}/attachments` accepts a valid multipart upload from an
  authenticated Owner and returns a descriptor with status `uploaded`.
- [ ] Invalid payloads return canonical errors (`ATTACHMENT_UNSUPPORTED_FORMAT`,
  `VALIDATION_ERROR`, `TASK_NOT_FOUND`) with the Section 9.2 envelope (Section 20.4
  item 5).
- [ ] Replaying the same idempotency key does not create a second attachment
  (Section 9.2).
- [ ] The pipeline enqueue seam exists and is exercised by a test (stub behavior
  documented) for MT-1.12-01 to complete.
- [ ] OpenAPI document updated with schema diff reviewed (Section 20.4 item 4);
  changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_upload_endpoint.py -v` — happy path,
rejection paths, idempotency replay, and enqueue-seam assertion.

## Attachments
* [Section 9.2 — REST API surface (attachments endpoints)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.5 — Attachment processing](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.11 deliverables](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Multipart handling interacts with request size limits at the ASGI/reverse-proxy
  layer; a 25 MB body must not be rejected earlier with a non-canonical error —
  align server/proxy limits with the Section 9.5 default and note it in the
  changelog.
* The enqueue seam is a temporary stub: without the MT-1.12-01 completion note, files
  could sit in `uploaded` forever — keep the pending item visible in the changelog.
