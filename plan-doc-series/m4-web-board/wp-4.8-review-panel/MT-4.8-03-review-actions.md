# MT-4.8-03 — Implement approve / request-changes / reassign actions with confirmation

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.8-03 |
| Title | Implement approve / request-changes / reassign actions with confirmation |
| Parent WP | WP-4.8 — Human review panel and queue (Milestone M4) |
| Requirements | FR-WEB-06 |
| Priority | M |
| Dependencies | MT-4.8-02 (panel actions region); WP-3.6 complete (`POST /tasks/{id}/review`, stale-resolution protection); MT-4.6-03 (resolution context) |
| Parent sections | 11.5 (three actions), 8.2 (T15, T16), 13.2 (drag-drop rules for confirmations), 9.2 (review endpoint), 7.2 (Review Decision), 19 (WP-4.8), 20.4, 20.5 |

## Context
Section 11.5 fixes the three actions: "approve and merge; request changes with a note
(which becomes `latest_feedback`, returns to `pending`); reassign (returns to
`pending`, clears worker). All decisions are recorded." The transition table makes
them precise: T15 approve → merge-pending with `merge_status` = `pending` and a Review
Decision recorded (guard: resolution exists); T16 request changes/reassign → `pending`
with `latest_feedback` set (note required for request changes), `attempt_number`
preserved, worker cleared. Section 13.2 requires confirmations: entering
`completed` via approval opens an approve-and-merge confirmation, and moving to
`pending` opens the request-changes/reassign dialog. The endpoint is
`POST /tasks/{id}/review` (Section 9.2, Owner caller), with WP-3.6's
stale-resolution protection rejecting approvals that reference an outdated resolution.

## Inputs / Prerequisites
* Parent plan Sections 11.5 and 8.2 (T15, T16) — exact action semantics and guards.
* Parent plan Section 13.2 — confirmation requirements for the two dialog flows.
* Parent plan Section 9.2 — `POST /tasks/{id}/review` with `approve`,
  `request_changes`, `reassign` payloads.
* Parent plan Section 7.2 — Review Decision (`decision`, `note`, `decided_via`
  `web`), `version` optimistic locking (Section 8.2 rule 3).
* WP-3.6 — implementation of the endpoint, `latest_feedback` propagation, stale
  approval rejection.
* MT-4.8-02 — the actions region these controls live in.

## Scope (in)
* The three action controls in the panel, enabled per T15/T16 guards (a resolution
  must exist for approve).
* **Approve:** opens the approve-and-merge confirmation (Section 13.2) showing task
  id, branch and diff stats context before submitting `approve` with the resolution
  `version` the panel is viewing; on success the queue/panel transitions toward the
  merge-pending state (MT-4.8-04 shows it live).
* **Request changes:** opens the dialog requiring a note (Section 8.2 T16 guard:
  "Note required for request changes"); submits `request_changes`; the note becomes
  `latest_feedback` (Section 11.5).
* **Reassign:** opens its dialog (Section 13.2 groups it with request changes);
  submits `reassign`, clearing the worker and returning the task to `pending`
  (Section 11.5).
* Conflict handling: `VERSION_CONFLICT` / `TASK_STATE_CONFLICT` refreshes the panel
  with a clear message and no blind retry (Sections 8.2 rule 3, 13.3 error mapping);
  WP-3.6's stale-resolution rejection surfaces as its own message (Section 19 WP-3.6
  acceptance).
* Decisions recorded server-side — the UI shows `decided_via` web history from the
  transition/decision records (Sections 7.2, 11.5, 12.5).
* Component tests: confirmation flows, required-note validation, payload contents,
  stale/conflict error paths, disabled approve without resolution.
* A WP changelog note.

## Out of scope
* Backend review endpoint and stale-resolution logic — WP-3.6.
* Merge execution and status polling — MT-4.8-04 / WP-3.7.
* Notification/push on decision — Section 9.8 workers (out of client scope).
* Mobile actions — WP-5.8 (MT-5.8-04…06, `decided_via` mobile).
* Drag-and-drop board moves — WP-4.4 (the panel's dialogs here are the canonical
  action path; Section 13.2's drag rules mirror them).

## Target paths
* `web/` (action controls and confirmation dialogs in the review panel)
* `web/` tests (action and dialog tests)
* WP changelog entry

## Acceptance criteria
- [ ] All three Section 11.5 actions exist with confirmation dialogs per
  Section 13.2 (approve-and-merge confirmation; request-changes/reassign dialog).
- [ ] Request changes cannot submit without a note; the note is sent as the feedback
  that becomes `latest_feedback` (Sections 8.2 T16, 11.5).
- [ ] Approve sends the resolution context the panel viewed so WP-3.6's stale
  protection can reject outdated approvals — the rejection is surfaced, not swallowed
  (Section 19 WP-3.6 acceptance).
- [ ] Success responses drive the correct transitions: approve → merge-pending
  (T15), request changes/reassign → `pending` with worker cleared (T16) — canonical
  states only (Sections 8.2, 20.5).
- [ ] `VERSION_CONFLICT`/`TASK_STATE_CONFLICT` produce a refresh + explanation, no
  blind retry (Sections 8.2 rule 3, 13.3; catalog codes only, 20.4 item 5).
- [ ] Decisions are recorded with `decided_via` `web` server-side (Section 7.2) —
  asserted through the API response/history.
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to review actions (for example `npm test -- -t
"approve"`) and confirm: confirmation dialog payloads, required-note validation,
stale-approval and version-conflict error paths, disabled-approve guard, and
post-action state transitions; then the full web suite stays green.

## Attachments
* [Section 8.2 — Transition table (T15, T16)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 11.5 — Human review workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.6 acceptance (stale approvals)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Approve triggers the merge queue (T15 sets `merge_status` pending) — the UI must
  not claim "completed" optimistically; only MT-4.8-04's executor-driven state ends
  in completion (ADR-008: completed only after successful merge).
* Double-click/double-submit on approve must be guarded (idempotency expectation of
  P6/ADR-012 on the wire; disable-while-pending in the UI).
* Reassign semantics for choosing the new worker are unspecified — Section 11.5 says
  it "clears worker" (returns to `pending` for any agent to claim); do not invent an
  assignee picker unless the plan/endpoint gains one.
