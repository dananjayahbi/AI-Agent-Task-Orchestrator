# MT-4.4-04 — Implement optimistic update with rollback on version/state conflicts

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.4-04 |
| Title | Implement optimistic update with rollback on version/state conflicts |
| Parent WP | WP-4.4 — Drag-and-drop with validation (Milestone M4) |
| Requirements | FR-WEB-02 |
| Priority | M |
| Dependencies | MT-4.4-01 (map), MT-4.4-02 (move callback), MT-4.4-03 (dialog outcomes), WP-4.3 (query cache + SSE patching), WP-4.1 (typed API client) |
| Parent sections | 13.2, 8.2, 9.6, 19 (WP-4.4), 20.4, 20.5 |

## Context
Section 13.2: "Optimistic UI with rollback on `VERSION_CONFLICT` or
`TASK_STATE_CONFLICT`." Section 8.2's rules: "The UI sends the `version` it saw; a
stale version returns a conflict and the UI refreshes" and illegal transitions return
`TASK_STATE_CONFLICT` (HTTP 409). WP-4.4's acceptance: "stale versions reconcile
gracefully." The board already patches its query cache from SSE events (WP-4.3
MT-4.3-05), so this task closes the loop: move appears instantly, the server decides,
and either the event confirms it or a conflict rolls the card back and refreshes.

## Inputs / Prerequisites
* MT-4.4-01..03 — map, DnD wiring, dialog outcomes feeding the move callback.
* Parent plan Sections 13.2, 8.2 — optimistic rule, version discipline, conflict
  codes.
* Parent plan Section 9.6 — SSE event stream (post-commit `task.transitioned` /
  `review.decided` patches that confirm or supersede the optimistic state).
* WP-4.3 (MT-4.3-04/05) — stream hook with reconnect/resume and cache patching.
* WP-4.1 — typed API client exposing `POST /tasks/{id}/transition` and
  `POST /tasks/{id}/review` with the `version`/`resolution_id` bindings.

## Scope (in)
* The move callback: on `allowed` (or dialog confirm), apply an optimistic cache
  patch — card moves to the target column immediately — then send the server call
  carrying the `version` the client saw (Section 8.2).
* Rollback: on `VERSION_CONFLICT` or `TASK_STATE_CONFLICT` (HTTP 409), revert the
  optimistic patch to server truth and refresh the affected task(s) from the API —
  the card lands where the server says, with a transient notice explaining the
  refresh (Section 13.2).
* Reconciliation with the stream: the confirming `task.transitioned` /
  `review.decided` event settles the optimistic state idempotently; a conflicting
  event received mid-flight supersedes the local patch (WP-4.3 cache patching stays
  the single writer afterward).
* Canonical-code messaging: `VERSION_CONFLICT` and `TASK_STATE_CONFLICT` map to
  friendly, distinct messages per Section 13.3; no raw envelope text in the UI.
* Dialog-driven moves (MT-4.4-03) use the same optimistic/rollback path on success.
* Tests: optimistic-then-confirmed flow; conflict rollback restores the original
  card position and version; event arriving before/after the HTTP response both
  settle idempotently; no flicker of double moves; failure keeps filters/scroll
  intact.

## Out of scope
* The map, DnD, dialogs — MT-4.4-01..03.
* Server conflict production (stale version → 409) — WP-1.5/WP-3.6 (consumed).
* General SSE reconnect/resume and cache patching infrastructure — WP-4.3.
* Backend event emission — WP-1.9/WP-1.10.

## Target paths
* `web/` — optimistic move/rollback module wired to the move callback
* `web/tests/` — optimistic/rollback tests
* WP changelog entry

## Acceptance criteria
- [ ] An allowed move (or confirmed dialog action) reflects immediately in the UI
  before the server responds (Section 13.2 optimistic UI).
- [ ] `VERSION_CONFLICT` and `TASK_STATE_CONFLICT` responses roll the card back to
  server truth and refresh, with distinct friendly messages (Sections 13.2, 13.3;
  Section 9.2 codes).
- [ ] The client sends the `version` it saw on every move; a stale version conflicts
  rather than silently overwriting (Section 8.2).
- [ ] SSE events confirm or supersede the optimistic state idempotently — no
  double-move or oscillation when response and event race (Section 9.6, WP-4.3
  cache patching).
- [ ] WP-4.4 acceptance: stale versions reconcile gracefully — no stuck ghost cards,
  lost tasks or broken filters after rollback.
- [ ] Only catalog error codes referenced (Section 20.4 item 5); lint/type/tests
  green (item 2); changelog note added (item 7).

## Test command
`npm test -- -t optimistic-rollback` — assert instant visual move, rollback to
server truth on both conflict codes with mapped messages, idempotent event/HTTP
settlement in both orders, and intact board state after rollback; then the full web
suite stays green.

## Attachments
* [Section 13.2 — Key components (optimistic UI)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.2 — Transition table (version discipline)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Two writers on the cache (optimistic patch vs SSE patch) is the classic race —
  define settlement order once (event wins after confirmation) and test both arrival
  orders; do not "fix" flicker by disabling events.
* Rollback must restore the *server* truth, not the pre-drag local state — another
  actor may have moved the card meanwhile; refresh beats restore-from-memory.
* Swallowing conflicts as silent refreshes would hide real misuse (e.g. approving a
  stale resolution) — always surface the mapped message so the operator re-orients.
