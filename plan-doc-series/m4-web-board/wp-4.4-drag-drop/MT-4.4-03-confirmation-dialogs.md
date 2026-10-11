# MT-4.4-03 — Implement confirmation dialogs for approve-merge and request-changes moves

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.4-03 |
| Title | Implement confirmation dialogs for approve-merge and request-changes moves |
| Parent WP | WP-4.4 — Drag-and-drop with validation (Milestone M4) |
| Requirements | FR-WEB-02, FR-AUD-05 |
| Priority | M |
| Dependencies | MT-4.4-01 (map verdicts), MT-4.4-02 (dialog handoff), WP-3.6 (review endpoint), WP-4.1 (typed API client) |
| Parent sections | 13.2, 8.2 (T15, T16), 11.5, 19 (WP-4.4), 20.4, 20.5 |

## Context
Section 13.2: `in_human_review` → `completed` "opens an approve-and-merge
confirmation (not a plain move)"; `in_human_review` → `pending` "opens the
request-changes/reassign dialog". Mechanically these are not column moves at all —
they are review decisions: T15 (approve → merge pending, resolution must exist) and
T16 (request changes with required note / reassign → `pending`), served by
`POST /tasks/{id}/review` (Section 9.2) and recorded as Review Decisions
(Section 11.5: all decisions are recorded). Section 13.4 requires keyboard navigation
for dialogs.

## Inputs / Prerequisites
* MT-4.4-01/02 — `dialog` verdicts routing here.
* Parent plan Sections 13.2, 13.4 — dialog requirements and keyboard navigation.
* Parent plan Sections 8.2 (T15/T16 guards: resolution exists; note required),
  11.5 — decision semantics.
* WP-3.6 (MT-3.6-01) — `POST /tasks/{id}/review` accepting `approve`,
  `request_changes`, `reassign` with `note` and `resolution_id` binding.
* WP-4.1 — generated typed API client for the call.

## Scope (in)
* An approve-and-merge confirmation dialog shown for `in_human_review` → `completed`:
  makes explicit that approval sends the task to merge (Section 8.1: merge pending is
  a sub-status; the card returns to an "approved, merging" badge, never directly to a
  `completed` column), surfaces the task id and enough context to decide, and
  confirms via the review endpoint's `approve` decision with the viewed
  `resolution_id` (stale protection — MT-3.6-04).
* A request-changes/reassign dialog for `in_human_review` → `pending`: two actions —
  `request_changes` (note mandatory, validated client-side before submit; the note
  becomes `latest_feedback`, Section 11.5) and `reassign` (returns to `pending`,
  clears worker).
* Error handling through canonical codes: `TASK_STATE_CONFLICT`,
  `VERSION_CONFLICT`, `VALIDATION_ERROR` mapped to friendly messages with the
  dialog staying open on failure so the operator can retry or refresh
  (Section 13.3).
* Accessibility: dialog keyboard navigation, focus management and announced outcomes
  (Section 13.4).
* Component tests: confirm/cancel paths; note-required validation; reassign path;
  endpoint error keeps dialog open with mapped message; keyboard-only operation.

## Out of scope
* The map and DnD wiring — MT-4.4-01/02.
* Optimistic cache moves and rollback — MT-4.4-04 (on success the move settles via
  the SSE event patch, WP-4.3 MT-4.3-05).
* The backend endpoint, decision recording, stale protection — WP-3.6.
* The full review panel (rule table, diff, evidence) — WP-4.8; mobile approve
  safety dialog — WP-5.8.

## Target paths
* `web/` — approve-merge confirmation and request-changes/reassign dialogs
* `web/tests/` — dialog component tests
* WP changelog entry

## Acceptance criteria
- [ ] Dropping onto `completed` from `in_human_review` opens the approve-and-merge
  confirmation — never a plain move (Section 13.2 verbatim).
- [ ] Dropping onto `pending` from `in_human_review` opens the
  request-changes/reassign dialog (Section 13.2).
- [ ] Approval sends `approve` with the viewed `resolution_id` via
  `POST /tasks/{id}/review`; request changes enforces the mandatory note (T16 guard);
  reassign sends `reassign` (Sections 8.2, 9.2).
- [ ] Success shows the correct resulting state — merge pending ("approved, merging")
  for approve; `pending` for T16 actions (Section 8.1) — with the decision recorded
  server-side (Section 11.5).
- [ ] Endpoint failures keep the dialog open with canonical-code-mapped messages
  (Section 13.3); dialogs are fully keyboard-operable (Section 13.4).
- [ ] Only catalog error codes used (Section 20.4 item 5); lint/type/tests green
  (item 2); changelog note added (item 7).

## Test command
`npm test -- -t review-dialogs` — assert dialog routing for both verdicts, note
validation, `resolution_id` binding, error-stays-open mapping, and keyboard
operation; then the full web suite stays green.

## Attachments
* [Section 13.2 — Key components (drag-and-drop rules)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.2 — Transition table (T15, T16)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Presenting approve as "move to Completed" would lie about Section 8.1 — the card
  lands in merge-pending state with a badge; copy and post-dialog UI must reflect
  that.
* The note requirement exists server-side (T16) too; client validation is courtesy,
  never the gate — keep both.
* The dialog binds to the `resolution_id` shown; if the review panel (WP-4.8) later
  provides richer context, the binding must come from the same resolution the
  operator actually saw.
