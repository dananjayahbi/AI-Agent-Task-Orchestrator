# MT-3.6-01 — Implement the review decision endpoint (approve / request_changes / reassign)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.6-01 |
| Title | Implement the review decision endpoint (approve / request_changes / reassign) |
| Parent WP | WP-3.6 — Human review decisions API (Milestone M3) |
| Requirements | FR-AUD-05 |
| Priority | M |
| Dependencies | WP-3.4 (plan: WP-3.6 depends on WP-3.4), WP-1.5 (state machine), WP-1.9 (event log), MT-3.6-02 (Review Decision model) |
| Parent sections | 9.2, 8.2 (T15, T16), 11.5, 12.2, 19 (WP-3.6), 20.4, 20.5 |

## Context
Section 9.2's Review row: `POST /tasks/{id}/review` (approve, request_changes,
reassign), caller Owner. Section 8.2 defines the transitions: **T15**
`in_human_review` → merge-pending, trigger Approve, actor O, guard "Resolution
exists", side effects `merge_status` = `pending` and record Review Decision;
**T16** `in_human_review` → `pending`, trigger Request changes / reassign, actor O,
guard "Note required for request changes", side effects `latest_feedback` set,
`attempt_number` preserved, clear worker. Section 11.5: all decisions are recorded.
FR-AUD-05 covers approve-and-merge, request changes (text note), reassign. Illegal
transitions return `TASK_STATE_CONFLICT` (HTTP 409); every transition runs in one
transaction that also writes the Transition and Event rows; the UI sends the `version`
it saw and a stale version returns a conflict.

## Inputs / Prerequisites
* Parent plan Sections 9.2, 8.2 (T15/T16), 11.5 — endpoint, guards, side effects.
* Parent plan Section 12.2 — authorization matrix: "Review decisions" — Owner: Yes,
  Device: Yes; agents/decomposers/executor: No.
* Parent plan Section 9.6 — `review.decided` in the event catalog (Section 20.4
  item 6 obligation).
* WP-1.5 — state machine implementation the transitions flow through.
* WP-1.9 — event log written in the same transaction.
* MT-3.6-02 — Review Decision record written by T15/T16.

## Scope (in)
* `POST /tasks/{id}/review` accepting `decision` ∈ {`approve`, `request_changes`,
  `reassign`} with `note` (mandatory for `request_changes`), `resolution_id`
  binding (consumed by MT-3.6-04), and the caller's `version`, keyed by an
  idempotency key (Section 9.2).
* T15 handling: guard — resolution exists; side effects — `merge_status` = `pending`,
  Review Decision recorded (MT-3.6-02).
* T16 handling: `request_changes` requires a note (missing note → `VALIDATION_ERROR`
  with hint); sets `latest_feedback`, preserves `attempt_number`, clears worker,
  moves to `pending`; `reassign` returns to `pending` and clears worker (Section
  11.5).
* Authorization per Section 12.2 (Owner sessions; device-bound mobile sessions
  allowed) — everyone else `AUTH_FORBIDDEN_PROJECT`/`ROLE_NOT_PERMITTED` per the
  catalog.
* One transaction per transition, writing Transition + Event rows (Section 8.2
  rules); `review.decided` event emitted (Section 9.6); post-commit publication per
  Section 9.6.
* Stale `version` → conflict; illegal decision from current state (e.g. approve a
  non-`in_human_review` task) → `TASK_STATE_CONFLICT` (Section 8.2).
* Backend tests: three decisions end-to-end; note-missing rejection; wrong-role
  rejection; stale-version conflict; event and Transition rows written.

## Out of scope
* The Review Decision model definition — MT-3.6-02.
* `latest_feedback` surfacing in `get_task_details` — MT-3.6-03.
* Stale-resolution protection logic — MT-3.6-04.
* Merge queue/executor behavior after approval — WP-3.7.
* Web/mobile UIs calling the endpoint — WP-4.4/WP-5.8.

## Target paths
* `backend/` — review endpoint, transition handlers (T15/T16)
* `backend/tests/` — endpoint tests
* OpenAPI document (endpoint added; schema diff reviewed)
* WP changelog entry

## Acceptance criteria
- [ ] `POST /tasks/{id}/review` implements approve, request_changes and reassign with
  the Section 8.2 T15/T16 guards and side effects exactly (FR-AUD-05).
- [ ] `request_changes` without a note is rejected (`VALIDATION_ERROR` with hint);
  approve without an existing resolution is rejected (T15 guard).
- [ ] Decisions are restricted to Owner and Device callers per the Section 12.2
  matrix; other callers are rejected with catalog codes.
- [ ] Each transition writes Transition + Event rows in one transaction and emits
  `review.decided` (Sections 8.2, 9.6; Section 20.4 item 6).
- [ ] Stale `version` returns a conflict; illegal-state decisions return
  `TASK_STATE_CONFLICT` (Section 8.2).
- [ ] OpenAPI updated with schema diff reviewed (Section 20.4 item 4); only catalog
  codes used (item 5); lint/type/tests green (item 2); changelog note added (item 7).

## Test command
`pytest backend/tests -k review_endpoint -q` — assert T15 (approve → merge pending +
decision recorded), T16 (request changes with note → `pending` + feedback;
reassign → `pending`), note/authorization/stale-version/illegal-state rejections, and
the `review.decided` event row; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 8.2 — Transition table (T15, T16)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Authorization matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* T15 hands off to the merge queue (`merge_status` = `pending`) — if WP-3.7 is not
  built yet, approval must still record the decision and set the sub-status without
  pretending completion (Section 8.1: "merge pending" is a sub-status, never a
  seventh state).
* Endpoint logic and model creation are deliberately split (20.3: never combine
  unrelated changes) — landing both in one migration-bundled change defeats the
  split; MT-3.6-02 owns the schema.
* Decision semantics must not be inferred from UI intent: only the three Section 9.2
  values are valid; extra values rejected with `VALIDATION_ERROR`.
