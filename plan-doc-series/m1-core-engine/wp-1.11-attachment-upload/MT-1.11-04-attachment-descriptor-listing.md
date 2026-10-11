# MT-1.11-04 — Implement Attachment Descriptor Listing (id, Filename, Size, Status)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.11-04 |
| Title | Implement attachment descriptor listing (id, filename, size, status) |
| Parent WP | WP-1.11 — Attachment storage and upload API (Milestone M1) |
| Requirements | FR-ATT-01, FR-ATT-03 |
| Priority | M |
| Dependencies | MT-1.11-03 (uploads create attachment records) |
| Parent sections | 9.2, 9.5, 19.1 (WP-1.11), 20.4, 20.5 |

## Context
Section 9.2: `GET /tasks/{id}/attachments` (list) and `GET /attachments/{id}`
(single). Section 19 (WP-1.11) deliverable: descriptor listing. FR-ATT-03: the
default task payload contains only attachment descriptors (id, filename, size, token
count, short description) — token count and short description are produced by the
pipeline (WP-1.12), so they appear as nullable fields until `ready`. FR-ATT-07: the
`processing_status` values `uploaded`, `processing`, `ready`, `failed` are visible.

## Inputs / Prerequisites
* MT-1.11-03 — attachment records with `uploaded` status.
* MT-0.5-04 — cursor-based pagination conventions for all list endpoints.
* Parent plan Section 9.2 — endpoint paths and callers (Owner; agents read own
  project).
* WP-0.5 error-envelope conventions.

## Scope (in)
* `GET /tasks/{id}/attachments` returning descriptors: `id`, `filename`, `size`,
  `processing_status`, plus the FR-ATT-03 fields (`token count`, `short description`)
  as null until the pipeline fills them.
* `GET /attachments/{id}` returning one descriptor, with the same access rules.
* Cursor-based pagination per the WP-0.5 conventions; ordering stable (by id).
* Authorization: Owner sees own-project attachments; agent tokens see only their
  project's attachments (Section 12.1 project filtering; `AUTH_FORBIDDEN_PROJECT`
  otherwise).
* OpenAPI updated, schema diff reviewed (Section 20.4 item 4).

## Out of scope
* Content retrieval with `format_preference` and pagination of document pages —
  WP-1.14 (`GET /attachments/{id}/content`).
* Producing token counts/summaries — WP-1.12 (this task only exposes the fields).
* Upload and deletion — MT-1.11-03 / MT-1.11-05.
* Embedding descriptors in the task payload — WP-1.4/task serialization (field shape
  is fixed here so that work reuses it).

## Target paths
* `backend/apps/attachments/views.py`
* `backend/apps/attachments/serializers.py`
* `backend/tests/attachments/test_descriptor_listing.py`
* WP changelog entry

## Acceptance criteria
- [ ] `GET /tasks/{id}/attachments` and `GET /attachments/{id}` return descriptors
  containing at least `id`, `filename`, `size`, `processing_status` (Section 19
  WP-1.11; FR-ATT-03/07).
- [ ] `token count` and `short description` fields exist and are null before the
  pipeline runs (FR-ATT-03 field shape fixed now, filled by WP-1.12).
- [ ] Listing is cursor-paginated per WP-0.5 conventions with stable ordering.
- [ ] Cross-project access returns `AUTH_FORBIDDEN_PROJECT` (Section 12.1).
- [ ] OpenAPI updated with schema diff reviewed (Section 20.4 item 4); error codes
  from the catalog only (item 5); changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_descriptor_listing.py -v` — descriptor shape,
pagination cursors, null-before-ready fields, and cross-project rejection.

## Attachments
* [Section 9.2 — REST API surface (attachments endpoints)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-ATT-03 / FR-ATT-07 — Descriptor and status requirements](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.11 deliverables](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Descriptor shape is consumed by task payloads (FR-ATT-03), the web modal and the
  mobile views — changing it later ripples across WPs; lock the field names in the
  OpenAPI schema diff at this task.
* Agents are listed as read callers in Section 9.2 but the bridge's
  `read_task_attachment` tool lands in WP-2.x — keep the permission test aligned with
  the Section 12.2 matrix (agent: read own project) so nothing is opened early.
