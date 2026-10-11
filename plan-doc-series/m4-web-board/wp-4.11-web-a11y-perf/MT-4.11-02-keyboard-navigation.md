# MT-4.11-02 — Implement Keyboard Navigation for Board and Dialogs

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.11-02 |
| Title | Implement keyboard navigation for board and dialogs |
| Parent WP | WP-4.11 — Responsive, accessibility and performance pass (Milestone M4) |
| Requirements | NFR-13 |
| Priority | M |
| Dependencies | MT-4.11-01 (responsive layout stable), MT-4.3-01 … MT-4.3-06 (board and cards), WP-4.4 … WP-4.9 (task modal, review panel, dialogs) |
| Parent sections | 13.2 (Board, Task modal, Review panel), 13.4 (keyboard navigation target), 18 (Web UI row: accessibility checks on core flows), 19 (WP-4.11 second slice), 20.4, 20.5 |

## Context
Section 13.4 names the target verbatim: "keyboard navigation for the board and
dialogs". Section 18's Web UI row requires accessibility checks on core flows, and
NFR-13 sets WCAG 2.1 AA for core flows — keyboard operability is the load-bearing
part of that bar for a drag-and-drop-heavy board (FR-WEB-02): every owner-valid move
and every dialog action must be reachable without a mouse, while the server-side
re-validation stays untouched. This slice comes after layout (MT-4.11-01) and before
the contrast/label audit (MT-4.11-03), because focus order depends on stable layout.

## Inputs / Prerequisites
* MT-4.11-01 — responsive layout landed; DOM order and stacking settled.
* Parent plan Section 13.2 — Board (columns, cards, drag rules), Task modal
  (editors, criteria, scope, dependencies, dropzone) and Review panel (three actions,
  diff viewer) as the surfaces to make keyboard-operable.
* Parent plan Section 13.4 — the exact target statement.
* Parent plan Section 18 — Web UI layer: component tests plus end-to-end flows for
  drag-and-drop, create task, review (these flows must also pass by keyboard).
* Existing e2e/core-flow tests (WP-4.x) — extend rather than duplicate.

## Scope (in)
* Keyboard navigation for the board: reach columns and cards by keyboard, open a
  task, and perform each Owner-valid transition the drag rules allow (Section 13.2)
  through a keyboard path — with the same server re-validation and the same
  rejection explanations for agent/system-owned states.
* Keyboard operation for dialogs: task modal and the review/confirmation dialogs
  (approve-and-merge confirmation, request-changes dialog) — focus moves into the
  dialog on open, is trapped while open, and returns to the trigger on close; Escape
  closes where closing is safe (not mid-confirmation of a merge).
* Visible focus indication on interactive elements (WCAG 2.1 AA, NFR-13).
* Keyboard paths for the three review actions (approve, request changes, reassign)
  — the fallback review channel must work keyboard-only at any viewport (connects to
  MT-4.11-01's phone-fallback goal).
* Component and e2e tests for the keyboard paths of the core flows (board move,
  create task, review) per Section 18's Web UI row.
* Changelog note (Section 20.4 item 7).

## Out of scope
* Contrast and label fixes — MT-4.11-03 (this task may expose label gaps; log them
  there rather than fixing both concerns at once).
* Responsive layout work — MT-4.11-01; performance — MT-4.11-04.
* Changing drag-and-drop rules, server validation or optimistic-update rollback
  semantics (FR-WEB-02 unchanged — keyboard is an additional input path).
* Screen-reader semantics beyond what keyboard operation and labels require — the
  full audit is MT-4.11-03.

## Target paths
* `web/` — keyboard interaction modules/hooks for board and dialog focus management
* `web/` tests — component tests (focus order, trap, restore, board key paths)
* `web/` e2e — keyboard variants of board move, create task and review flows
  (Section 18 Web UI row)
* WP changelog entry

## Acceptance criteria
- [ ] Every Owner-valid board transition is performable by keyboard with identical
  validation and rejection messaging to the drag path (Section 13.2; FR-WEB-02).
- [ ] Task modal and review dialogs trap and restore focus correctly and are
  operable without a mouse (Section 13.4).
- [ ] Focus is visibly indicated on all interactive elements (NFR-13, WCAG 2.1 AA).
- [ ] The three review actions are completable keyboard-only (core flow per Section
  18 Web UI row).
- [ ] Keyboard e2e variants of board move, create task and review pass in CI
  (Section 20.4 items 1–2); changelog note added (item 7).

## Test command
`npm --prefix web test -- keyboard` for component focus tests, then the e2e keyboard
variants of the Section 18 core flows (board move, create task, review) — all pass
with no mouse input and no focus loss after dialog close.

## Attachments
* [Section 13.4 — Non-functional targets](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.2 — Key components (Board drag rules, dialogs)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing strategy (Web UI row)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* A keyboard "move" that bypasses the drag-rule explanations would diverge from
  Section 13.2's rejection semantics — implement it as the same transition request,
  only the input differs.
* Confirm dialogs and destructive actions need careful Escape handling — closing a
  merge confirmation on Escape is safe; completing it by accident is not; spell the
  rule out in the component test.
* If a third-party component (editor, diff viewer) has keyboard gaps, record them in
  the MT-4.11-03 findings list instead of forking the dependency here.
