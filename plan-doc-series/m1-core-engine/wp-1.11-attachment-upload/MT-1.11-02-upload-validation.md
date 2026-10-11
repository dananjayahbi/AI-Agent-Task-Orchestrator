# MT-1.11-02 — Implement Upload Validation: Size, MIME Content Sniffing, De-Duplication

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.11-02 |
| Title | Implement upload validation: size, MIME content sniffing, de-duplication |
| Parent WP | WP-1.11 — Attachment storage and upload API (Milestone M1) |
| Requirements | FR-ATT-01 |
| Priority | M |
| Dependencies | MT-1.11-01 (storage abstraction and content-addressed keys) |
| Parent sections | 9.5, 12.1, 19.1 (WP-1.11), 20.4, 20.5 |

## Context
Section 9.5 fixes the limits and safety rules (all default, configurable): 25 MB per
file; 10 attachments per task; 100 MB total; allowlist `image/png`, `image/jpeg`,
`image/webp`, `application/pdf`, DOCX, `text/markdown`, `text/plain`; MIME verified
by **content sniffing, not extension**; files stored under content-hash keys with
de-duplication. Section 12.1 lists malicious uploads among the threats ("type
sniffing, size limits"). Section 19 (WP-1.11) acceptance: disallowed types and
oversize files rejected with clear errors; duplicate uploads de-duplicated.

## Inputs / Prerequisites
* MT-1.11-01 — storage abstraction and content-hash key derivation.
* Parent plan Section 9.5 — exact limits, allowlist and sniffing requirement.
* Section 9.2 canonical error codes — `VALIDATION_ERROR`,
  `ATTACHMENT_UNSUPPORTED_FORMAT` (no invented codes, Section 20.4 item 5).
* WP-0.5 error-envelope conventions for the rejection responses.

## Scope (in)
* A validation stage run before any bytes are stored: per-file size cap (25 MB),
  per-task count (10) and total-size (100 MB) caps — all configurable with the
  Section 9.5 defaults.
* MIME validation by content sniffing against the Section 9.5 allowlist; extension
  alone never decides; a mismatch between sniffed type and declared type is rejected.
* De-duplication: if the content hash already exists for the task, the upload maps
  to the existing attachment instead of storing a second copy.
* Clear rejection responses using canonical codes: wrong type →
  `ATTACHMENT_UNSUPPORTED_FORMAT`; oversize/over-count/over-total →
  `VALIDATION_ERROR` with details, per the WP-0.5 envelope conventions.
* Tests: each limit boundary (25 MB at/over), each allowlisted type accepted,
  disguised type (e.g. executable bytes named `.png`) rejected, duplicate upload
  de-duplicated.

## Out of scope
* The HTTP endpoint wiring — MT-1.11-03 (this stage is endpoint-independent).
* ClamAV/AV scanning — explicitly "Could" in Section 9.5; not v1.
* Storage backends — MT-1.11-01.
* Pipeline processing of accepted files — WP-1.12.
* Rate limiting/abuse controls — WP-1.2 (API) and WP-5.2 (edge).

## Target paths
* `backend/apps/attachments/validation.py`
* `backend/tests/attachments/test_upload_validation.py`
* Environment template entries for the configurable limits (documented defaults)
* WP changelog entry

## Acceptance criteria
- [ ] Disallowed types are rejected using content sniffing, not extension, with
  `ATTACHMENT_UNSUPPORTED_FORMAT` (Section 9.5; Section 19 WP-1.11 acceptance).
- [ ] Oversize files (over 25 MB default) and per-task count/total caps are rejected
  with a clear `VALIDATION_ERROR` (Section 9.5).
- [ ] The allowlist matches Section 9.5 exactly — no types added or dropped
  (Section 20.5).
- [ ] Duplicate uploads (same content hash) de-duplicate to one stored object and one
  attachment record (Section 19 WP-1.11 acceptance).
- [ ] Error codes used exist in the catalog (Section 20.4 item 5); limits have
  documented defaults (item 3); changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_upload_validation.py -v` — boundary cases for
every limit, allowlist acceptance/rejection, sniffing bypass attempt, and
de-duplication.

## Attachments
* [Section 9.5 — Attachment processing (limits and safety)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.1 — Threat model (malicious uploads)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.11 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Sniffing libraries disagree on some formats (DOCX is a zip container; Markdown is
  plain text) — for zip-based DOCX verify the internal structure, not just the
  `application/zip` magic; document the decision in the changelog note.
* The "10 attachments per task / 100 MB total" counters must be computed atomically
  at write time or concurrent uploads can overshoot; include a concurrent test.
