# MT-5.8-06 — Implement the reassign action

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.8-06 |
| Title | Implement the reassign action |
| Parent WP | WP-5.8 — Review action sheet (Milestone M5) |
| Requirements | FR-MOB-05 |
| Priority | M |
| Dependencies | MT-5.8-01 (sheet action bar); WP-3.6 complete (`POST /tasks/{id}/review` reassign) |
| Parent sections | 14.1 (three actions), 11.5 (reassign semantics), 8.2 (T16), 7.2 (Review Decision), 19 (WP-5.8 acceptance), 20.3, 20.4, 20.5 |

## Context
Section 11.5: "reassign (returns to `pending`, clears worker). All decisions are
recorded." T16 (Section 8.2) covers it alongside request changes — from
`in_human_review` to `pending` with `latest_feedback` set (a note may accompany),
`attempt_number` preserved, worker cleared — but only request changes *requires* a
note (T16 guard: "Note required for request changes"). FR-MOB-05 lists reassign as
the third review action; Section 14.1 shows three actions on the sheet; Section 19
WP-5.8 acceptance: reassign works end to end against the real backend. The decision
is recorded with `decided_via` `mobile` (Section 7.2), and "all decisions are
recorded" (Section 11.5; Section 12.5 writes an Event row).

## Inputs / Prerequisites
* Parent plan Sections 11.5 and 8.2 T16 — exact semantics (note optional; worker
  cleared; returns to `pending`).
* Parent plan Section 9.2 — `POST /tasks/{id}/review` `reassign` payload.
* Parent plan Section 7.2 — Review Decision fields; Task `attempt_number`,
  `worker_agent_id`/`worker_session_id` cleared on return to `pending`.
* WP-3.6 — endpoint implementation and decision recording.
* MT-5.8-01 — the action bar this control lives in.

## Scope (in)
* The reassign control in the sheet's action bar opening a confirmation dialog:
  explains the outcome in plain language — the task returns to `pending` and the
  current worker is cleared so any eligible agent may claim it (Section 11.5) —
  with an **optional** note field (it becomes `latest_feedback when provided,
  consistent with T16).
* Submit via the generated client with disable-while-pending; success shows the T16
  outcome on the sheet/task state (back to `pending`, worker cleared, decision
  recorded `decided_via` `mobile`), then navigates/refreshes to reflect the queue
  change (Section 8.2; Section 20.5 canonical values).
* Offline disabled with the Section 14.2 clear offline state — no queued reassigns;
  conflict errors (`TASK_STATE_CONFLICT`/`VERSION_CONFLICT`) refresh with friendly
  messages from catalog codes (Section 20.4 item 5).
* No assignee picker: reassign clears the worker for re-claim (Sections 11.5, 8.2) —
  the plan defines no target-agent selection.
* Widget/integration tests: confirmation copy, optional note payload, payload shape,
  success state/transition display, offline disabled, conflict path, no assignee
  input present — mocked backend per Section 14.3.
* A WP changelog note.

## Out of scope
* Server-side endpoint and decision recording — WP-3.6.
* Approve and request-changes flows — MT-5.8-04/05.
* Web reassign dialog — WP-4.8 (MT-4.8-03).
* Claiming the reassigned task — coder flow (bridge, Section 11.1), not mobile.
* Push notification of the reopened task — Section 9.8 worker.

## Target paths
* `mobile/` (reassign confirmation flow in the review sheet)
* `mobile/` tests (widget and integration tests)
* WP changelog entry

## Acceptance criteria
- [ ] Reassign opens a confirmation stating the task returns to `pending` and the
  worker is cleared (Sections 11.5, 8.2 T16), with an optional note — no required
  field (only request changes requires a note, Section 8.2).
- [ ] Success displays/refreshes to the T16 outcome: `pending` state, worker cleared,
  `attempt_number` preserved server-side (Sections 8.2, 7.2) — canonical values only
  (Section 20.5).
- [ ] The decision is recorded with `decided_via` `mobile` (Section 7.2;
  Section 11.5 "All decisions are recorded").
- [ ] No assignee picker exists — reassign means free re-claim (Sections 11.5, 8.2);
  nothing invented (Section 20.5).
- [ ] Offline disabled with the Section 14.2 clear offline state; conflict errors
  map from catalog codes (Section 20.4 item 5).
- [ ] End-to-end against the real backend: reassign returns the task to `pending`
  with worker cleared (Section 19 WP-5.8 acceptance).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the mobile suite filtered to reassign (for example
`flutter test --dart-define=test_filter=reassign` or the project's equivalent) for
confirmation copy, optional-note payload, success state, offline and conflict paths;
then the WP end-to-end check against the real backend confirms the T16 outcome
(Section 19 WP-5.8 acceptance); the full mobile suite stays green.

## Attachments
* [Section 11.5 — Human review workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.2 — Transition table (T16)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.8 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Reassign and request changes share T16 — the two mobile dialogs must not send
  ambiguous payloads; distinguish them explicitly in the client contract and cover
  both in tests to avoid one flow regressing the other.
* The reassigned task re-enters `pending` where any coder may claim it immediately
  (Section 8.2 T4 guards still apply) — the sheet should not imply a specific next
  worker in its copy (no invented targeting semantics).
* Confirmation-versus-direct action: Section 14.2 mandates confirmation only for
  approve; a reassign confirmation is a UX safeguard consistent with the web dialog
  (Section 13.2) — record this parity choice in the changelog rather than treating
  it as plan text.
