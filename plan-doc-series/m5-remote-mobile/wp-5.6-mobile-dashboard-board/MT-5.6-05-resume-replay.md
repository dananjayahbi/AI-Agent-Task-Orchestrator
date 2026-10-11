# MT-5.6-05 — Implement resume replay from last event id after suspension

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.6-05 |
| Title | Implement resume replay from last event id after suspension |
| Parent WP | WP-5.6 — Overview dashboard and mobile Kanban (Milestone M5) |
| Requirements | FR-MOB-02, FR-MOB-01 |
| Priority | M |
| Dependencies | MT-5.6-04 (foreground stream lifecycle); MT-5.5-05 (SSE client with resume); WP-1.10 complete (MT-1.10-03 server resume) |
| Parent sections | 14.2 (on resume, replay from the last event id), 9.6 (reconnect resume: no gaps, no duplicates), 19 (WP-5.6), 20.4, 20.5 |

## Context
Section 14.2: "on resume, replay from the last event id." Section 9.6 makes the
contract precise: reconnecting clients send their last event id, receive the missed
events, then switch to live — "no gaps, no duplicates." The server side ships in
MT-1.10-03 and the transport client in MT-5.5-05; Section 19 WP-5.6 acceptance
demands "resume replays missed events." This micro-task persists the last received
event id across suspension, drives replay on resume, and reconciles the board and
dashboard to server truth.

## Inputs / Prerequisites
* MT-5.6-04 — foreground stream lifecycle that suspends/resumes the subscription.
* MT-5.5-05 — SSE client capable of attaching the last event id.
* MT-1.10-03 — server replay-then-live behavior.
* Parent plan Section 9.6 — monotonic event ids and the no-gaps/no-duplicates
  guarantee; Section 7.2 Event Log (`id` monotonic sequence doubles as the SSE
  event id).

## Scope (in)
* Persist the highest processed event id (in memory + durable enough to survive
  suspension — process death handled by re-reading from storage where the platform
  allows; Section 14.2 resume context is app suspension/relaunch).
* On resume/reconnect: attach the last event id, consume the replayed backlog,
  apply each missed event through MT-5.6-04's patching path in id order, then continue
  live — no gap and no duplicate application (idempotent patches; Section 9.6).
* Reconciliation: after replay, board pages and dashboard reflect server state for
  the current project; a task missed entirely while suspended appears after replay.
* Fallbacks: if the server cannot honor replay (too-old id, endpoint rejects it) or
  replay fails, fall back to a full board/dashboard refetch and then resume live —
  never display a known-stale view as live (Section 14.2 polling fallback discipline
  reused).
* Tests: suspend → emit events server-side → resume replays exactly the missed set
  (no duplicates), monotonic ordering, out-of-order/duplicate-id defensive handling,
  replay-failure → refetch fallback, first-launch (no stored id) → live-only path.
* Add a WP changelog note.

## Out of scope
* Server replay implementation — MT-1.10-03.
* The foreground/background connect/disconnect policy — MT-5.6-04 (this task hooks
  the resume moment that lifecycle emits).
* Web reconnect resume — MT-4.3-04/MT-4.3-05.
* Push notification catch-up while backgrounded — WP-5.4/WP-5.9 (missed events while
  backgrounded arrive via push + replay here; push delivery itself is not this task).
* Event Log retention/limits — Section 9.9 retention cleanup (hardening WPs).

## Target paths
* `mobile/` (last-event-id persistence, resume replay orchestration, fallback refetch)
* `mobile/` tests (replay and fallback tests)
* WP changelog entry

## Acceptance criteria
- [ ] On resume after suspension, the client replays from the last event id and the
  missed events are applied — Section 19 WP-5.6 acceptance "resume replays missed
  events" (Section 14.2; FR-MOB-02).
- [ ] Replay then switches to live with no gaps and no duplicates per the
  Section 9.6 contract — asserted by a test counting applied events for a known
  missed range.
- [ ] The stored last id survives suspension; a fresh launch without a stored id
  takes the live-only path safely (no fabricated id).
- [ ] Replay failure or unusable id falls back to full refetch, then live — the UI
  never presents a stale board as current (Section 14.2 fallback discipline;
  RISK-05).
- [ ] Replayed events flow through the same catalog-typed, version-guarded patching
  as live events (Section 20.4 item 6; MT-5.6-04 guards).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the mobile test suite filtered to resume (for example
`flutter test --dart-define=test_filter=resume` or the project's equivalent) and
confirm: missed-event replay with exact counts (no gaps/duplicates), first-launch
live-only path, replay-failure refetch fallback, and ordered patch application; then
the full mobile suite stays green.

## Attachments
* [Section 14.2 — Realtime: resume replay](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.6 — Resume semantics (no gaps, no duplicates)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.6 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Long suspensions can exceed server replay windows (retention is only pinned by
  Section 9.9 cleanup, with no replay-window size stated) — the refetch fallback is
  mandatory for that case; raise OQ-xx to pin the server's replay window so "too
  old" is a defined condition, not a guess.
* Duplicate application during replay/live overlap (last replayed id == first live
  id) is the classic double-patch bug — make patch application idempotent by event
  id and assert it in tests; the plan's "no duplicates" (Section 9.6) is the
  acceptance bar.
