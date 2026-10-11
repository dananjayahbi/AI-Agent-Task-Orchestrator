# MT-1.11-01 — Create the Storage Abstraction Layer (Local Volume + S3-Compatible Seam)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.11-01 |
| Title | Create the storage abstraction layer (local volume + S3-compatible seam) |
| Parent WP | WP-1.11 — Attachment storage and upload API (Milestone M1) |
| Requirements | FR-ATT-01 |
| Priority | M |
| Dependencies | MT-1.4-06 (WP-1.4 complete; task model exists to attach to) |
| Parent sections | 9.5, 16.3, 9.10, 19.1 (WP-1.11), 20.4, 20.5 |

## Context
Section 16.3: local named volumes by default; a storage abstraction supports
S3-compatible object storage **by configuration only**; patch artifacts and
attachments share this abstraction; keys are content-addressed. Section 9.5: files
are stored under content-hash keys, originals are retained, derived data is
re-creatable. Section 19 (WP-1.11) deliverables: content-addressed storage behind the
abstraction. This task builds the seam before any endpoint touches it.

## Inputs / Prerequisites
* Parent plan Section 9.5 — limits/safety: content-hash keys, original retention,
  re-creatable derived data.
* Parent plan Section 16.3 — default local volumes, config-only S3 switch, shared
  abstraction with patch artifacts (WP-1.10-era patches land in M3 — keep the seam
  generic).
* Parent plan Section 9.10 — storage backend is an environment-driven setting with a
  documented default (local volume).
* Module layout Section 9.1 — `attachments` module.
* WP-1.1 — backend container with the media volume mounted (Section 16.1).

## Scope (in)
* A storage interface (put / get / exists / delete / open-by-key) used by the
  attachments module, with two implementations selected by configuration: local
  named-volume backend (default) and an S3-compatible backend seam.
* Content-addressed key derivation: key = content hash (per Section 9.5/16.3), so
  identical bytes map to one stored object (foundation for de-duplication in
  MT-1.11-02).
* Configuration surface per Section 9.10: backend selector, local root path, S3
  endpoint/bucket/credentials placeholders — documented defaults, no real values
  committed (Section 20.4 item 3).
* Unit tests for both backends against the same contract test suite (local backend
  fully exercised; S3 backend exercised against an interface-level fake or skipped
  with an explicit marker if no fixture exists).

## Out of scope
* Upload validation (size/MIME/sniffing) — MT-1.11-02.
* The multipart endpoint — MT-1.11-03.
* Retention/deletion rules — MT-1.11-05.
* Patch artifact storage consumers — M3 (WP-3.x); only the seam is shared.
* Provisioning real S3 buckets — operations, not this task; S3 configuration remains
  a documented seam.

## Target paths
* `backend/apps/attachments/storage.py`
* `backend/tests/attachments/test_storage.py`
* `infra/compose/` environment template entries (documented defaults only)
* WP changelog entry

## Acceptance criteria
- [ ] One interface is used by both a working local-volume backend (default) and an
  S3-compatible backend reachable by configuration only (Section 16.3).
- [ ] Keys are content-addressed: the same bytes produce the same key from either
  backend (Sections 9.5, 16.3).
- [ ] The backend contract test suite passes against the local backend; the S3
  implementation is selected purely by configuration (Section 9.10).
- [ ] No secrets or environment-specific paths committed (Section 20.4 item 3);
  public contract unchanged so no schema diff is required (item 4 — N/A noted);
  changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_storage.py -v` — contract suite (put/get/
exists/delete, content-addressed key stability) for the local backend and the S3
seam's configuration path.

## Attachments
* [Section 9.5 — Attachment processing (storage rules)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.3 — Storage](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.10 — Configuration](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The abstraction is shared with patch artifacts (Section 16.3) — over-fitting it to
  attachment-only assumptions now causes a refactor in M3; keep operations generic
  (opaque bytes + metadata).
* Content-hash keys expose identical-file equality across tasks; the plan accepts
  this (de-duplication is a deliverable), but access control must still be enforced
  per attachment record, not by key secrecy — flag in review.
