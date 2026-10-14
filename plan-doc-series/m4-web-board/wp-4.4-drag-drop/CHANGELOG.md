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

- **MT-4.4-03 — approve-merge and request-changes/reassign dialogs
  (done; consumes WP-3.6's `POST /tasks/{id}/review`, landed Wave 8).**
  Both `dialog` verdicts now open a real confirmation instead of the
  deferred notice — the board renders `components/review/review-move-dialogs.tsx`
  by default (the `onDialog` seam still interceptable for tests).
  `approve-merge-dialog.tsx` (T15): surfaces task id, title, the
  Section 8.4 escalation reason (verbatim code + friendly label from
  `lib/review/review-reasons.ts`) and **the resolution being approved** —
  attempt/branch/commit loaded via the existing fetch-on-expand
  `useTaskResolutionsQuery`, newest attempt first; the submitted
  `resolution_id` binds to exactly that displayed row (Section 14.2 /
  MT-3.6-04 stale protection), and with no resolution the confirm button
  is blocked with T15's reason. Outcome copy is honest to Section 8.1:
  approval → "approved, merging" badge, never a completed column.
  `request-changes-dialog.tsx` (T16): note **mandatory** and validated
  client-side before any request (`noteValidationError` — the server
  guard stays the gate), `reassign` optional-note; both send the
  `version` the dialog saw. Both dialogs keep open on endpoint failure
  with catalog-mapped copy (Section 13.3; G-07 — raw envelope text never
  rendered), and are Radix-backed (focus trap, Escape, focus return —
  Section 13.4), reachable from the keyboard/touch destination picker.
  **Tests:** `tests/review/review-dialogs.test.tsx` (7) — dialog routing
  for both verdicts (card never moves on open), `resolution_id` + version
  binding to the *displayed* attempt, T15 no-resolution block, note
  guard before any request, reassign body, failure-stays-open with
  catalog copy + rollback refresh, keyboard-only path (picker → dialog →
  focus-in → Escape, zero calls).
- **MT-4.4-04 — optimistic update with rollback (done on the review
  path; the `allowed`-move sender stays behind the seam — endpoint gap
  below, unchanged).** `lib/review/optimistic.ts` (pure reducers) +
  `lib/queries/review-decision.ts` (one `useMutation`): `onMutate`
  patches the exact board cache entry the dialog opened from — T16
  previews the return to `pending` with lease fields cleared (Section
  8.3 invariant 1), T15 only flips `merge_status` to `pending`
  (merge-pending is a sub-status — the card never leaves the review
  column); the POST carries the version the dialog saw (Section 8.2 rule
  3). `onSuccess` settles from the response's post-transition identity
  (`VerdictTaskState`), re-applying the active server filters;
  `onError` rolls back to **server truth** — a targeted
  `GET /tasks/{id}` refresh (refresh beats restore-from-memory), with
  the snapshot only as fallback — and announces the catalog-mapped
  message; `VERSION_CONFLICT` and `TASK_STATE_CONFLICT` map to distinct
  copy plus a "board refreshed" note. Stream reconciliation: WP-4.3's
  cache patcher now routes `review.decided` to a targeted single-task
  refetch (the `task.claimed` precedent), so the confirming event and
  the HTTP response settle the same row idempotently in either arrival
  order — one writer after confirmation, no double move. The one
  behavior pin that changed with this wiring: `cache-patching.test.tsx`'s
  "out-of-scope events" fixture now uses `audit.escalated`
  (`review.decided` is in scope), and `drag-drop.test.tsx`'s
  deferred-seam test asserts the dialog opening instead of the
  hand-off notice (`moveSendUnavailableNotice` stays for `allowed`).
  **Tests:** `tests/board/optimistic-rollback.test.tsx` (5) — instant
  move before the response, event-before-response and response-after
  settlement with no oscillation, approve staying in review, both
  conflict codes rolling back to server truth with distinct messages,
  filters intact. Full battery: 307 passed (37 files); `tsc --noEmit`,
  `eslint .`, `prettier --check .` green.

### Deferrals (recorded per roadmap §4a rule 1)

- **MT-4.4-03 (superseded historical note):** approve-and-merge and request-changes/reassign dialogs wait on `POST /tasks/{id}/review` (WP-3.6, Wave 8) — both `dialog` verdicts already route to the `onDialog` seam with mocked tests. **Superseded: delivered above once WP-3.6 landed the endpoint; authoritative status is the bold entry under `## Unreleased`.**
- **MT-4.4-04 (deferred):** optimistic update with rollback waits on MT-4.4-03 (dialog outcomes) and the transition endpoint — the `onMove` seam already carries `{task (with version), target, action}` with mocked tests. **Partially superseded: the dialog-driven optimistic/rollback path is delivered above; the `allowed`-move sender still waits on the transition endpoint (below).**

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
