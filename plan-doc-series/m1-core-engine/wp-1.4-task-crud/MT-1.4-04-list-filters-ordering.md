# MT-1.4-04 — Implement List Filters and Priority/FIFO Ordering

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.4-04 |
| Title | Implement list filters and priority/FIFO ordering |
| Parent WP | WP-1.4 — Task model, id sequencing and CRUD (Milestone M1) |
| Requirements | FR-TSK-05; NFR-09 (list performance scale) |
| Priority | M |
| Dependencies | MT-1.4-03 (list endpoint exists), MT-1.4-01 (model fields), MT-0.5-04 (cursor pagination conventions) |
| Parent sections | 9.2 (Tasks list row), 7.2, 9.3 (ordering precedent), 19.1 (WP-1.4), 20.4, 20.5 |

## Context
FR-TSK-05 fixes ordering: `urgent > high > medium > low`, FIFO tie-break by creation
time. Section 9.3 shows the same ordering discipline for "next available" selection
("ordering by priority then creation time") — the list endpoint must agree with it so
the board, the API and later claim selection present one consistent ordering. The
`GET /projects/{pid}/tasks` endpoint (Section 9.2) also needs filters so the web board
(FR-WEB-01) and later the agent work view can slice the list; pagination follows the
MT-0.5-04 cursor conventions for all list endpoints.

## Inputs / Prerequisites
* MT-1.4-03 — the `GET /projects/{pid}/tasks` endpoint this task extends.
* MT-1.4-01 — model fields: `priority`, `state`, `created_at`, `archived_at`.
* Parent plan FR-TSK-05 — ordering rule, verbatim.
* Parent plan Section 9.2 — cursor-based pagination for all list responses; caller
  Owner.
* MT-0.5-04 — the canonical pagination shape (cursor, page size limits).
* Parent plan Section 7.2 — task fields available for filtering; `archived_at`
  default-visibility expectation foreshadowed by T19 ("hidden from boards by default")
  — full archive behavior is MT-1.4-06; coordinate the default filter here.

## Scope (in)
* Extend `GET /projects/{pid}/tasks` with cursor pagination per MT-0.5-04 and filters
  derivable from Section 7.2 fields: by `state` (single or multiple canonical values),
  by `priority`, and by the project path parameter (already implied).
* Apply canonical ordering: `priority` descending in the order
  `urgent > high > medium > low`, then `created_at` ascending (FIFO) as tie-break
  (FR-TSK-05) — implemented in the queryset, not in Python, so it scales (NFR-09:
  10,000 tasks).
* Exclude archived tasks from the default view (`archived_at` null) with an explicit
  filter to include them, matching T19's "hidden from boards by default" — confirm the
  include-flag name in the changelog (MT-1.4-06 owns the behavior; this task owns the
  list default).
* Filters must not weaken permissions: results are always scoped to the
  path-project's token/Owner context (Section 12.2).
* Tests: ordering across priorities with same-timestamp tie-break; each filter;
  pagination stability (cursor resumes without duplicates/skips per MT-0.5-04).
* Document query parameters in the OpenAPI snapshot (Section 20.4 item 4).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* The agent "available work" endpoint with role filters and dependency gating —
  WP-1.6 (`GET /projects/{pid}/work`).
* Filter UI — WP-4.x.
* Sort options other than the canonical FR-TSK-05 order — not in the plan; do not add
  arbitrary `ordering=` parameters (Section 20.1 item 5).
* Dependency-based filtering — MT-1.4-05 relation first.

## Target paths
* `backend/apps/tasks/` — list view filters/ordering/cursor wiring
* `backend/tests/` — ordering, filter and pagination tests
* `schemas/` — OpenAPI snapshot updated (query parameters)
* WP changelog entry

## Acceptance criteria
- [ ] Default list order is `urgent > high > medium > low`, then oldest `created_at`
  first (FR-TSK-05) — verified by a test with mixed priorities and identical
  timestamps.
- [ ] State and priority filters return exactly the matching sets; archived tasks are
  excluded by default (Section 8.2 T19 default visibility; MT-1.4-06 coordinates).
- [ ] Pagination follows MT-0.5-04 cursor conventions for this list endpoint
  (Section 9.2).
- [ ] Ordering/filtering happens in the database query; a plan/explain check or
  indexing test supports NFR-09 scale intent (10,000 tasks).
- [ ] Result set never crosses project boundaries (path-project scope;
  Section 12.2).
- [ ] OpenAPI snapshot updated (item 4); tests/lint green (item 2); error codes from
  the catalog (item 5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests/test_task_list.py` covering: mixed-priority list order,
FIFO tie-break on equal `created_at`, each filter combination, archived default
exclusion, cursor pagination resumption, and cross-project isolation (requesting
another project's pid yields no rows / catalog auth error per MT-1.2-05).

## Attachments
* [Section 9.2 — REST API surface (Tasks list)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.3 — "Next available" ordering precedent](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.4](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Priority is stored as an enum; ordering by enum must follow the FR-TSK-05 sequence
  explicitly (alphabetical ordering of `urgent/high/medium/low` is wrong) — test the
  exact sequence.
* `created_at` FIFO can tie at sub-second precision — the test must define tie-break
  behavior (add id as final stable tie-break) and document it; the plan says FIFO "by
  creation time" without a last-resort key.
