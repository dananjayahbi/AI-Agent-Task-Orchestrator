# MT-1.7-04 — Implement the Lease-Expiring Warning Event at 80% of Lease

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.7-04 |
| Title | Implement the lease-expiring warning event at 80% of lease |
| Parent WP | WP-1.7 — Lease sweeper and retry policy (Milestone M1) |
| Requirements | FR-LEA-04, FR-LEA-05, NFR-03 |
| Priority | M |
| Dependencies | MT-1.7-01 (beat/worker wired); MT-1.6-01 (lease record) |
| Parent sections | 9.6 (event catalog), 9.9, 19 (WP-1.7), 20.4, 20.5 |

## Context
Section 9.6's event catalog includes `task.lease_expiring` "(sent at 80% of lease)",
and the Section 9.9 job table pairs the lease sweeper with a "Lease-expiring
notifier, every 60 s, emits warning events at 80% of lease". WP-1.7 lists it as a
deliverable ("lease-expiring warning job"). The warning is what lets the web/mobile
boards (agents and leases panel) and the bridge see a lease about to lapse before
the sweeper applies T5 — turning silent expiry (RISK-02) into a visible signal.

## Inputs / Prerequisites
* MT-1.7-01 — beat schedule with the second 60-second stub entry to replace.
* MT-1.6-01 — lease fields `lease_acquired_at`, `lease_expires_at`,
  `lease_generation`, `lease_duration_minutes` from Project Policy (Section 7.2).
* Section 9.6 — `task.lease_expiring` is a catalog event; envelope shape per
  Section 9.6 (id, type, project_id, task_id, occurred_at, actor, data).
* WP-1.9 — event-log write and post-commit publish path (the warning must reach SSE
  subscribers per Section 9.6).
* NFR-03 — realtime delivery expectations (event flows to stream clients).

## Scope (in)
* Implement the lease-expiring notifier Celery task on the Section 9.9 60-second
  schedule: find `in_progress` tasks where the 80%-of-lease point has been passed
  (now >= `lease_acquired_at` + 0.8 × current lease window toward
  `lease_expires_at`) and the lease is still valid, and emit `task.lease_expiring`
  once per lease window.
* Exactly-once-per-window semantics: the event carries `lease_generation`; a lease
  extended by checkpoints (MT-1.6-03) starts a new window with a new expiry — decide
  and document the re-emission rule consistently with the generation so extensions
  can re-arm the warning without duplicate spam within one window (see Risk notes
  for the OQ trigger).
* Emit through the WP-1.9 event path so the event reaches the SSE stream
  (Section 9.6) and history (`GET /events`) — consumers: WP-4.9 agents panel,
  bridge display later.
* Payload `data` includes what consumers need to act: task id, lease expiry,
  generation (Section 9.6 envelope; no invented envelope fields).
* Tests: sub-80% → no event; crossing 80% → exactly one event; repeated runs within
  the window → no duplicates; after expiry/sweep → no event (the
  `task.lease_expired` event from T5 takes over); extended lease re-arms per the
  documented rule.
* Add a WP changelog note.

## Out of scope
* Consuming the warning in web/mobile UI — WP-4.9 (agents and leases panel).
* SSE transport and resume — WP-1.10 (events must simply exist to be streamed).
* The sweeper's T5 reclaim and `task.lease_expired` — MT-1.7-02.
* Push notifications for the warning — not a Section 9.8 trigger; do not add.
* Stalled-task detector (5-minute job, Section 9.9) — WP-4.9/UI concern; not part
  of this WP's slices.

## Target paths
* `backend/apps/leases/` (notifier task)
* `backend/` Celery beat schedule (60 s notifier entry active)
* `backend/tests/` (notifier tests)
* WP changelog entry

## Acceptance criteria
- [ ] A lease that passes 80% of its window while still valid produces exactly one
  `task.lease_expiring` event — catalog type, Section 9.6 envelope
  (Section 20.4 items 5 and 6).
- [ ] No duplicate warnings within one lease window across repeated 60-second runs
  (FR-LEA-05 idempotency pattern; Section 9.9).
- [ ] No warning fires for expired or already-swept leases; T5's
  `task.lease_expired` remains the sole expiry event.
- [ ] The event flows through the WP-1.9 write/publish path so SSE subscribers can
  receive it (NFR-03 path, Section 9.6).
- [ ] Emission is generation-aware so checkpoint extensions behave per the
  documented rule (Section 8.6 extension).
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k lease_expiring_warning -q` and confirm the 80%
threshold, single emission per window, no emission after expiry, and
extension/re-arm behavior; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 9.6 — Realtime gateway and event model](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.9 — Background jobs](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan fixes "80% of lease" and the 60-second interval but not the re-emission
  rule after a checkpoint extension — pick generation-scoped single emission as the
  reading of Section 8.6 (each extension defines the remaining window); if
  re-warning on every extension proves noisy or ambiguous, raise an OQ (Section 22
  numbering) before changing semantics.
* 80% of a 45-minute default window is ~36 minutes in — with `lease_duration_minutes`
  overridable per project, guard against zero/negative durations (policy validation
  belongs to WP-1.3; fail closed here).
