# MT-4.3-05 — Implement query-cache patching from stream events

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.3-05 |
| Title | Implement query-cache patching from stream events |
| Parent WP | WP-4.3 — Kanban board (read) with realtime (Milestone M4) |
| Requirements | FR-WEB-05, FR-WEB-01 |
| Priority | M |
| Dependencies | MT-4.3-04 (stream hook delivering events); MT-4.3-01/MT-4.3-02/MT-4.3-03 (board, cards, filters as cache consumers) |
| Parent sections | 13.3 (SSE applies event patches to the cache), 9.6 (event envelope and catalog), 7.2 (version), 19 (WP-4.3), 20.4, 20.5 |

## Context
Section 13.3: "Server state cached and invalidated through a query library; the SSE
stream applies event patches to the cache so the board updates without refetching."
Section 9.6's envelope carries `task_id`, `project_id`, `task_version` and payload
data (e.g. `task.transitioned` with `from_state`, `to_state`, `reason_code`). Section
19 WP-4.3 acceptance sets the bar: "a transition made by an agent appears within 2 s
without refresh; reconnect restores state with no gaps." This micro-task turns the
hook's event feed (MT-4.3-04) into cache mutations so cards move, update and disappear
without refetch storms.

## Inputs / Prerequisites
* MT-4.3-04 — typed event delivery with reconnect/resume.
* Parent plan Section 9.6 — event envelope fields and catalog
  (`task.created|updated|transitioned|claimed|released`, `task.checkpoint`,
  `task.lease_expiring`, `task.lease_expired`, `audit.*`, `review.*`, `merge.*`,
  `agent.session_*`, `system.alert`).
* MT-4.3-01 … MT-4.3-03 — the query keys (board per project/filters, card data) the
  patches target.
* Section 7.2 Task `version` — optimistic concurrency; events carry `task_version`.

## Scope (in)
* An event-to-cache adapter subscribing to the MT-4.3-04 hook and applying targeted
  patches to the query cache:
  * `task.transitioned` — move the task between column groups (state change) using
    `to_state`;
  * `task.updated` / `task.claimed` / `task.released` — refresh card fields (worker,
    lease, priority, review reason) in place;
  * `task.checkpoint` — update percent/last-checkpoint on the card;
  * `task.created` — insert into the correct column (respecting active filters and
    archive default);
  * `task.lease_expiring` / `task.lease_expired` — update lease/countdown/stalled
    presentation data;
  * other catalog events affecting board data (e.g. `merge.*` for the
    merge-pending badge) — patch where the board displays the affected field.
* Stale-event protection: ignore patches whose `task_version` is older than the
  cached version (never regress newer local data).
* Filter-aware insertion/removal so a patched task respects MT-4.3-03 predicates.
* Unknown event types ignored without breaking the stream (Section 9.6 catalog is
  closed; Section 20.4 item 6).
* Tests per event type: patch correctness, version staleness ignored, filter
  awareness, no-refetch assertion (board updates without a network call), and
  end-to-end "agent transition appears without refresh".
* Add a WP changelog note.

## Out of scope
* Producing events — backend (WP-1.9 / transition writers).
* The stream connection itself — MT-4.3-04.
* Invalidating instead of patching on complex changes — keep patches targeted; full
  refetch fallback only for events outside board scope.
* Review/audit/merge workflow mutations (actions that change state) — WP-4.8 / WP-4.4
  (this task is read-path patching only).
* Mobile cache patching — WP-5.6 (Flutter side).

## Target paths
* `web/` (event → cache adapter, subscriptions)
* `web/` tests (per-event patch tests, no-refetch assertions)
* WP changelog entry

## Acceptance criteria
- [ ] An agent-made transition appears on the board within 2 s without any page
  refresh or refetch — Section 19 WP-4.3 acceptance (FR-WEB-05) demonstrated by a
  test asserting no network refetch during the patch.
- [ ] `task.transitioned` moves the card between the six canonical columns using
  `to_state`; card fields patch in place for `task.updated`, `task.claimed`,
  `task.released`, `task.checkpoint` (Section 13.3: stream applies event patches).
- [ ] Stale events (older `task_version`) are ignored — cached newer state never
  regresses (Section 7.2 `version`; Section 9.6 envelope).
- [ ] Patches respect active filters and the archive default from MT-4.3-03.
- [ ] Only Section 9.6 catalog event types are processed; unknown types ignored
  safely (Section 20.4 item 6).
- [ ] Reconnect replay after MT-4.3-04 resume applies missed patches idempotently —
  no duplicate cards, no gaps (Section 9.6; Section 19 WP-4.3 acceptance part 2).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to cache patching (for example `npm test -- -t
cache`) and confirm: per-event patch cases, stale-version ignore, filter-aware
insert/remove, no-refetch on transition, and idempotent replay after reconnect; then
the full web suite stays green.

## Attachments
* [Section 13.3 — Data and state handling (SSE cache patching)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.6 — Event envelope and catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.3 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Patch granularity vs. refetch: events carry partial payloads (Section 9.6 example
  has `from_state`/`to_state` only) — a card patch may miss fields changed in the same
  action; if a field is absent from the event, prefer a targeted single-task refetch
  over guessing, and document which events are patch vs. invalidate.
* The 2 s acceptance target depends on server post-commit publishing (Section 9.6);
  measure end-to-end during integration — if the gap is server-side, log it against
  WP-1.10/WP-1.9 rather than masking it with polling in this task.
