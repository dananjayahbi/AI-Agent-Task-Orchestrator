# MT-5.8-04 — Implement approve-and-merge with resolution-bound confirmation

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.8-04 |
| Title | Implement approve-and-merge with resolution-bound confirmation |
| Parent WP | WP-5.8 — Review action sheet (Milestone M5) |
| Requirements | FR-MOB-05 |
| Priority | M |
| Dependencies | MT-5.8-01 (sheet action bar); MT-5.8-02, MT-5.8-03 (confirmation context: rule results, diff stats); WP-3.6 complete (stale-resolution protection, `POST /tasks/{id}/review`) |
| Parent sections | 14.2 (Approve safety), 11.5 (approve and merge), 8.2 (T15), 7.2 (Review Decision `decided_via`), 19 (WP-5.8 acceptance), 20.4, 20.5; ADR-008 |

## Context
Section 14.2's approve-safety rule is exact: "approve-and-merge requires an explicit
confirmation showing task id, branch, and diff stats; the decision is bound to the
viewed `resolution` id so a newer submission invalidates a stale approval." T15
(Section 8.2) applies on the backend: guard "Resolution exists", `merge_status` =
`pending`, Review Decision recorded — `decided_via` `mobile` for this channel
(Section 7.2). Section 19 WP-5.8 acceptance requires approve to "work end to end
against the real backend; stale approval rejected." Completion itself follows the
Merge Executor (ADR-008) — the mobile UI shows merge-pending, never jumps to
`completed`.

## Inputs / Prerequisites
* Parent plan Section 14.2 — the exact confirmation contents and resolution binding.
* Parent plan Sections 11.5 and 8.2 T15 — action semantics, guards, side effects.
* Parent plan Section 9.2 — `POST /tasks/{id}/review` with `approve` and the
  resolution id/version context; Section 7.2 — Review Decision fields.
* WP-3.6 — endpoint implementation, stale-resolution rejection (Section 19 WP-3.6
  acceptance), `VERSION_CONFLICT` handling.
* Section 14.2 offline rule — no queued approvals; mutations require connectivity.

## Scope (in)
* The approve-and-merge flow: explicit confirmation dialog showing **task id**,
  **branch**, and **diff stats** (Section 14.2), plus a summary of failing/passing
  rules from MT-5.8-02 as supporting context.
* Resolution binding: the approval request carries the id of the `resolution` the
  user viewed; if the task's latest resolution changes meanwhile, the backend
  rejects the stale approval (WP-3.6) and the sheet surfaces that rejection and
  refreshes to the new resolution — requiring a fresh confirmation
  (Section 19 WP-5.8 acceptance "stale approval rejected").
* Submit `approve` via the generated client with disable-while-pending (no
  double-submit; P6/ADR-012 on the wire); on success show merge-pending status
  (T15: `merge_status` = `pending`; completion follows executor reports per
  ADR-008 — mirrored by live updates when foregrounded, Section 14.2).
* Offline: the action is unavailable with the Section 14.2 clear offline state —
  nothing queued, ever (explicit plan rule to avoid stale decisions).
* Conflicts (`TASK_STATE_CONFLICT`/`VERSION_CONFLICT`) refresh with an explanation —
  catalog codes mapped to friendly messages (Sections 13.3-equivalent mobile
  discipline; 20.4 item 5).
* Widget/integration tests: confirmation contents (id/branch/diff stats), payload
  carries viewed resolution id, stale-rejection surfacing + refresh, double-tap
  guard, offline disabled, success → merge-pending display — against the mocked
  backend (Section 14.3) and the real backend in the WP's end-to-end check.
* A WP changelog note.

## Out of scope
* The review endpoint and stale-protection logic — WP-3.6.
* Request changes / reassign — MT-5.8-05/06.
* Merge execution and completion — WP-3.7; mobile observes via events (WP-5.9 /
  sheet refresh).
* Web approve flow — WP-4.8 (MT-4.8-03).
* Biometric re-prompt per action — not specified; app-level gate (Section 14.2).

## Target paths
* `mobile/` (approve confirmation flow in the review sheet)
* `mobile/` tests (widget and integration tests)
* WP changelog entry

## Acceptance criteria
- [ ] Approve opens an explicit confirmation showing task id, branch and diff stats —
  exactly Section 14.2's approve-safety requirements.
- [ ] The decision is bound to the viewed `resolution` id: a newer submission makes
  the backend reject the approval and the sheet refreshes for re-confirmation
  (Section 14.2; Section 19 WP-5.8 acceptance "stale approval rejected"; WP-3.6).
- [ ] Success applies T15 semantics: `merge_status` = `pending` with a Review
  Decision recorded `decided_via` `mobile` — the UI shows merge-pending, never
  premature `completed` (Sections 8.2, 7.2; ADR-008).
- [ ] Offline disables the action with the clear offline state; nothing is queued
  (Section 14.2).
- [ ] Double-submit guarded; conflict errors map from catalog codes to friendly
  messages (Sections 20.4 item 5, ADR-012 context).
- [ ] End-to-end against the real backend passes: approve works and stale approval
  is rejected (Section 19 WP-5.8 acceptance).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the mobile suite filtered to approve (for example
`flutter test --dart-define=test_filter=approve` or the project's equivalent) for
confirmation contents, resolution binding, stale rejection, offline and double-tap
cases; then run the WP end-to-end check against the real backend per Section 19
WP-5.8 acceptance; the full mobile suite stays green.

## Attachments
* [Section 14.2 — Mobile-specific behaviors (Approve safety)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.2 — Transition table (T15)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.8 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Resolution binding requires knowing which resolution the sheet rendered — pin it at
  sheet load and re-pin after any refresh; a background resolution change must
  invalidate the open confirmation, not just the sent request (the stricter reading
  of Section 14.2).
* Diff stats shown in the confirmation come from the backend `diff_summary`
  (Section 9.7) — do not compute them from the renderer (would reintroduce the stale
  mismatch the binding prevents).
* Merge-pending on mobile can outlive a foreground session (executor latency) — the
  sheet must tolerate re-opening later and showing the current `merge_status`
  (Section 8.1 sub-status model), with completion arriving via events/refresh.
