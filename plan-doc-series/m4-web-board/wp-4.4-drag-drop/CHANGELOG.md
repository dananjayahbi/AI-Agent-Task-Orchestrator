# WP-4.4 — Drag-and-drop with validation: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).
All commands run from the repository root: `npm --prefix web run
lint|typecheck|format:check|test|build` — all green (160 tests across 19
files, including the 141 pre-existing WP-4.1/4.2/4.3 tests) and
`npm --prefix web run check:api` reports no drift against
`schemas/openapi.yaml` (no backend contract change this round).

## Unreleased

- **MT-4.4-01** — Allowed-move map, client-side (Sections 13.2, 8.1,
  8.2 T2/T3/T15/T16; FR-WEB-02; ADR-010). `lib/board/move-map.ts` is the
  pure, side-effect-free single source of truth for what a move may do:
  canonical source → canonical target → exactly one verdict. `allowed`
  covers exactly `draft` ⇄ `pending` (publish/unpublish); `dialog` maps
  `in_human_review` → `completed` to `approve_merge` and
  `in_human_review` → `pending` to `request_changes` (never plain
  moves); everything else is `rejected` with one of three stable,
  operator-phrased explanations — any drop into or out of
  `in_progress`/`to_be_audited` names them agent/system-owned, plus
  same-column and not-Owner-valid copy (nothing is implicitly allowed;
  a straight drag toward `completed` is rejected). Keys are canonical
  snake_case states only (display labels never appear in the map), the
  full 6×6 matrix has no undefined cell, and the map stays advisory UX —
  the server re-validates every transition (Section 13.2 posture). One
  fix during verification: the agent-owned pair guard's tuple
  `.includes()` was narrowed so `typecheck` accepts any `BoardState`
  argument. **Tests:** `tests/board/allowed-move.test.ts` (11) —
  table-driven full-matrix verdicts, one spot assertion per Section 13.2
  bullet, canonical-key/label-leak discipline, stable non-empty
  explanations, purity/determinism.

- **MT-4.4-02** — Drag-and-drop integrated on the board (Sections 13.2,
  13.4; FR-WEB-02). Native HTML5 drag-and-drop with **no new
  dependency** (same discipline as MT-4.3-06): cards become draggable
  inside their column, the six canonical columns are drop targets, and
  every interaction — `dragover`/`drop` and the keyboard/touch path —
  routes through one funnel (`routeMove` in `lib/board/move-routing.ts`)
  that consults the MT-4.4-01 map and dispatches exactly one handler:
  `allowed` → the `onMove(task, target, action)` seam carrying the
  versioned task and canonical target for the documented Section 9.2
  `POST /tasks/{id}/transition` (`{ to_state, version }`); `dialog` →
  the `onDialog(task, dialog)` seam (T15/T16 hand-off — the card never
  moves on a dialog verdict); `rejected` → the board's `role="status"`
  aria-live notice showing the map's explanation, with the card left in
  place, no query-cache mutation, and **no network call**. Drag hover
  shows a per-column text affordance from the map (`column-drop-hint-*`
  with `data-verdict`, dashed outline for rejected) so meaning never
  rides on color alone; hints clear on `dragleave`/`dragend`, and a
  stray `dragover` after the session ends routes nothing. Keyboard and
  touch parity (Section 13.4): every card inside a Board exposes a
  native "Move" button opening the destination-picker dialog
  (`move-destination-dialog.tsx` — Radix focus trap, Escape, focus
  return) listing all six columns with their verdicts; picking calls the
  same `route` a drop would, so drag is an enhancement, not the only
  channel. Cards rendered outside a Board are unchanged — no `draggable`,
  no button. DnD adds no fetches and leaves the virtualized window
  bounded. **Tests:** `tests/board/drag-drop.test.tsx` (8) — allowed
  drop → callback with contract payload (id/`version`/target/action) and
  zero network calls; dialog verdicts hand off without moving the card;
  agent-owned rejections into and out of `in_progress` with the stable
  explanation and the card still in its column; straight-to-completed
  and same-column drops rejected; keyboard-picker parity including a
  rejected pick; hover-affordance lifecycle; explicit deferred-seam
  notices (never a silent no-op); virtualization intact with DnD wired.

### Deferrals (recorded per roadmap §4a rule 1)

- **MT-4.4-03 (deferred):** approve-and-merge and request-changes/reassign dialogs wait on `POST /tasks/{id}/review` (WP-3.6, Wave 8) — both `dialog` verdicts already route to the `onDialog` seam with mocked tests.
- **MT-4.4-04 (deferred):** optimistic update with rollback waits on MT-4.4-03 (dialog outcomes) and the transition endpoint — the `onMove` seam already carries `{task (with version), target, action}` with mocked tests.

### Endpoint gap — `POST /tasks/{id}/transition` is unowned in the schema

Section 9.2 documents `POST /tasks/{id}/transition` (publish/unpublish/
archive, Owner), but **`schemas/openapi.yaml` has no
`/tasks/{id}/transition` path** (deferred to WP-1.15) and no
`/tasks/{id}/review` (WP-3.6, Wave 8), so no generated typed model
exists (NFR-11). Following the dashboard-gap precedent (WP-5.6
CHANGELOG), MT-4.4-02 was delivered **behind the seam** with **mocked
consumer tests** targeting the documented contract (`{ to_state,
version }` for T2/T3 actions; T15/T16 dialogs); no backend code was
written from this WP (scope rule). The production board page passes no
handlers yet, so `allowed`/`dialog` verdicts resolve to an explicit
stable notice ("…not available on this board yet … the task stays in …")
instead of a silent dead end. **Recommendation:** when WP-1.15 adds the
path, regenerate the typed client (NFR-11), then wire MT-4.4-04's
optimistic sender to `onMove` and MT-4.4-03's dialog layer to
`onDialog` — each seam makes that a one-file change.
