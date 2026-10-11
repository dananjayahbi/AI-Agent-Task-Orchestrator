# MT-4.4-01 — Define the allowed-move map (client-side)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.4-01 |
| Title | Define the allowed-move map (client-side) |
| Parent WP | WP-4.4 — Drag-and-drop with validation (Milestone M4) |
| Requirements | FR-WEB-02; ADR-010 |
| Priority | M |
| Dependencies | WP-4.3 (board columns mapped to canonical states), WP-1.5 (canonical state machine) |
| Parent sections | 13.2, 8.2, 8.1, 19 (WP-4.4), 20.4, 20.5 |

## Context
Section 13.2 fixes the drag-and-drop rules (FR-WEB-02): "the client only allows
Owner-valid moves, and the server re-validates." The rules verbatim: `draft` ⇄
`pending` allowed (publish/unpublish); `in_human_review` → `completed` opens an
approve-and-merge confirmation (not a plain move); `in_human_review` → `pending`
opens the request-changes/reassign dialog; dropping into `in_progress` or
`to_be_audited`, or out of them, is rejected with an explanation (agent/system-owned);
optimistic UI with rollback on `VERSION_CONFLICT` or `TASK_STATE_CONFLICT`. The board
columns map 1:1 to canonical states (Section 13.2, WP-4.3). This task authors the
pure, client-side map those rules become — one testable source of truth for what a
drag may do.

## Inputs / Prerequisites
* Parent plan Section 13.2 — drag-and-drop rules (verbatim).
* Parent plan Sections 8.1/8.2 — canonical states and Owner-valid transitions
  (T2 publish, T3 unpublish, T15 approve, T16 request changes/reassign); the map must
  mirror Owner-valid moves only.
* ADR-010 — canonical snake_case state values, not display labels.
* WP-4.3 (MT-4.3-01) — the six board columns keyed by canonical state.

## Scope (in)
* A pure, side-effect-free allowed-move map module: canonical source state →
  canonical target state → verdict of `allowed` (plain move) / `dialog`
  (`approve_merge` or `request_changes`), or `rejected` with a human-readable
  explanation string.
* Coverage of every Section 13.2 rule: `draft` ⇄ `pending` allowed;
  `in_human_review` → `completed` = `approve_merge` dialog; `in_human_review` →
  `pending` = `request_changes` dialog; any drop into or out of `in_progress` or
  `to_be_audited` = rejected with the agent/system-owned explanation; all other
  pairs rejected with a generic explanation (nothing implicitly allowed).
* Keys use canonical snake_case states only (ADR-010; display labels never appear in
  the map).
* Explanations phrased for the operator: why the move is not Owner-valid (e.g.
  agent-owned state), never a dead end — the rejected card stays put with the reason
  visible.
* Table-driven unit tests: every source×target pair has a defined verdict; spot
  assertions for each Section 13.2 bullet.

## Out of scope
* The drag interaction and DOM wiring — MT-4.4-02.
* The confirmation dialogs — MT-4.4-03.
* Optimistic update and rollback — MT-4.4-04.
* Server-side re-validation (always happens regardless of the map) — WP-1.5
  endpoint guards; the map is advisory UI, not authorization (Section 12.1 posture:
  server re-validates per Section 13.2).

## Target paths
* `web/` — allowed-move map module
* `web/tests/` — table-driven map tests
* WP changelog entry

## Acceptance criteria
- [ ] Every canonical state pair resolves to exactly one verdict
  (`allowed`/`dialog`/`rejected`), with no pair falling through undefined
  (Section 13.2).
- [ ] `draft` ⇄ `pending` is allowed; `in_human_review` → `completed` maps to the
  approve-and-merge confirmation; `in_human_review` → `pending` maps to the
  request-changes/reassign dialog (Section 13.2 verbatim).
- [ ] Moves into or out of `in_progress` and `to_be_audited` are rejected with an
  explanation naming them agent/system-owned (Section 13.2).
- [ ] The map is keyed by canonical snake_case states only (ADR-010), pure (no I/O),
  and used as the single client-side source of truth — no duplicated move logic in
  components.
- [ ] Table-driven tests cover the full pair matrix; lint/type/tests green
  (Section 20.4 item 2); changelog note added (item 7).

## Test command
`npm test -- -t allowed-move` — assert every state pair's verdict, each Section 13.2
bullet, canonical-state keys, and presence of rejection explanations; then the full
web suite stays green.

## Attachments
* [Section 13.2 — Key components (drag-and-drop rules)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.2 — Transition table](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The map is UX validation only — it must never be treated as the security boundary;
  the server re-validates every move (Section 13.2, FR-WEB-02's "server transition
  validation").
* Drift against Section 8.2: the map must not gain "convenient" moves the state
  machine forbids (e.g. dragging straight to `completed` from anywhere) —
  table-driven tests pin it to Section 13.2.
* Explanations are user-facing copy; keep them stable strings the tests assert, so a
  silent empty toast cannot satisfy "with an explanation".
