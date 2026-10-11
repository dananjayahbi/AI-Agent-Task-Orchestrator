# MT-3.7-05 — Implement conflict reporting back to in_human_review (merge_conflict)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.7-05 |
| Title | Implement conflict reporting back to in_human_review (merge_conflict) |
| Parent WP | WP-3.7 — Merge queue and Merge Executor (Milestone M3) |
| Requirements | FR-AUD-06 |
| Priority | M |
| Dependencies | MT-3.7-01 (failure result path); MT-3.7-04 (strategy failure classification); WP-3.9 events context (review.requested) |
| Parent sections | 11.4 (step 4), 8.1 (conflict arrow), 8.2 (T18), 8.4 (review reasons), 9.6, 9.8, 19 (WP-3.7), 20.4, 20.5; ADR-008 |

## Context
Section 8.1's diagram shows the conflict arrow: "merge conflict / failure → back to
in_human_review (review_reason = merge_conflict)". T18 (Section 8.2) formalizes it:
actor M (Merge Executor), trigger "Merge conflict/failure", side effects `merge_status`
= `conflict`/`failed`, `review_reason` = `merge_conflict`, push notification.
`merge_conflict` is in the canonical review-reason enum (Section 8.4). Section 11.4
step 4 requires the executor to "abort cleanly and report details" while Section 19
WP-3.7 acceptance demands the developer's working tree stays untouched. This task
connects the executor's failure report to that escalation.

## Inputs / Prerequisites
* Parent plan Section 11.4 step 4 — abort cleanly and report details.
* Parent plan Section 8.2 T18 — exact transition and side effects.
* Parent plan Section 8.4 — `merge_conflict` must be used verbatim from the enum.
* Parent plan Section 9.8 — merge failure is a push-notification trigger (FCM via
  worker, dedupe key `(event type, task id, state version)`).
* Parent plan Section 9.6 — `merge.failed` event, emitted after commit.
* MT-3.7-01 — the `POST /merge/{task}/result` failure branch this task drives.
* MT-3.7-03 — clean abort in the worktree with the dev tree untouched.

## Scope (in)
* Executor-side conflict detection: when the strategy merge fails or conflicts, abort
  the merge in the worktree (no partial state), destroy the worktree, and collect
  report details (task id, strategy, branch, the Git failure summary — carried as
  `details` in the standard error/result envelope of Section 9.2, not a new envelope).
* Result call to `POST /merge/{task}/result` with the failure outcome so the backend
  applies T18 exactly once: `merge_status` `conflict`/`failed`,
  `review_reason` = `merge_conflict`, task back in `in_human_review` (Sections 8.2,
  8.4).
* Backend side of T18 (if not already covered by MT-3.7-01): emit `merge.failed`
  (Section 9.6) after commit and trigger the merge-failure push of Section 9.8.
* The escalation becomes visible to reviewers: the reason is stored on the task and
  surfaces in the review panel/queue (WP-4.8 consumption — out of scope here).
* Tests: simulated conflict in a scratch repo → worktree destroyed, dev tree
  byte-identical, failure result accepted, task asserted in `in_human_review` with
  `review_reason` = `merge_conflict`, one `merge.failed` event, one push trigger.
* A WP changelog note.

## Out of scope
* The success path and T17 — MT-3.7-01.
* Web/mobile display of the conflict — WP-4.8 (MT-4.8-04), WP-5.x.
* Automatic conflict resolution or rebase assistance — not in the plan; human review
  is the resolution path (Section 8.1, RISK-04).
* Changing the canonical reason enum — Section 8.4 is closed (Section 20.5).

## Target paths
* `bridge/` (conflict abort and failure report in the merge executor)
* `backend/` (T18 side-effect assertions if extended beyond MT-3.7-01)
* `backend/` and `bridge/` tests (conflict path)
* WP changelog entry

## Acceptance criteria
- [ ] A merge conflict aborts cleanly: no partial merge state, worktree removed,
  developer's working tree untouched (Sections 11.4 step 4, 19 WP-3.7 acceptance).
- [ ] The failure report applies T18 exactly once: task back to `in_human_review`,
  `merge_status` conflict/failed, `review_reason` = `merge_conflict` — verbatim
  canonical values (Sections 8.2, 8.4).
- [ ] `merge.failed` is emitted after commit and the merge-failure push fires with the
  Section 9.8 dedupe key (Sections 9.6, 9.8, 20.4 item 6).
- [ ] Report details travel inside the standard Section 9.2 envelope — no bespoke
  error format (Section 20.4 item 5: codes from the catalog, e.g.
  `TASK_STATE_CONFLICT` for wrong-state reports).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `uv run pytest bridge/tests/ -k conflict_report -q` together with
`pytest backend/tests -k t18 -q` and confirm: simulated conflict → clean abort, dev
tree untouched, T18 applied once (`in_human_review` + `merge_conflict`), `merge.failed`
event and push trigger observed; then both full suites stay green.

## Attachments
* [Section 8.2 — Transition table (T18)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.4 — Review reasons (canonical enum)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.7 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "Report details" (Section 11.4) has no specified schema — keep fields minimal and
  carry them in the result payload/event `data`; any new persisted field is a schema
  change requiring Section 20.4 item 4 review.
* Repeated conflicts on the same task will re-enter review each time (T18 loop) —
  RISK-04 territory; no automatic retry counter for merges exists in Section 9.9, and
  inventing one would be a plan change.
* Push failures must not block the T18 transition: Section 9.8 dispatch is worker-side
  with retry — commit the transition first, notify after (Section 9.6 "after commit").
