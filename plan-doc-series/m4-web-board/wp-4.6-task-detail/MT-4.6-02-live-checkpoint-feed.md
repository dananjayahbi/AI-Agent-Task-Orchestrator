# MT-4.6-02 — Implement the live checkpoint feed

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.6-02 |
| Title | Implement the live checkpoint feed |
| Parent WP | WP-4.6 — Task detail: checkpoints, resolutions, attachments (Milestone M4) |
| Requirements | FR-WEB-04 |
| Priority | M |
| Dependencies | MT-4.6-01 (detail shell); WP-4.3 complete (MT-4.3-04 stream hook, MT-4.3-05 cache patching); WP-1.8 complete (checkpoint API) |
| Parent sections | 13.2 (Checkpoint feed component), 13.3 (SSE patches), 9.2 (checkpoints endpoints), 9.6 (`task.checkpoint`), 7.2 (Task Checkpoint fields), 19 (WP-4.6), 20.4, 20.5 |

## Context
Section 13.2 defines the component: "Checkpoint feed: reverse-chronological live list
with percent, message, token usage, and auto-scroll toggle." Section 19 WP-4.6
delivers the feed with acceptance "feed streams live." The stream arrives through the
existing Section 9.6 event `task.checkpoint` (already surfaced by the WP-4.3 hook),
initial history through `GET /tasks/{id}/checkpoints` (Section 9.2), and each row
renders the Task Checkpoint fields of Section 7.2: `message`, `percent` (0-100,
nullable), `token_usage`, `kind` (`progress` / `liveness` / `system`), server
`timestamp`.

## Inputs / Prerequisites
* Parent plan Section 13.2 — exact feed contents and the auto-scroll toggle.
* Parent plan Section 9.2 — `GET /tasks/{id}/checkpoints` (history, cursor-paginated).
* Parent plan Section 9.6 — `task.checkpoint` in the event catalog; the WP-4.3 hook
  delivers events (MT-4.3-04) and applies patches (MT-4.3-05).
* Parent plan Section 7.2 — Task Checkpoint entity fields.
* WP-1.8 — checkpoint ingestion (including `next_checkpoint_due` from WP-2.6, shown
  indirectly through lease state if present in responses).
* MT-4.6-01 — the detail region this feed occupies.

## Scope (in)
* The feed component in the task detail's checkpoint region: reverse-chronological
  list rendering percent, message, token usage and the checkpoint `kind`.
* Initial load from `GET /tasks/{id}/checkpoints` with pagination for older entries;
  subsequent entries arrive live via `task.checkpoint` events applied through the
  WP-4.3 cache patching (no refetch-per-event; Section 13.3).
* Auto-scroll toggle: newest-at-top (default reading order) with the toggle controlling
  follow behavior as Section 13.2 states — the toggle persists per user session.
* Resilient states: loading, empty ("no checkpoints yet"), stream-disconnected
  indicator reusing the hook's connection status (Section 13.3 stream hook contract),
  and error state mapped from canonical codes (Section 20.4 item 5).
* Deduplication on reconnect replay (Section 9.6 no-gaps/no-duplicates) — the feed
  must not double-render replayed checkpoints.
* Component tests: fixture history render, live event append, replay dedupe, toggle
  behavior, empty and error states.
* A WP changelog note.

## Out of scope
* The stream hook itself — WP-4.3 (MT-4.3-04).
* Server-side checkpoint ingestion and lease extension — WP-1.8 / WP-2.6.
* Stalled/lease indicators derived from checkpoints — WP-4.9 (MT-4.9-03).
* Mobile feed (and its backgrounding rules) — WP-5.7 (MT-5.7-02).
* Attachments/resolutions content in the feed — MT-4.6-03/04.

## Target paths
* `web/` (checkpoint feed component in the task detail region)
* `web/` tests (feed tests with mocked events)
* WP changelog entry

## Acceptance criteria
- [ ] The feed renders reverse-chronological checkpoints with percent, message and
  token usage exactly per Section 13.2 (nullable fields degrade gracefully per
  Section 7.2).
- [ ] Initial history comes from `GET /tasks/{id}/checkpoints`; live entries arrive via
  `task.checkpoint` events through the WP-4.3 hook and cache patching (Sections 9.2,
  9.6, 13.3).
- [ ] Replayed events after reconnect do not duplicate rows (Section 9.6 contract).
- [ ] Auto-scroll toggle works and its state is user-controllable (Section 13.2).
- [ ] Loading, empty, disconnected and error states are all handled (Section 20.3);
  error messages map from catalog codes only (Section 20.4 item 5).
- [ ] Feed streams live — WP-4.6 acceptance demonstrated against the real SSE
  endpoint.
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to the feed (for example `npm test -- -t checkpoint`)
and confirm: fixture history, live append, replay dedupe, toggle, empty/error states;
then verify live streaming against the running stack per Section 18 and the full web
suite stays green.

## Attachments
* [Section 13.2 — Key components (Checkpoint feed)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.6 — Realtime gateway and event model](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.6 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Checkpoint volume can be high on long tasks — Section 9.2 pagination must gate the
  initial load; rendering the full history unbounded will breach the Section 13.4
  responsiveness target (RISK-13 territory).
* `token_usage` is free-form JSON (Section 7.2) — render defensively (known keys when
  present, no invented schema) and confirm the actual payload shape against WP-1.8's
  implementation before hard-coding labels.
* The auto-scroll toggle's persistence scope (session vs account) is unspecified —
  session-level is the safe default; record the choice in the changelog.
