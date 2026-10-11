# MT-3.7-01 — Implement the merge queue API (pending / start / result)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.7-01 |
| Title | Implement the merge queue API (pending / start / result) |
| Parent WP | WP-3.7 — Merge queue and Merge Executor (Milestone M3) |
| Requirements | FR-AUD-06 |
| Priority | M |
| Dependencies | WP-3.6 complete (approve sets `merge_status` pending, T15); WP-1.4 / WP-1.6 complete (task model and transition machinery for T17/T18) |
| Parent sections | 9.2 (Merge queue row), 8.1, 8.2 (T13, T15, T17, T18), 7.2 (`merge_status`), 12.2 (authorization matrix), 9.6 (events), 19 (WP-3.7), 20.4, 20.5; ADR-008, ADR-012 |

## Context
Section 9.2 gives the Merge Executor exactly three endpoints: `GET /merge/pending`,
`POST /merge/{task}/start`, `POST /merge/{task}/result`. ADR-008 fixes the invariant
that `completed` is reached only after a successful merge performed host-side; the
backend's job here is purely to run the queue protocol and apply the state machine.
`start` moves a merge-pending task to `merging`; `result` applies T17 (merge succeeded →
`completed`, `merge_status` merged) or T18 (merge conflict/failure → back to
`in_human_review` with `review_reason` = `merge_conflict`). Section 19 WP-3.7 lists the
queue API as the first slice.

## Inputs / Prerequisites
* Parent plan Section 9.2 — the three merge-queue endpoints and their caller (Merge
  Executor), inside the standard envelope with idempotency-key headers.
* Parent plan Section 8.2 — T13/T15 produce merge-pending (`merge_status` = `pending`);
  T17 and T18 are the only exits; illegal transitions return `TASK_STATE_CONFLICT`.
* Parent plan Section 7.2 — `merge_status` values `none` / `pending` / `merging` /
  `merged` / `conflict` / `failed`.
* Parent plan Section 12.2 — authorization matrix: Merge Executor = "Merge queue: Yes";
  Owner read-only; agents no.
* Parent plan Section 9.6 — event catalog entries `merge.started|succeeded|failed`,
  emitted after commit.
* WP-3.6 — approval (`POST /tasks/{id}/review`, T15) is what enqueues work here.

## Scope (in)
* Backend implementation of the three Section 9.2 endpoints with OpenAPI schema
  updates (Section 20.4 item 4).
* `GET /merge/pending` — list tasks with `merge_status` = `pending` for the queue
  (Owner read-only, Merge Executor full access per Section 12.2).
* `POST /merge/{task}/start` — guarded transition of a pending task to `merging`,
  rejecting wrong states with `TASK_STATE_CONFLICT`, honoring idempotency keys
  (ADR-012), and emitting `merge.started` after commit (Section 9.6).
* `POST /merge/{task}/result` — success branch: apply T17 (`merge_status` → `merged`,
  task `completed`, emit `task.completed` and `merge.succeeded`); failure branch: apply
  T18 (`merge_status` → `conflict`/`failed`, `review_reason` = `merge_conflict`, emit
  `merge.failed` and trigger the merge-failure push of Section 9.8).
* Authorization enforcement with canonical error codes only (`AUTH_REQUIRED`,
  `AUTH_FORBIDDEN_PROJECT`, `TASK_STATE_CONFLICT` — Section 9.2 catalog).
* API tests covering both result branches, idempotent replay, and authorization.
* A WP changelog note.

## Out of scope
* Executor polling, worktree and Git operations — MT-3.7-02 to MT-3.7-04 (bridge side).
* Conflict escalation UX — MT-3.7-05 and web WP-4.8.
* Crash recovery semantics — MT-3.7-06.
* The approval endpoint that creates merge-pending — WP-3.6.

## Target paths
* `backend/` (merge queue endpoints, serializers/schemas, transition application)
* `backend/` tests (merge queue API tests)
* OpenAPI schema output (updated via the generated document)
* WP changelog entry

## Acceptance criteria
- [ ] All three endpoints from Section 9.2 exist with the Merge Executor as caller and
  are documented in the generated OpenAPI document (Sections 9.2, 20.4 item 4).
- [ ] `start` sets `merge_status` = `merging`; `result` success applies T17 exactly once
  (`completed` only when the merge result is reported — ADR-008; Section 8.2).
- [ ] `result` failure applies T18: back to `in_human_review`, `merge_status`
  conflict/failed, `review_reason` = `merge_conflict` (Section 8.2, Section 8.4
  canonical enum).
- [ ] `merge.started`, `merge.succeeded`, `merge.failed` are emitted after commit, from
  the Section 9.6 catalog only (Sections 20.4 item 6, 20.5).
- [ ] Illegal states return `TASK_STATE_CONFLICT`; replayed mutations with the same
  idempotency key do not double-apply (Sections 9.2, 8.2, ADR-012).
- [ ] Only catalog error codes used (Section 20.4 item 5).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k merge_queue -q` and confirm: pending listing, start →
`merging`, success result → T17 completed with `merge.succeeded`, failure result → T18
`in_human_review`/`merge_conflict` with `merge.failed`, idempotent replay, and
non-Executor callers rejected; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 9.2 — REST API surface (merge queue row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.2 — Transition table (T17, T18)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-008 — Host-side Merge Executor](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Section 7.2 has no dedicated field for the merge result sha ("report the resulting
  sha", Section 11.4) — carry it in the result payload, the transition note and the
  event payload; if a task-level field is wanted, raise it as a schema change first
  (Section 20.4 item 4), do not silently add columns.
* `merge_status` has no timeout sweeper in Section 9.9 — a task stuck in `merging`
  after an executor crash is reconciled only by MT-3.7-06 restart recovery; flag if
  operational experience shows a sweeper is needed.
* Section 12.2 grants the Owner read access to the merge queue but no write — do not
  add Owner-side bypass endpoints here.
