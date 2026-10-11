# MT-4.3-06 — Add column virtualization for 500-card boards

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.3-06 |
| Title | Add column virtualization for 500-card boards |
| Parent WP | WP-4.3 — Kanban board (read) with realtime (Milestone M4) |
| Requirements | FR-WEB-01, FR-WEB-05 |
| Priority | M |
| Dependencies | MT-4.3-02 (card component), MT-4.3-01 (columns), MT-4.3-05 (live patching under virtualization) |
| Parent sections | 13.4 (500-card responsiveness), 13.2 (Board), 19 (WP-4.3), 20.3, 20.4, 20.5 |

## Context
Section 13.4 sets the non-functional target: "Board with 500 cards stays responsive
(virtualized columns); first load under 3 s on LAN; keyboard navigation for the board
and dialogs." Section 19 WP-4.3 lists virtualization as the WP's final slice. With
SSE patching (MT-4.3-05) re-rendering cards on every event, rendering all cards in
the DOM would blow the responsiveness target — column virtualization (windowing) keeps
rendered nodes bounded while scrolling and during live updates.

## Inputs / Prerequisites
* MT-4.3-01/MT-4.3-02 — columns hosting TaskCard components.
* MT-4.3-05 — event patching that must not force full-column re-renders.
* Parent plan Section 13.4 — the measurable targets: 500-card board responsive,
  keyboard navigation, first load under 3 s on LAN (load time is shared with
  WP-4.1/data layer; virtualization's share is render/scroll performance).

## Scope (in)
* Windowed rendering for each board column: only visible cards (+ small overscan)
  mounted in the DOM, via a virtualization approach consistent with the project's
  stack (no new heavy dependency without recording the choice).
* Stable row identity by task id so scroll position and card state survive live
  patches (MT-4.3-05) and filter changes (MT-4.3-03).
* Interaction with live updates: a card entering/leaving a column via a patch
  reconciles with the virtual window without scroll jumps or focus loss where
  feasible (document behavior).
* Preserve keyboard navigation reachability for off-screen cards per Section 13.4
  (focus/scroll-into-view for keyboard traversal) — virtualization must not create a
  keyboard dead end; deep a11y audit remains WP-4.11.
* Performance test/benchmark with a synthetic 500-card board fixture: assert bounded
  rendered card nodes (far below 500 mounted) and responsive scroll/patch behavior;
  first-load budget kept (Section 13.4).
* Add a WP changelog note.

## Out of scope
* Changing the card or column designs — MT-4.3-01/MT-4.3-02.
* Drag-and-drop integration with virtualized lists — WP-4.4 (coordinate there).
* Mobile board paging — WP-5.6 (Flutter horizontally paged board; different
  technique).
* Server pagination of tasks — not part of Section 13.2; board loads the project set
  it needs (raise OQ-xx if 500-card load time misses the 3 s target even
  virtualized).
* The full accessibility pass — WP-4.11.

## Target paths
* `web/` (column virtualization wrapper integrated with the board)
* `web/` tests (virtualization behavior, bounded render counts, keyboard reach)
* WP changelog entry

## Acceptance criteria
- [ ] With a 500-card fixture, rendered (mounted) card elements per column are bounded
  to the visible window plus overscan — far fewer than 500 total — and the board
  stays responsive per Section 13.4 (FR-WEB-01 non-functional target).
- [ ] Scroll position and card identity are keyed by task id; live patches
  (MT-4.3-05) update cards without resetting scroll or remounting the column.
- [ ] Keyboard navigation can still reach off-screen cards (focus moves them into
  view) — Section 13.4 keyboard requirement not regressed by windowing.
- [ ] Loading/empty/error states from MT-4.3-01 keep working with virtualization
  enabled (Section 20.3 states preserved).
- [ ] First load stays within the Section 13.4 target on LAN as previously measured —
  virtualization adds no blocking cost (record the measurement).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web suite filtered to virtualization (for example `npm test -- -t
virtual`) and confirm: 500-card fixture renders a bounded number of card nodes,
scroll/patch reconciliation keeps scroll position, and keyboard reach works; then the
full web suite stays green.

## Attachments
* [Section 13.4 — Non-functional targets](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.2 — Board component](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.3 slices](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Virtualization + drag-and-drop (WP-4.4) is a classic conflict (dragged items leave
  the window) — land the virtualization seam cleanly here and flag the integration
  explicitly for WP-4.4 rather than deferring discovery.
* "Responsive" in Section 13.4 has no numeric budget — define the measurement you
  will show (mounted-node count, sustained interaction during event bursts) in the
  test so acceptance is objective; if a number is required, propose it as OQ-xx
  instead of inventing a plan value.
