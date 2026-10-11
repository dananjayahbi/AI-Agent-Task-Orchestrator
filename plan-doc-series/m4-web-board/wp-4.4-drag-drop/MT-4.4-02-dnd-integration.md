# MT-4.4-02 — Integrate drag-and-drop onto the board

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.4-02 |
| Title | Integrate drag-and-drop onto the board |
| Parent WP | WP-4.4 — Drag-and-drop with validation (Milestone M4) |
| Requirements | FR-WEB-02 |
| Priority | M |
| Dependencies | MT-4.4-01 (allowed-move map), WP-4.3 (board, cards, columns), WP-4.1 (typed API client) |
| Parent sections | 13.2, 13.4, 19 (WP-4.4), 20.4, 20.5 |

## Context
WP-4.4's goal: "Move rules from parent plan 13.2 with optimistic updates
(FR-WEB-02)." With the map defined (MT-4.4-01), this task wires real dragging onto
the WP-4.3 board: cards become draggable, the six canonical columns become drop
targets, every drag consults the map before anything is sent, and rejected drops
show the map's explanation with the card staying put. Section 13.4 adds the keyboard
navigation obligation for the board and dialogs — the drag feature must not become a
mouse-only island.

## Inputs / Prerequisites
* MT-4.4-01 — the allowed-move map (verdicts + explanations).
* Parent plan Section 13.2 — rules and "the server re-validates" posture;
  Section 13.4 — keyboard navigation target.
* WP-4.3 — board columns (MT-4.3-01), task cards (MT-4.3-02), query-cache patching
  (MT-4.3-05) that applies event patches.
* WP-4.1 — generated typed API client used for the actual transition/review calls
  (made by MT-4.4-03/04, not here).
* Section 9.2 endpoints — `POST /tasks/{id}/transition` (publish/unpublish) and
  `POST /tasks/{id}/review` (approve/request_changes/reassign) as the eventual
  targets; this task routes `allowed` moves to a callback consumed by MT-4.4-04.

## Scope (in)
* DnD wiring on the WP-4.3 board: task cards draggable; the six canonical-state
  columns are drop targets; drag hover shows allowed/rejected affordances per the
  map.
* Pre-flight consultation: before a drop resolves, the map decides — `allowed`
  invokes the move callback (later wired to optimistic update, MT-4.4-04), `dialog`
  hands off to the dialog layer (MT-4.4-03), `rejected` shows the map's explanation
  and cancels the move with no network call.
* Visual and announcement feedback: rejected drops explain why (agent/system-owned
  states), cards never disappear from their column on rejection, and the outcome is
  perceivable without color alone (accessibility posture of Section 13.4).
* Keyboard path: the board's move interactions are reachable via keyboard (Section
  13.4) — a non-drag affordance that routes through the same map and callbacks, so
  drag is an enhancement, not the only channel.
* Component tests: successful allowed drag invokes the callback with (task, target);
  dialog verdict opens the dialog layer instead of moving; rejected drag shows the
  explanation and performs no call; keyboard move parity.

## Out of scope
* The map itself — MT-4.4-01.
* Dialog content and confirmations — MT-4.4-03.
* Optimistic update, server calls, rollback — MT-4.4-04.
* Server re-validation — WP-1.5/WP-3.6 (always enforced there).
* Read-only board behaviors (filters, virtualization, SSE) — WP-4.3.

## Target paths
* `web/` — board drag-and-drop integration (components/hooks)
* `web/tests/` — DnD component tests
* WP changelog entry

## Acceptance criteria
- [ ] Cards drag across the six canonical columns, and every drop is routed through
  the MT-4.4-01 map — no path bypasses it (Section 13.2).
- [ ] Rejected drops (into/out of `in_progress`, `to_be_audited`, and other
  disallowed pairs) show the map's explanation, leave the card in place, and make no
  network call (WP-4.4 acceptance: "disallowed moves blocked client-side with
  explanation").
- [ ] `allowed` verdicts invoke the move callback (consumed by MT-4.4-04);
  `dialog` verdicts open the dialog layer (MT-4.4-03) instead of moving the card.
- [ ] Move interactions are keyboard-reachable per Section 13.4, with identical
  map consultation.
- [ ] The board keeps the 500-card responsiveness target — DnD wiring does not defeat
  WP-4.3's virtualization (Section 13.4).
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`npm test -- -t drag-drop` — assert allowed/dialog/rejected routing through the map,
explanation on rejection with zero network calls, keyboard parity, and virtualized
board compatibility; then the full web suite stays green.

## Attachments
* [Section 13.2 — Key components](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.4 — Non-functional targets](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Adding a DnD library is a dependency decision — pick one that supports keyboard
  alternatives and does not break virtualization; if no library satisfies Section
  13.4, raise it as a decision rather than shipping a mouse-only board (Section 20.1,
  no hidden decisions).
* Drag state and server state must not be conflated: the card visually previews the
  move only through the MT-4.4-04 callback — never mutate the query cache here.
* Touch devices (phone-browser fallback, Section 13.4) behave differently under DnD —
  verify the rejected/allowed affordances still work, or route touch through the
  keyboard path.
