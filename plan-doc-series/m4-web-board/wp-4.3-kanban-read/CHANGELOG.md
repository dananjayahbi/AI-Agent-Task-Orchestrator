# WP-4.3 — Kanban board (read) with realtime: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).
All commands run from the repository root: `npm --prefix web run
lint|typecheck|format:check|test|build`; the full battery is green
(141 tests across 17 files, including the 96 pre-existing WP-4.1/4.2
tests) and `npm --prefix web run check:api` reports an empty diff against
`schemas/openapi.yaml` (no backend contract change this round).

## Unreleased

- **MT-4.3-01** — Six board columns mapped to canonical states
  (Sections 8.1/G-01, 13.1/13.2; FR-WEB-01). `lib/board/states.ts` owns
  the six canonical machine values in the Section 8.1 diagram order
  (`draft → pending → in_progress → to_be_audited → in_human_review →
  completed`) with presentation-only labels; the value list is derived
  from the generated `StateEnum` and guarded **both ways** at compile
  time (`satisfies` + coverage assertion) so a schema change is a build
  failure here, never a silent mis-grouping (MT risk note). Grouping
  (`groupTasksByState`) keys columns by machine value; the board page
  (`app/(app)/projects/[pid]/board/`) renders `<Board>` through
  `components/board/board.tsx` + `board-column.tsx` with the Section 20.3
  state separation — `LoadingState`, catalog-mapped `ErrorState` with
  retry, and an empty state whose copy distinguishes "no tasks in this
  project" from "no tasks match the current filters" (filter-driven, so a
  live patch that empties the cache cannot mislabel the project as
  empty). Data flows through the generated client only (`listTasks`,
  cursor-followed by `fetchAllPages`, `page_size=100` — NFR-11).
  Merge-pending stays a sub-status badge on `to_be_audited`/
  `in_human_review` cards ("approved, merging", Section 8.1 note) — the
  suite asserts exactly six columns and no seventh. **Decision (MT risk
  note):** column order = the Section 8.1 diagram order; reordering later
  is a presentation-only change. **Tests:** `tests/board/board-columns
  .test.tsx` (7) — order/keys, grouping + generated-client transport,
  badge without a seventh column, loading, catalog error copy without raw
  server text + retry recovery, project-empty state, heartbeat-only
  stream tolerance.

- **MT-4.3-02** — Task card (Sections 7.2, 8.6, 13.2; FR-WEB-01).
  `components/board/task-card.tsx` renders exactly the Section 13.2 list:
  id, title, priority chip, worker badge with lease countdown, percent
  bar, attachment count, stalled/escalation marker. Stalled follows the
  Section 8.6 definition verbatim via `lib/board/stalled.ts` (no
  checkpoint within the policy's `stalled_after_minutes` while the lease
  is still valid; the never-checkpointed window measures from the claim;
  an expired lease is T5 territory, not "stalled") — policy value comes
  from `GET /projects/{pid}/policy` with the documented Section 7.2
  default (20 min) as fallback. The lease countdown
  (`lib/board/lease.ts`) is display-only. Tick economy (MT risk note):
  one module-level shared timer (`lib/board/use-now.ts`) drives every
  countdown/marker; windowing (MT-4.3-06) bounds how many cards re-render
  per tick. Priority chips cover exactly the four Section 7.2 values via
  cva + MT-4.1-04 theme tokens. Explicit unknowns (risk note): percent
  `null` renders an indeterminate bar labelled "Progress unknown" — never
  a fake 0 %; the attachment count renders "–" because the tasks list
  contract carries no count (**OQ-4.3-01** below). Unclaimed tasks show
  no worker badge. **Tests:** `tests/board/task-card.test.tsx` (10) —
  seven elements, stalled/not-stalled/lease-expired/never-checkpointed
  variants, claimed vs unclaimed, four priorities, unknown percent,
  escalation marker with accessible review reason, countdown formats.

- **MT-4.3-03** — Board filters, search and archive toggle (Sections
  7.2, 8.2 T19, 13.1; FR-WEB-01). `lib/board/filters.ts` binds strictly
  to the tasks-list contract parameters exposed by the generated client —
  `priority` (single value), `state` (repeated param, canonical order
  normalized so equal selections share one query key), `include_archived`
  — nothing invented (NFR-11); absent filters are omitted, letting the
  server's documented defaults apply. Archive defaults OFF (T19) and the
  client predicate hides archived rows even if a response includes them.
  **Search is client-side** over the loaded board set (id/title
  substring) because the contract has no server search — recorded as
  **OQ-4.3-01**, not silently faked as a server semantic. The
  server-filter half lives in the react-query key
  (`queryKeys.boardTasks`) so toggles refetch through the cache, with
  `placeholderData: keepPreviousData` so the toolbar never unmounts
  mid-interaction (first load still shows `LoadingState`; refetch errors
  under a new key map to canonical catalog copy). Search composes as a
  pure client predicate; the filtered-empty state (with a clear-filters
  action) stays distinct from loading and error. **Tests:**
  `tests/board/board-filters.test.tsx` (6) — T19 default against a
  deliberately filter-ignoring server (proves the client belt too),
  toggle reveal + request params, priority server-side + search
  composition without extra requests, state param shape, clear-to-default
  (cache-served, Section 13.3), catalog-mapped refetch errors.

- **MT-4.3-04** — SSE stream hook with reconnect and status (Sections
  9.6, 13.3; FR-WEB-05). `lib/stream/use-event-stream.ts` subscribes via
  the generated `GET /events/stream` operation only (NFR-11; imported
  through the `@/lib/api` barrel so the runtime transport config —
  same-origin base, credentialed fetch — applies). It owns the
  reconnect loop with exponential backoff (base 1 s, capped 30 s;
  progress resets the ladder) and disables the generated client's
  internal retry (`sseMaxRetryAttempts: 1`) so exactly one loop is the
  backoff authority. Resume uses the **`Last-Event-ID` header** (the SSE
  standard; the backend accepts header *or* `last_event_id` query per
  MT-1.10-03 — recorded per the MT risk note; the header passes through
  the generated client without inventing a query parameter the schema
  does not expose). Heartbeat comment lines (`: heartbeat`) carry no
  `data:` line, so the parser skips them — tolerated without resetting
  event state or triggering reconnects. Status `connecting → open →
  reconnecting → open` (and `closed` on unmount) is exposed for the
  board's visible indicator (`components/board/stream-status.tsx`);
  since the SSE parser surfaces only data frames, `open` registers at the
  first parsed envelope after (re)connect. Only Section 9.6 catalog
  types are forwarded (`lib/stream/event-catalog.ts`, compile-time
  coverage guard); unknown types are ignored but still advance the
  resume position so replays never re-deliver them. The hook delivers
  typed envelopes only — zero cache mutation here (separation for
  MT-4.3-05). **Tests:** `tests/stream/event-stream-hook.test.tsx` (7) —
  project filter + delivery, heartbeat tolerance, failed-stream and
  clean-end reconnects carrying `Last-Event-ID` with in-order replay,
  status transitions, catalog gating + resume advancement, unmount
  abort with no further connects.

- **MT-4.3-05** — Query-cache patching from stream events (Sections
  7.2, 9.6, 13.3; FR-WEB-05; Section 19 WP-4.3 acceptance). The pure
  reducer `lib/board/patch.ts` plus the subscription
  `lib/queries/board-live.ts` turn envelopes into targeted cache writes.
  **Patch-vs-invalidate table** (MT risk note — backend payloads are
  minimal by WP-1.9 design): `task.transitioned` and `task.lease_expired`
  are **pure in-place patches** (state+version from `to_state`/
  `task_version`; lease/worker fields cleared per Section 8.3 invariant
  1) — zero network, the acceptance case; `task.lease_expiring` patches
  `lease_expires_at`; `task.checkpoint` patches `last_checkpoint_at` and
  the percent map (`lib/queries/checkpoint-progress.ts` — the tasks list
  carries no percent, so the stream is the card's percent source);
  `task.created|updated|claimed|released`, `audit.passed` and `merge.*`
  schedule a **targeted `GET /tasks/{id}` refetch** (never a board-list
  refetch) because their payloads omit row data — merged filter-aware
  (insert/keep/remove) with in-flight dedupe. Stale protection: an event
  with an older `task_version` than the cache is ignored outright; every
  patch is idempotent, so MT-4.3-04 replays apply missed events exactly
  right the second time. Filter-awareness: patched results are
  re-evaluated against the active server filters (a task that leaves the
  filter disappears; a refetched row that fails the filter is not
  inserted). Out-of-scope catalog types (`project.*`, `attachment.*`,
  `review.*`, `agent.*`, `system.alert`, remaining `audit.*`) are
  ignored without breaking the stream. **Tests:**
  `tests/board/cache-patching.test.tsx` (10) — the acceptance case with
  explicit no-refetch assertions (list calls stay at 1, zero
  single-task fetches), stale-version ignore, idempotent replay,
  filter-aware removal, created→targeted-refetch insert (and non-insert
  when filtered), checkpoint percent without any fetch, claimed move +
  one-row worker refresh, lease-expiry lease clearing, out-of-scope
  events ignored. End-to-end latency: patching is synchronous after
  frame delivery, far inside the Section 19 2 s budget (server-side
  post-commit publishing measured at integration per the MT risk note).

- **MT-4.3-06** — Column virtualization for 500-card boards (Sections
  13.2, 13.4; FR-WEB-01). `components/board/virtual-list.tsx` is a
  dependency-free windowed list (MT risk note: no new heavy dependency;
  fixed-row-height model recorded, variable heights flagged for
  WP-4.11): only the visible slice plus overscan (3) mounts, items key by
  task id so live patches reconcile in place without scroll resets or
  column remounts, and the container self-measures (rAF + resize) with a
  480 px fallback for unmeasured environments (SSR/jsdom). Keyboard
  navigation cannot dead-end (Section 13.4): Arrow/Home/End move a roving
  focus target, scrolling it into the window before focusing; blur resets
  it. Column headers keep reporting full (unwindowed) counts.
  **Objective "responsive" measure** (MT risk note): with a synthetic
  500-task fixture, mounted card nodes stay bounded (< 100 total vs 500
  tasks), scrolling windows the list, patches during scroll keep
  `scrollTop`, and the MT-4.3-01 loading/empty/error states keep working.
  First-load budget (Section 13.4 "under 3 s on LAN") is unchanged by
  virtualization — it adds no fetch or blocking cost to the load path
  (render-time only); the LAN measurement itself stays an integration
  activity with WP-4.11's performance report. **Tests:**
  `tests/board/virtual-columns.test.tsx` (5).

### Open questions recorded by this WP

- **OQ-4.3-01 (server search):** `GET /projects/{pid}/tasks` exposes no
  search/text parameter, so the board's search box filters the loaded set
  client-side (documented in the UI). If Section 13.1's "search" must
  scale beyond the loaded board, the backend contract needs a search
  parameter — a Section 9.2 change, raised here rather than faked.
- **OQ-4.3-02 (card data fields):** the tasks list contract carries
  neither an attachment count nor the latest checkpoint percent (both in
  the Section 13.2 card list). Percent is recovered from `task.checkpoint`
  events during the session; the attachment count shows an explicit "–"
  until the contract gains the field (or WP-4.6's detail view).
