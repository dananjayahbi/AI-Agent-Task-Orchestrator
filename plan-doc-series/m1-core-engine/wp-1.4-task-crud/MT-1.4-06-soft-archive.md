# MT-1.4-06 — Implement Soft Archive and Read-Only Completed State

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.4-06 |
| Title | Implement soft archive and read-only completed state |
| Parent WP | WP-1.4 — Task model, id sequencing and CRUD (Milestone M1) |
| Requirements | FR-TSK-08; ADR-008 (completed semantics) |
| Priority | S |
| Dependencies | MT-1.4-01 (`archived_at`, `state` fields), MT-1.4-03 (update path), MT-1.4-04 (default list exclusion), MT-1.4-05 (dependency interaction) |
| Parent sections | 7.2 (`archived_at`), 7.3 (no deletion), 8.2 (T17 read-only, T19 archive), 9.2, 19.1 (WP-1.4), 20.4, 20.5 |

## Context
FR-TSK-08 (priority S): "Soft archive of tasks and a read-only `completed` state."
Section 7.3: "Deleting a task is not supported; archiving preserves id continuity."
Section 8.2 T19: archive is Owner-only, sets `archived_at`, tasks are "hidden from
boards by default"; T17 side effect: task becomes read-only on completion
(completed = merged, ADR-008). WP-1.4's deliverable list includes archive. This task
implements the model-behavior half — the archive *transition endpoint* (T19) is
WP-1.5's owner-transitions slice (MT-1.5-02), so this task defines what `archived_at`
and read-only mean for reads/updates and hands T19 a settled field to set.

## Inputs / Prerequisites
* MT-1.4-01 — `archived_at` (nullable timestamp) and `state`/`merge_status` fields.
* MT-1.4-03 — PATCH endpoint whose write rules this task extends.
* MT-1.4-04 — list default excluding archived tasks (already implemented; verify
  coordination).
* Parent plan Section 7.3 — no deletion; archive preserves id continuity.
* Parent plan Section 8.2 — T17 (completed → read-only) and T19 (archive: any
  non-completed, sets `archived_at`, hidden by default).
* Parent plan Section 9.2 — no `DELETE /tasks/{id}` exists in the surface (deletion
  unsupported).
* ADR-008 — `completed` only after successful merge (the state machine enforces
  *entering* completed; this task enforces *remaining* read-only once there).

## Scope (in)
* Read-only `completed` enforcement at the API layer: `PATCH /tasks/{id}` on a task in
  `completed` state is rejected (catalog code — see Risk notes for code choice);
  read endpoints continue to serve it (read-only means reads allowed, writes refused).
* Archival behavior contract: archived tasks remain readable by id (id continuity,
  Section 7.3), are excluded from default lists (coordinate with MT-1.4-04's flag),
  and can never be deleted — no delete route exists or may be added (Section 7.3).
* Update-path rule for archived tasks: archived tasks reject edits — they are
  historical records; document the chosen catalog code consistently with the
  completed-state rejection (both are write-refusals on terminal/archived rows).
* Tests: PATCH on `completed` rejected; PATCH on archived rejected; GET by id still
  returns both; list default excludes archived; no delete route exists (route-table
  test).
* Wire notes for WP-1.5: T19's side effect ("Sets `archived_at`") targets this field
  — record the setter contract in the changelog/comments for MT-1.5-02.
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* The `POST /tasks/{id}/transition` archive endpoint (T19) and unpublish (T3) —
  WP-1.5 (owner transitions slice).
* Entering `completed` (T17) — merge WPs with `merge_status` handling (ADR-008).
* Restoring/unarchiving — not specified in the plan (T19 has no inverse); do not
  invent it; raise as an open point if the owner asks (Section 20.1 item 5).
* Retention/deletion of archived data — OQ-10 retention (M6).
* Board UI "hidden by default" rendering — WP-4.x consumes the list default.

## Target paths
* `backend/apps/tasks/` — update-path guard for completed/archived rows; archive
  helper for WP-1.5
* `backend/tests/` — read-only and archive behavior tests
* WP changelog entry

## Acceptance criteria
- [ ] `PATCH` on a `completed` task is refused; the task remains fully readable
  (FR-TSK-08 "read-only `completed` state").
- [ ] Archived tasks: excluded from default lists (Section 8.2 T19), readable by id,
  not deletable — no delete route exists (Section 7.3; FR-TSK-08 soft archive).
- [ ] `archived_at` is the single archive marker per Section 7.2; no rows are ever
  hard-deleted by application code (test asserts refusal paths).
- [ ] Refusals use only Section 9.2 catalog codes with the choice recorded in the
  changelog (Section 20.4 item 5).
- [ ] The archive setter is exposed for WP-1.5's T19 to call — contract documented
  (Section 8.2; Section 9.1 "tasks owns state changes").
- [ ] Tests, lint, type check green (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests/test_task_archive.py` covering: PATCH rejected on completed
and on archived tasks with the recorded catalog code; GET by id succeeds for both;
default list omits archived and the include-flag restores them; route scan confirms no
DELETE endpoint on tasks.

## Attachments
* [Section 8.2 — Transition table (T17, T19)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.3 — Identifier generation rules (no deletion)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.4](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The catalog has no `TASK_ARCHIVED`/`READ_ONLY` code — decide once between
  `TASK_STATE_CONFLICT` (fits "not allowed in this state") and `VALIDATION_ERROR`,
  apply it to both completed and archived refusals, and record the mapping; do not
  invent a 20th code (Section 20.4 item 5).
* Read-only-on-completed and state transitions overlap with WP-1.5's guard framework —
  keep this task's rule at the update endpoint (API write refusal) and let WP-1.5 own
  transition guards, noting the boundary in the changelog to avoid two competing
  implementations.
