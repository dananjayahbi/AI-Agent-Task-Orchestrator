# MT-1.8-04 — Implement Checkpoint Listing with Pagination

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.8-04 |
| Title | Implement checkpoint listing with pagination |
| Parent WP | WP-1.8 — Checkpoints and token usage (Milestone M1) |
| Requirements | FR-LEA-03, FR-WEB-04, FR-MOB-03, NFR-11 |
| Priority | S |
| Dependencies | MT-1.8-01 (model + index); MT-1.8-03 (endpoint conventions) |
| Parent sections | 9.2 (Progress endpoints), 13.2 (checkpoint feed), 14.1, 19 (WP-1.8), 20.4, 20.5 |

## Context
Section 9.2 pairs the write endpoint with `GET /tasks/{id}/checkpoints` (Agent /
Owner callers), and WP-1.8's deliverables close with "history listing with
pagination". Consumers: the web task-detail checkpoint feed (FR-WEB-04,
reverse-chronological live list with percent, message and token usage —
Section 13.2), the mobile task detail stream (FR-MOB-03, Section 14.1), and the
bridge for context reads. Pagination must follow the plan-wide cursor convention
(WP-0.5-04) so every list endpoint in the API behaves identically (NFR-11).

## Inputs / Prerequisites
* MT-1.8-01 — Task Checkpoint model with the listing index; MT-1.8-03 — endpoint
  conventions (auth, envelope, OpenAPI update flow).
* WP-0.5-04 — cursor-based pagination conventions for all list endpoints (mandatory
  for this endpoint).
* Parent plan Section 9.2 — endpoint row and caller set (Agent / Owner);
  Section 13.2 — feed ordering/content expectations.
* Section 12.2 — authorization matrix: owner sees own project; agent token sees own
  project only (`AUTH_FORBIDDEN_PROJECT` otherwise).

## Scope (in)
* Implement `GET /tasks/{id}/checkpoints`: paginated, reverse-chronological
  (newest-first) checkpoint history for a task, returning the Section 7.2 fields
  (`timestamp`, `message`, `percent`, `token_usage`, `kind`, `attempt_number`,
  `session_id`).
* Cursor pagination per WP-0.5-04 (cursor parameter, next-cursor in the response,
  stable ordering keyed on server `timestamp`/id so inserts during paging never
  shift or duplicate rows).
* Authorization: Owner session and project-scoped Agent token per Section 9.2/12.2;
  cross-project tokens get `AUTH_FORBIDDEN_PROJECT`; unknown task
  `TASK_NOT_FOUND` — catalog codes only.
* OpenAPI updated; schema diff reviewed (NFR-11, Section 20.4 item 4).
* API tests: first page shape and order, cursor continuation reaches every row
  exactly once even with concurrent inserts, default/maximum page size per the
  WP-0.5-04 conventions, authorization matrix, empty-task response.
* Add a WP changelog note.

## Out of scope
* SSE live streaming of new checkpoints — WP-1.10 (`task.checkpoint` events);
  this endpoint serves history/backfill and initial load.
* Web feed component and mobile stream UI — WP-4.6 / WP-5.7 (consumers).
* Aggregations (token totals, per-attempt summaries) — not in Section 9.2; needs an
  OQ before inventing.
* Filtering by `kind` or `attempt_number` — not specified in the plan; only add via
  an OQ.
* Retention/pruning (OQ-10) — WP-6.x.

## Target paths
* `backend/apps/tasks/` (checkpoint listing view/serializer)
* `schemas/openapi` generated snapshot (contract update)
* `backend/tests/` (listing and pagination tests)
* WP changelog entry

## Acceptance criteria
- [ ] `GET /tasks/{id}/checkpoints` exists per Section 9.2 with Agent/Owner callers
  and appears in the generated OpenAPI document (Section 20.4 item 4).
- [ ] Pagination follows WP-0.5-04 cursor conventions exactly; paging an active task
  yields every checkpoint exactly once with no gaps or duplicates.
- [ ] Rows are newest-first with the Section 7.2 fields needed by the Section 13.2
  feed (percent, message, token usage).
- [ ] Authorization matches Section 12.2; errors are catalog codes in the Section
  9.2 envelope (Section 20.4 item 5).
- [ ] Empty task returns an empty page, not an error.
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k checkpoint_listing -q` and confirm ordering, cursor
continuation under concurrent inserts, page-size conventions, and the authorization
matrix; regenerate/validate the OpenAPI snapshot; full suite stays green.

## Attachments
* [Section 9.2 — REST API surface (Progress)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.2 — Web task detail (checkpoint feed)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Reverse-chronological cursors over an append-heavy table need the MT-1.8-01 index
  to sort on — verify the query plan with the Section 18 performance dataset
  (10,000 tasks) later in WP-1.15; flag index gaps there rather than adding
  ad-hoc offsets (cursor conventions forbid offset paging).
* Agent callers listing checkpoints is specified in Section 9.2 but agents "never
  subscribe" to streams (Section 9.6) — keep listing and streaming authorization
  distinct; any confusion becomes an OQ with WP-1.10.
