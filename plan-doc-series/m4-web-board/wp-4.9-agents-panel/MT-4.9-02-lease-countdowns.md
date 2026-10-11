# MT-4.9-02 — Implement lease countdown displays

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.9-02 |
| Title | Implement lease countdown displays |
| Parent WP | WP-4.9 — Agents and leases panel (Milestone M4) |
| Requirements | FR-WEB-07 |
| Priority | S |
| Dependencies | MT-4.9-01 (sessions/lease join); WP-4.3 complete (stream hook); WP-1.6 complete (lease fields, `task.lease_expiring`) |
| Parent sections | 13.1 (countdowns), 13.2 (board card worker badge with lease countdown), 8.6 (lease semantics), 7.2 (`lease_expires_at`), 9.6 (`task.lease_expiring`), 19 (WP-4.9), 20.4, 20.5 |

## Context
Section 13.1 lists "countdowns" for the Agents route and Section 13.2 puts a "worker
badge with lease countdown" on board cards. The countdown target is `lease_expires_at`
(Section 7.2; set/extended per Section 8.6: acquire, per-checkpoint extension capped
by `lease_max_total_minutes`). Live changes arrive via `task.claimed`,
`task.checkpoint` (each valid checkpoint moves the expiry), `task.lease_expiring`
(sent at 80% of the lease, Section 9.6) and `task.lease_expired`. Principle P7 — the
server clock is authoritative; the display derives remaining time from server-issued
timestamps, never from client-supplied times.

## Inputs / Prerequisites
* Parent plan Sections 13.1 and 13.2 — where countdowns appear (Agents route, board
  card badge).
* Parent plan Section 8.6 — acquire/extend/expire semantics the countdown must
  reflect (including the hard cap).
* Parent plan Section 7.2 — `lease_acquired_at`, `lease_expires_at`;
  Project Policy `lease_duration_minutes` default 45.
* Parent plan Section 9.6 — lease events through the WP-4.3 hook.
* Principle P7 (Section 6.1) — server clock authority.
* MT-4.9-01 — the sessions/lease join rows that host one of the countdowns.

## Scope (in)
* A reusable countdown component computing remaining time from `lease_expires_at`
  using server-clock alignment (P7): derive remaining duration from the server's
  timestamps/event times, not the browser's notion of "now" alone; tick locally
  between updates.
* Countdown rendering in the Agents list (per active lease) and in the board card
  worker badge (Section 13.2), formatted consistently (e.g. mm:ss/hh:mm remaining).
* Live updates: `task.claimed` resets the countdown; `task.checkpoint` extends it to
  the new `lease_expires_at`; `task.lease_expiring` (80%) can drive a warning state;
  `task.lease_expired`/`task.released` clear the badge (Section 9.6).
* States: no lease (hidden), normal, warning at the Section 9.6 80% signal, expired
  (cleared/zero with transition handled by MT-4.9-03 for stall semantics).
* Component tests: initial computation from fixture timestamps, extension on
  checkpoint event, 80% warning, expiry clearing, server-clock offset handling (P7),
  no lease state.
* A WP changelog note.

## Out of scope
* Lease acquisition/extension/expires logic — WP-1.6 (Section 8.6 server side).
* Stalled detection (`stalled_after_minutes`) — MT-4.9-03 (distinct concept: lease
  valid but no progress).
* Liveness ping mode (OQ-04) — off by default; not displayed differently.
* Push of `task.lease_expiring` — Section 9.8 worker.

## Target paths
* `web/` (countdown component; Agents list and board card integration)
* `web/` tests (countdown tests with fixture lease data)
* WP changelog entry

## Acceptance criteria
- [ ] Countdown displays on the Agents route and the board card worker badge
  (Sections 13.1, 13.2) for tasks with an active lease.
- [ ] Remaining time derives from server-issued `lease_expires_at` with server-clock
  authority — no client-authoritative time math (Principle P7; Section 8.6).
- [ ] The countdown updates live on `task.claimed`, `task.checkpoint` (extension),
  `task.lease_expiring` (warning at 80%) and clears on expired/released
  (Sections 9.6, 8.6).
- [ ] The extension shown never exceeds the Section 8.6 hard-cap behavior — display
  mirrors server values, never guesses (Section 8.6).
- [ ] Lease-free states render nothing rather than zero-value noise (Section 20.3).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to leases (for example `npm test -- -t lease`) and
confirm initial countdown, checkpoint extension, 80% warning, expiry clearing, and
server-clock offset handling; then the full web suite stays green.

## Attachments
* [Section 8.6 — Lease semantics in detail](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.2 — Key components (board card badge)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* P7 strictness: a browser with a skewed clock must not show negative/wild
  countdowns — anchor to server timestamps from events/responses and re-anchor on
  each update; document the offset approach in the changelog.
* `lease_expires_at` moves on every checkpoint, so a ticking display is only as
  fresh as the last event — on stream disconnect, show the connection status
  (Section 13.3) rather than silently counting down stale time.
* Board cards already show several badges (Section 13.2) — adding countdown updates
  at 1 s ticks across 500 cards risks Section 13.4 regressions; batch/throttle ticks
  (one timer for visible cards).
