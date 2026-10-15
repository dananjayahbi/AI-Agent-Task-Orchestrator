# WP-4.8 — Human review panel and queue: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).
All commands run from `web/`: `npx vitest run` (307 tests across 37
files green), `npx tsc --noEmit`, `npx eslint .`, `npx prettier --check .`
— all green; no backend/schema change (no `check:api` drift).

## Unreleased

- **MT-4.8-04 — live merge-status display (done).** One shared badge
  (`components/review/merge-status-badge.tsx`,
  `lib/review/merge-status.ts`) now carries the Section 7.2
  `merge_status` sub-status on every surface: the review panel header
  (hosts it while the task is in review), the task-detail header
  (takes over once the panel unmounts — e.g. `merged` after T17), the
  review-queue row, and the board card (which switched from its inline
  pending/merging-only span to the shared component and now also shows
  the T18 failure branch `conflict` / `failed`; `merged` stays off the
  card — the Completed column already states the outcome). Canonical
  value rides on `data-merge-status`, label is presentation
  (ADR-010): `merging` keeps Section 8.1's verbatim "approved,
  merging"; the other labels track the canonical names per the MT's
  risk note — `pending` reads "approved, waiting" per its scope
  wording, `conflict`/`failed` get destructive styling. **Recorded
  wording reconciliation:** the MT-4.4 approve dialog/notice copy
  still describes the phase with Section 8.1's umbrella phrase
  "approved, merging" (untouched — its tests pin it); the badge shows
  the finer-grained instant, both quoting plan text. Live: the queue
  sink (`lib/queries/review-queue-live.ts`) gained `merge.started` /
  `merge.succeeded` / `merge.failed` handling — one targeted refetch
  for rows the queue holds (a row that left review on the way is
  dropped by the same upsert); the board and detail sinks already
  routed merge.* to targeted refetches (WP-4.3), so the badge moves
  with the executor, and the approve response seeds `pending`
  optimistically on both board and detail caches (T15). Event gaps
  after a drop ride the stream hook's Last-Event-ID resume (MT-1.10
  contract) — the sink is frame-driven, replay-agnostic, and the
  reconnect catch-up is proven at component level. Manual-strategy
  projects (OQ-06) land completed/merged straight from the approve
  response — the display only ever shows what the row carries, never
  an invented "merging" phase. Tests:
  `tests/review/merge-status.test.tsx` (6) — full pending → merging →
  merged cycle across panel/header via fixture SSE frames, T18
  conflict branch (badge + `merge_conflict` reason + actions stay),
  reconnect catch-up from a replayed frame, queue-row badge live
  update + row drop, board-card failure badges + merged skip, and the
  manual-strategy approve (no phantom merging). `board-columns`'s
  pending-card assertion updated to the new label ("approved,
  waiting", `data-merge-status` pinned). Suite: **390 tests across 50
  files green** (362 baseline + 10 + 6 + 6 from this WP, plus 6 from
  the concurrent ops work sharing the tree); `tsc --noEmit`,
  `eslint .` and `prettier --check` clean on every file touched.

- **MT-4.8-03 — review actions: approve / request changes / reassign
  (done).** The panel's docked actions region
  (`components/review/review-panel.tsx`) now hosts the three Section
  11.5 actions wired onto the **existing** MT-4.4-03 dialogs and the
  shared `useReviewDecision` mutation — nothing rebuilt. Approve
  displays and binds the viewed resolution + version (WP-3.6 stale
  protection, T15's "a resolution must exist" guard now also disables
  the panel control itself with the reason); request changes keeps the
  dialog's mandatory-note guard and returns the task to `pending` with
  the note as `latest_feedback` (T16); reassign returns to `pending`
  without a note. Success surfaces the recorded decision with its
  `decided_via` channel from the response record (Sections 7.2/11.5 —
  no GET review-history endpoint exists in Section 9.2, so the POST
  response is the only record the UI can show) and states "merge
  pending", never "completed" (Section 8.1 / ADR-008).
  `lib/queries/review-decision.ts` extended additively: the mutation
  now applies the same optimistic / settle / server-truth discipline
  to the **task detail** cache row (`queryKeys.taskDetail`) so the
  panel moves exactly like the board entry; the detail optimistic
  patch is deliberately **approve-only** — a T16 state flip would
  unmount the panel hosting the in-flight dialog, so the detail row
  moves only when the server's verdict settles it (recorded). Board
  callers are unchanged (missing detail row = no-op); the conflict
  refresh copy was generalized to "The view now shows the server's
  current state." (still catalog-only, G-07; the pinned substring
  and every existing board assertion hold). VERSION_CONFLICT /
  TASK_STATE_CONFLICT keep the dialog open, announce the catalog
  copy and refetch the row to server truth — no blind retry;
  double-submit is guarded (panel controls + dialog buttons lock to
  the pending mutation). Tests:
  `tests/review/review-actions.test.tsx` (6) — approve request body
  (`{decision, version, resolution_id}`), merge-pending notice +
  `decided_via: web` record + settle to the response identity,
  request-changes note guard then `{decision, version, note}` and the
  return to Pending, reassign without a note, VERSION_CONFLICT
  (catalog copy only, dialog open, detail row refreshed to the newer
  server version), double-submit single-flight, T15 disabled-with-
  reason. Full suite green: 384 tests across 49 files (includes
  concurrent ops work in the shared tree); `tsc --noEmit`, `eslint .`
  and `prettier --check` clean on all files touched here.

- **MT-4.8-02 — review panel: reasons, rule table, evidence (done).**
  Supersedes the batch-9 deferral (MT-4.6-03 and the WP-4.7 diff
  viewer had already landed). `components/review/review-panel.tsx`
  mounts in the task detail (`task-detail.tsx`, only while
  `state === in_human_review`) with the Section 13.2 composition:
  escalation reason (friendly label **and** verbatim Section 8.4
  code), submission summary (attempt, branch@commit, execution
  summary, Section 9.7 authoritative diff stats straight off the
  resolution row), audit report (verdict / confidence / policy
  decision + auditor notes), the Section 9.4 **rule table** rendered
  from the persisted `policy_rule_results` rows
  (`lib/review/rule-results.ts` + `components/review/rule-table.tsx` —
  every R1–R9 row verbatim in plan order; a failing row's own
  persisted `review_reason` wins and the Section 9.4 mapping for that
  rule id fills in when absent; **no client-side rule math**, Section
  9.4 authority note), Section 10.5 **evidence** commands with exit
  codes + `lint_clean` (`lib/review/evidence.ts` +
  `components/review/evidence-block.tsx` — unknown evidence keys stay
  visible but collapsed behind a disclosure, never dropped or
  reinterpreted), the WP-4.7 `DiffPanel` (mount-on-open toggle) and
  the WP-4.6 `AttachmentViewer` **embedded, not re-implemented**, and
  a docked actions region left as the MT-4.8-03 placeholder.
  Distinct states (Section 20.3): loading, catalog-only error,
  no-submission (pre-audit escalation → reason + note) and
  no-audit-report (Section 8.5 path → summary + note) — neither
  degrades into an empty "all pass" table (MT risk note). **Seams
  recorded:** while in review the panel's attachments embed and the
  detail page's own Attachments section render side by side (one
  shared `taskAttachments` cache entry, one fetch); the MT's "review
  panel entry" OQ resolves as the queue rows' existing task-detail
  links — the panel is the destination content, row contract
  unchanged. No new endpoints (Section 9.2 resolutions/audit-reports
  only). Tests: `tests/review/review-panel.test.tsx` (10) — mount
  gating from the detail page, R2/R5 fail rows with verbatim reasons
  (persisted reason and Section 9.4 fallback mapping), all nine rule
  outcomes, evidence exit codes + lint flag + collapsed extras,
  summary/auditor fields, all 12 Section 8.4 reasons, no-report and
  no-submission degradation, catalog-only error copy, hosted
  diff/attachment embeds. Suite green at time of writing: 378 tests
  across 48 files (362 baseline + 10 here + 6 from the concurrent
  ops-dashboard work sharing the tree); `tsc --noEmit` and
  `eslint .` clean; `prettier --check` clean on all files this entry
  touches.

- **MT-4.8-01 — cross-project review queue page (done).**
  `app/(app)/review/page.tsx` replaces the placeholder with
  `components/review/review-queue.tsx`: every `in_human_review` task
  **across all projects** (Section 13.1), rows carrying project id,
  task id, title (a link), the priority chip, the canonical Section 8.4
  review reason (friendly label from `lib/review/review-reasons.ts`
  **plus the verbatim code** — Sections 20.4 item 5 / 20.5), age since
  escalation, and an entry action into the task detail (WP-4.6 contract;
  the richer panel link joins with MT-4.8-02). Sorting is **age-first
  as written** — longest-waiting row on top, Section 7.2/FR-TSK-05
  canonical priority order (urgent → low) as tiebreak, task id for a
  deterministic total order — recomputed on render so live inserts land
  in order (recorded per the MT risk note, which leaves precedence
  open). **Recorded data-source choice** (the MT risk note: no
  cross-project task query exists in Section 9.2): one
  `GET /dashboard/summary` call prefilters to projects whose
  `state_counts.in_human_review > 0`, and only those get a
  `GET /projects/{pid}/tasks?state=in_human_review` cursor fetch
  (page_size 100 clamp) — zero-count projects cost no task request
  (tested), so the fan-out is bounded by the prefilter rather than N;
  **age basis:** while a task sits in `in_human_review` nothing else
  writes its row, so the escalation transition's `updated_at` bump is
  the escalation timestamp (no transitions endpoint exists to read a
  dedicated one — same WP-4.6 OQ). Live maintenance
  (`lib/queries/review-queue-live.ts`, WP-4.3 pattern): the queue
  subscribes **cross-project** (`useEventStream`'s Section 9.6
  `project` filter is now optional — board/detail callers unchanged);
  `review.requested` upserts the row via one targeted, in-flight-
  deduplicated `GET /tasks/{id}` (the MT-3.9-01 payload carries no row),
  transition-shaped events leaving `in_human_review` remove rows as
  pure cache writes (no network), entering ones insert; the connection
  status is visible (`StreamStatusIndicator`) and rows stay readable
  while the stream reconnects (Section 13.3). Loading / "Nothing to
  review" empty / catalog-mapped error states are distinct
  (Section 20.3, G-07). Shared-file edits: `lib/queries/keys.ts`
  (`reviewQueue` key) and `lib/stream/use-event-stream.ts` (optional
  `project`); no nav change (the `/review` entry predates this WP).
  Tests: `tests/review/review-queue.test.tsx` (5) — cross-project
  listing with the zero-count prefilter proof and `state=in_human_review`
  request shape, age-first/priority-tiebreak order, friendly+verbatim
  reason, detail-route navigation, live add (single targeted GET) and
  live remove (zero network), empty and error states, stream-status
  visibility with rows intact.

### Open questions recorded by this WP

- **OQ: queue age precision.** Age uses `updated_at` (above); if a
  dedicated "entered `in_human_review` at" field or the transitions
  endpoint lands, the queue should switch to it.
- **OQ: review panel entry.** Resolved by MT-4.8-02: rows keep
  navigating to the task detail (row contract unchanged), where the
  review panel mounts automatically while the task is in
  `in_human_review`.
