# MT-4.8-04 — Implement live merge-status display (pending → merged)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.8-04 |
| Title | Implement live merge-status display (pending → merged) |
| Parent WP | WP-4.8 — Human review panel and queue (Milestone M4) |
| Requirements | FR-WEB-06 |
| Priority | M |
| Dependencies | MT-4.8-03 (approve action); WP-3.7 complete (queue + executor events); WP-4.3 complete (stream hook) |
| Parent sections | 8.1 (merge pending sub-status and badge note), 8.2 (T15, T17, T18), 7.2 (`merge_status`), 9.6 (`merge.started|succeeded|failed`), 19 (WP-4.8 acceptance), 20.4, 20.5; ADR-008 |

## Context
Section 8.1's diagram note is the design contract for this task: "'merge pending' is a
sub-status of the task (merge_status), not a seventh state. The card stays in
`to_be_audited` or `in_human_review`, with an 'approved, merging' badge, until the
Merge Executor reports success." The sub-status values are `none` / `pending` /
`merging` / `merged` / `conflict` / `failed` (Section 7.2), moved by T15 (approve →
pending), executor `start` (→ merging), T17 (→ merged, `completed`) and T18 (→
conflict/failed, back to `in_human_review`). Section 19 WP-4.8 acceptance: "approve
triggers merge pending state visible live; completed state follows executor report."

## Inputs / Prerequisites
* Parent plan Section 8.1 — the badge note and sub-status semantics.
* Parent plan Sections 8.2 and 7.2 — T15/T17/T18 and `merge_status` values.
* Parent plan Section 9.6 — `merge.started`, `merge.succeeded`, `merge.failed` events
  plus `task.transitioned` for T17/T18; WP-4.3 hook delivers them.
* WP-3.7 — the queue/executor that emits these (MT-3.7-01).
* MT-4.8-03 — approve action whose result seeds the pending display.

## Scope (in)
* Merge-status presentation in the review panel and on the affected queue row/board
  card: a status badge cycling `pending` (approved, waiting) → `merging` (executor
  working; Section 8.1 "approved, merging" wording) → `merged` (task `completed`), or
  → `conflict`/`failed` returning the task to review with reason `merge_conflict`.
* Live updates driven by SSE: `merge.started|succeeded|failed` events and
  `task.transitioned` (T17/T18) applied through WP-4.3 cache patching — no polling
  (Section 13.3), visible connection status when the stream drops (Section 13.3).
* Immediate optimistic seed after a successful approve response (T15 sets
  `merge_status` pending server-side), reconciled by subsequent events — never
  displaying `completed` before the executor's report (ADR-008, Section 8.1 note).
* Failure state UX: conflict/failed shows the `merge_conflict` reason and re-opens
  the path into the review panel (MT-4.8-02) for the returned task.
* Canonical values only: every displayed sub-status is a Section 7.2 value
  (Section 20.5).
* Component tests: badge sequence on fixture event order (pending → merging →
  merged), conflict branch, card position stays in `in_human_review`/`to_be_audited`
  while merging (Section 8.1), event-gap reconciliation after reconnect.
* A WP changelog note.

## Out of scope
* Queue API and executor emission — WP-3.7 (MT-3.7-01…05).
* Approval controls — MT-4.8-03.
* Mobile merge display — WP-5.8.
* Push notifications on merge failure — Section 9.8 worker (server-side).

## Target paths
* `web/` (merge-status badge/state in panel, queue row, board card)
* `web/` tests (merge-status state tests with fixture events)
* WP changelog entry

## Acceptance criteria
- [ ] After approve, the merge-pending state is visible live without refetch —
  Section 19 WP-4.8 acceptance ("approve triggers merge pending state visible live").
- [ ] The displayed transition follows `pending` → `merging` → `merged` driven by the
  Section 9.6 events, with completion only after the executor's success report
  (Section 8.1 badge note; ADR-008; Section 19 WP-4.8 acceptance).
- [ ] Conflict/failure shows `merge_status` conflict/failed and the `merge_conflict`
  reason, with the card back in `in_human_review` — canonical values only
  (Sections 8.2 T18, 8.4, 7.2, 20.5).
- [ ] While merging, the task's board/queue position remains its state (not a seventh
  state) with the "approved, merging" style badge (Section 8.1 note).
- [ ] Event loss/reconnect is reconciled through last-event-id resume without wrong
  final status (Sections 9.6, 13.3).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to merge status (for example `npm test -- -t
"merge status"`) and confirm the pending → merging → merged sequence, conflict
branch, in-place card badge, and reconnect reconciliation; then verify live behavior
against the running stack (approve a fixture task end to end, Section 18) and the
full web suite stays green.

## Attachments
* [Section 8.1 — State diagram (merge pending sub-status note)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.6 — Realtime gateway (merge events)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.8 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* A missed `merge.succeeded` event must not leave a stale `merging` badge forever —
  reconcile via the task's `version`/state on reconnect (Section 9.6 replay) and a
  refresh of the task snapshot; note that the plan defines no merge-timeout sweeper
  (Section 9.9), so badge freshness equals event freshness plus resume.
* `manual` merge strategy projects (OQ-06) skip the executor — approval there goes
  straight to `completed`; the display must handle an immediate T15 → completed flow
  without flashing a phantom `merging` badge (coordinate with WP-3.6/WP-3.7
  MT-3.7-04 guard).
* Badge wording is specified only as "approved, merging" (Section 8.1) — keep other
  labels consistent with the canonical `merge_status` names to avoid display drift
  (ADR-010: canonical values separate from labels).
