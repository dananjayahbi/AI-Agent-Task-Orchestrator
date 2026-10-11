# MT-4.9-03 — Implement stalled-task indicators (stalled_after_minutes)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.9-03 |
| Title | Implement stalled-task indicators (stalled_after_minutes) |
| Parent WP | WP-4.9 — Agents and leases panel (Milestone M4) |
| Requirements | FR-WEB-07 |
| Priority | S |
| Dependencies | MT-4.9-01, MT-4.9-02 (sessions and lease context); WP-4.3 complete (stream hook); WP-1.8 complete (checkpoints, `last_checkpoint_at`) |
| Parent sections | 8.6 (stalled indicator definition), 7.2 (`stalled_after_minutes` default 20), 9.6 (`task.checkpoint`, `system.alert`), 9.9 (stalled-task detector), 13.2 (card stalled marker), 19 (WP-4.9 acceptance), 20.4, 20.5 |

## Context
Section 8.6 defines the concept precisely and marks it UI-only: "A task is 'stalled'
if no `progress` checkpoint arrived within `stalled_after_minutes`, even though the
lease is still valid." The threshold is the Project Policy field
`stalled_after_minutes` (Section 7.2, default 20). Section 13.2 puts a
"stalled/escalation marker" on board cards; Section 9.9 runs a stalled-task detector
every 5 minutes emitting `system.alert` flags for the UI (Section 9.6 catalog), and
Section 9.6 delivers `task.checkpoint` live. Section 19 WP-4.9 acceptance: "stalled
indicator appears after `stalled_after_minutes` without progress."

## Inputs / Prerequisites
* Parent plan Section 8.6 — the exact stalled definition (progress checkpoints only;
  lease still valid; UI-only).
* Parent plan Section 7.2 — `stalled_after_minutes` (policy, default 20), Task
  `last_checkpoint_at`, checkpoint `kind` (`progress` / `liveness` / `system`).
* Parent plan Sections 9.6 and 9.9 — `task.checkpoint` events and the server-side
  detector's `system.alert` flags.
* Parent plan Section 13.2 — where the marker appears (board card) and Section 13.1
  (Agents route context).
* MT-4.9-02 — lease state the stall condition coexists with (stall ≠ expiry).

## Scope (in)
* A stalled indicator component/logic: given `last_checkpoint_at`, the policy's
  `stalled_after_minutes`, and an active lease, mark the task stalled once the
  threshold passes without a `progress` checkpoint — per Section 8.6's definition
  (kind matters: liveness/system checkpoints do not clear a stall unless the server
  treats them as progress; follow what WP-1.8 stores on `last_checkpoint_at`).
* Placement: board card stalled/escalation marker (Section 13.2) and an indicator in
  the Agents lease view (Section 13.1 scope), using a consistent visual with an
  accessible text label (Section 13.4 a11y).
* Live clearing: a new `task.checkpoint` (progress) for the task clears the indicator
  immediately (Section 9.6); `task.lease_expired`/release ends the stall context
  (task no longer has a valid lease — Section 8.6 definition).
* Server flag intake: consume `system.alert` events (Section 9.9 detector) as a
  cross-check/refresh — the client computes for immediacy (UI-only per 8.6) and the
  server flag covers missed events.
* Policy threshold source: read `stalled_after_minutes` from project policy data the
  client already has (Section 7.2) — no hard-coded 20 beyond the documented default.
* Component tests: before-threshold (not stalled), after-threshold (stalled), clear
  on progress checkpoint, clear on lease end, `system.alert` intake, threshold
  honored when policy value differs from default.
* A WP changelog note.

## Out of scope
* The server-side detector job — Section 9.9 (WP-1.x).
* Escalation transitions (retry exhaustion T9, etc.) — state machine, not this
  indicator (stall is UI-only, Section 8.6).
* Lease countdowns/sessions — MT-4.9-01/02.
* Push notifications for stalled work — Section 9.8 triggers don't include stalls;
  do not invent one.

## Target paths
* `web/` (stalled indicator logic and placements: board card, agents view)
* `web/` tests (stall state tests with fixture data)
* WP changelog entry

## Acceptance criteria
- [ ] The stalled indicator appears after `stalled_after_minutes` passes with no
  progress checkpoint while the lease is still valid — Section 19 WP-4.9 acceptance
  and Section 8.6 definition, using the policy value (default 20, Section 7.2).
- [ ] Liveness/system checkpoint kinds are handled per the server's
  `last_checkpoint_at` semantics — the indicator never contradicts Section 8.6
  ("no `progress` checkpoint").
- [ ] A fresh progress `task.checkpoint` clears the indicator live (Section 9.6);
  lease end stops showing stall (Section 8.6).
- [ ] `system.alert` events from the Section 9.9 detector refresh/cross-check the
  indicator (Sections 9.6, 9.9; 20.4 item 6).
- [ ] The marker renders on board cards per Section 13.2 with accessible labeling
  (Section 13.4).
- [ ] No hard-coded threshold beyond the documented policy default; canonical event
  and state names only (Sections 20.4 items 5–6, 20.5).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to stalled (for example `npm test -- -t stall`) and
confirm threshold crossing, custom policy threshold, checkpoint clearing, lease-end
behavior, and `system.alert` intake; then the full web suite stays green.

## Attachments
* [Section 8.6 — Lease semantics (stalled indicator)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.9 — Background jobs (stalled-task detector)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.9 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The detector runs every 5 minutes (Section 9.9) while the client computes
  instantly — acceptance says "after `stalled_after_minutes`", so rely on the
  UI-only client computation (Section 8.6) for promptness and treat `system.alert`
  as reinforcement; documenting this split avoids a false "wait up to 5 min"
  interpretation.
* Policy threshold can change mid-view — re-read on project policy updates rather
  than caching the number at page load.
* Stall ≠ escalation: do not conflate the marker with `in_human_review` reasons
  (Section 8.4 enum) — stall has no transition reason code (Section 8.6 UI-only),
  and inventing one would violate Section 20.5.
