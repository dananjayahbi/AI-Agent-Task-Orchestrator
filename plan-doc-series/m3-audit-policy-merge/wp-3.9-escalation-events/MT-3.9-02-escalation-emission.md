# MT-3.9-02 — Implement escalation event emission on every in_human_review entry

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.9-02 |
| Title | Implement escalation event emission on every in_human_review entry |
| Parent WP | WP-3.9 — Escalation notifications hook (Milestone M3) |
| Requirements | FR-MOB-04 |
| Priority | M |
| Dependencies | MT-3.9-01 (payload contract), WP-1.5 (state machine), WP-1.9 (event log), WP-3.4 (rule details on policy escalations) |
| Parent sections | 8.2 (T8, T9, T14, T18), 8.4, 9.6, 9.8, 19 (WP-3.9), 20.4, 20.5 |

## Context
FR-MOB-04: push notification when any task enters `in_human_review`. Section 9.8:
triggers are "`in_human_review` entry (all reasons), merge failure, retry
exhaustion". Four transitions in the Section 8.2 table enter `in_human_review`: **T8**
(submit self-flagged or scope violation → `review_reason` `self_flagged` /
`scope_violation`), **T9** (retry exhausted → `retry_exhausted`), **T14** (verdict +
any rule fails → enumerated reason), **T18** (merge conflict/failure →
`merge_conflict`). Section 8.2's global rules: every transition runs inside one
database transaction that also writes the Transition row and the Event row; Section
9.6: every state-changing action writes an Event row and, after commit, publishes it
to the Redis channel. This task makes entry emission systematic — a hook on the
transition itself, not scattered per-callsite sends.

## Inputs / Prerequisites
* MT-3.9-01 — the `review.requested` payload contract.
* Parent plan Section 8.2 — the four entering transitions and their side effects.
* Parent plan Sections 9.6, 9.8 — event writing/publication and the push trigger.
* WP-1.5 — state machine where the hook lives.
* WP-1.9 — event log machinery (row + post-commit publish).
* WP-3.4 — rule details available for T14 escalations (and absent by design for
  T8/T9/T18, where no policy evaluation runs).

## Scope (in)
* A single emission point in the transition path: whenever `to_state` is
  `in_human_review` (T8, T9, T14, T18), write exactly one `review.requested` event
  with the correct canonical `review_reason` and, where the Policy Engine decided
  (T14), the persisted rule details — in the same transaction as the Transition and
  task rows (Section 8.2), published after commit (Section 9.6).
* Reason sourcing per transition: T8 → `self_flagged` or `scope_violation`; T9 →
  `retry_exhausted`; T14 → the enumerated reason from the failed rule(s)
  (Section 8.4/9.4); T18 → `merge_conflict`.
* Rule-details availability: T14 carries rule results; T8/T9/T18 carry no policy rule
  results — the payload still names the reason (do not fabricate empty rule sets as
  "failures"; absence must be expressible per MT-3.9-01's contract).
* No emission for any other transition (no `review.requested` on `pending`,
  `to_be_audited`, `completed`, etc.); no double emission when side effects list
  "push notification" (T8/T9/T14/T18) — push is a downstream consumer of this one
  event (WP-5.4), not a second writer.
* Tests: each of the four transitions produces one event with the right reason;
  re-entry after a later cycle (T18 back into `in_human_review`) emits again;
  non-entry transitions emit none; publication happens post-commit only.

## Out of scope
* Payload field design — MT-3.9-01.
* Per-reason coverage of all 12 enum values — MT-3.9-03.
* Push dispatch and dedupe — WP-5.4; the web/mobile in-app displays — WP-4.x/WP-5.9.
* Emitting `review.decided` — WP-3.6's endpoint.

## Target paths
* `backend/` — transition-path `review.requested` emission hook
* `backend/tests/` — emission tests
* WP changelog entry

## Acceptance criteria
- [ ] Every entry into `in_human_review` (T8, T9, T14, T18) writes exactly one
  `review.requested` event carrying the canonical `review_reason` (Section 9.8
  trigger; Section 8.2 side effects; Section 20.4 item 6).
- [ ] T14 events include the Policy Engine's persisted rule details; T8/T9/T18 carry
  their reason without fabricated rule results (Section 9.4, MT-3.9-01 contract).
- [ ] The event row is written in the same transaction as the Transition row, and
  published to the stream only after commit (Sections 8.2, 9.6).
- [ ] Non-entry transitions emit no `review.requested`; a task that re-enters
  `in_human_review` later emits a fresh event (one per entry, not one per task).
- [ ] Only catalog/Section 9.6 event types used (Section 20.4 items 5–6);
  lint/type/tests green (item 2); changelog note added (item 7).

## Test command
`pytest backend/tests -k review_requested_emission -q` — drive T8, T9, T14 and T18
transitions and assert one correctly-reasoned event each, zero events for control
transitions, same-transaction write, and post-commit publication; then
`pytest backend/tests -q` stays green.

## Attachments
* [Section 8.2 — Transition table (T8, T9, T14, T18)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.8 — Notifications](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Scattered per-callsite "send a push" code is exactly what this hook replaces —
  if a fifth entry path appears later (plan change), it must flow through the same
  transition hook; centralize or the acceptance silently rots.
* Double emission (event + a direct push writer) would double-notify once WP-5.4
  lands — assert single-writer ownership of the trigger.
* T14's rule details come from WP-3.4's persistence; if that write lags the event
  in the transaction, the payload ships empty — order the writes inside the one
  transaction and test it.
