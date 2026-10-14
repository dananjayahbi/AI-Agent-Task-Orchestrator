# WP-4.9 — Agents panel: changelog

## Unreleased

- **MT-4.9-01 — agent sessions list (done).**
  `web/components/panels/agents-panel.tsx` (project context),
  `sessions-view.tsx` (active/ended sections + states), and
  `session-row.tsx` (Section 9.2 fields + task/lease join) replace the
  `/agents` placeholder; `web/lib/queries/agent-sessions.ts` owns the
  data. **Recorded reading (MT risk note, endpoint gap):** Section 9.2
  publishes no owner-facing `GET /agent-sessions` (the Sessions row is
  bridge `POST`-only) and the backend never emits `agent.session_*`
  (only the catalog defines them), so active rows are derived from
  canonical lease state — every `in_progress`/`to_be_audited` task with
  `worker_session_id` (Section 8.3 invariant 1) joined through
  `worker_agent_id`/`claimed_role`/`lease_acquired_at`/
  `last_checkpoint_at`/`lease_expires_at` — and recently-ended rows are
  reconstructed from the `GET /events` history (claim → release/expiry/
  lease-clearing transitions; `ended_at` = the closing envelope's
  `occurred_at`). Session envelopes are handled defensively for when the
  backend starts emitting them: `session_started` revives/creates a row,
  `session_ended` closes it, and both are folded into the row even in
  history. **Contract-gap fields:** `client_name`, `capability` and
  `transport` exist only on the server AgentSession row — with no read
  endpoint they render as "–", never invented values; the row's liveness
  flag records whether explicit session events or lease-derived signals
  define "active" (a lease-derived row ends when its last lease does; a
  session-observed row ends only on `session_ended`). **Live, not a
  poll (AC 2):** `useAgentSessionsLive` subscribes through the WP-4.3
  stream hook — `session_*`/`task.released`/`task.lease_expired` patch
  the cache purely (replay-safe: rows keyed by session id, joins by
  task id), while `task.claimed`/`audit.claimed` (data omits worker
  columns) and lease-affecting transitions schedule one deduplicated
  single-task `GET /tasks/{id}` refetch — never a list refetch. Ended
  list capped at 50 newest (RISK-13) and history paged through the
  shared bounded cursor helper. Project selection follows the
  MT-4.2-01 stored-project rule (derived during render: explicit →
  stored → first; the effect only persists), and `SessionsView`
  remounts per project so query/stream state resets.
  Tests: `web/tests/panels/agents-sessions.test.tsx` (8 — fixture
  derivation + gap dashes, history-ended separation, live
  started/ended, claim join via exactly one targeted refetch with the
  list unfetched, pure release patch under a replayed frame, separated
  empty states, catalog-only error copy, project default/switch).
- **MT-4.9-02 — lease countdown displays (done).**
  `web/components/panels/lease-countdown.tsx` is the reusable display:
  remaining time from server-issued `lease_expires_at`, ticked by the
  shared module timer (`useNow` — one interval for every subscriber,
  the MT's 500-card regression guard), formatted with the board
  badge's `formatLeaseRemaining` so both surfaces read identically;
  no lease → renders nothing (Section 20.3), past deadline →
  "expired" (never a negative value). **P7 server-clock alignment
  (recorded approach):** `web/lib/server-clock.ts` anchors an offset
  from each live envelope's `occurred_at` minus the local receive
  time, re-anchoring on every event; countdowns re-render immediately
  on a new anchor (`useSyncExternalStore`) and tick between anchors.
  Before the first envelope the offset is 0 (client tick against the
  server's deadline); history envelopes are deliberately not anchors
  (age would masquerade as skew), and latency biases the server at
  most one one-way delay "behind". **Live updates (AC):** the MT-4.9-01
  stream seam now also notes the anchor on every event, patches
  `task.lease_expiring` purely (sets the Section 9.6 80% warning flag
  and re-arms `leaseExpiresAt` from the envelope's own server field),
  and schedules the targeted single-task refetch for `task.checkpoint`
  (whose data omits the extended deadline) — claim resets already came
  through the claim refetch; release/expiry clear the join, so the
  badge disappears. Warning state = the `lease_expiring` push OR the
  computed 80%-elapsed threshold (elapsed/total from
  `lease_acquired_at`→`lease_expires_at`, same instant the server's
  notifier fires); a refetched row resets the flag and the computed
  arm takes over. Display mirrors server fields only — the Section 8.6
  hard cap is never re-derived client-side.
  **Board badge (AC 1):** the Section 13.2 worker badge with countdown
  already exists on cards from MT-4.3-02 (`task-card-lease`) and is
  left untouched (concurrent agent owns `components/board`); this
  deliverable adds the Agents-route countdown and the shared P7 anchor
  module a future board wiring can consume.
  Tests: `web/tests/panels/lease-countdown.test.tsx` (7 — no-lease
  → nothing, initial + expired under a frozen clock, P7 re-anchor via
  a live envelope, checkpoint extension via exactly one targeted
  refetch, computed 80% warning, `lease_expiring` warning + deadline
  re-arm, clearing on `task.lease_expired`).
- **MT-4.9-03 — stalled-task indicators (done).**
  `web/components/panels/stalled-indicator.tsx` marks a join stalled
  through the SAME Section 8.6 derivation the board card uses —
  `isTaskStalled` in `web/lib/board/stalled.ts`, whose parameter
  widened to `Pick<Task, state | lease_expires_at | last_checkpoint_at
  | lease_acquired_at | created_at>` (surgical, backward-compatible:
  board cards still pass whole tasks — its tests stay green) so the
  Agents view and the pre-existing board marker
  (`task-card-stalled`, MT-4.3-02, untouched — concurrent agent owns
  `components/board`) can never disagree. **Recorded readings:**
  (1) `last_checkpoint_at` semantics follow what WP-1.8 stores — the
  server moves the field for every *accepted* checkpoint kind
  (`store_checkpoint` is unconditional; rejections write nothing), so
  the client mirrors the field exactly as the MT's scope instructs
  ("follow what WP-1.8 stores") and as the board already does; lease
  *extension* kind-gating (`_kind_extends_lease`) is a different
  question and is not re-derived. (2) The shared derivation reads
  `state === in_progress` with a still-valid lease (coder-lease
  reading of 8.6 from MT-4.3-02) — stall ≠ expiry, so an expired
  lease never shows the marker. **Threshold:** read live from
  `usePolicyQuery` (`stalled_after_minutes`) with the documented
  default 20 only as load-failure fallback — a mid-view policy change
  reaches the indicator through the query cache; nothing hard-codes
  20. **Live:** a progress `task.checkpoint` refetch clears the
  marker immediately (MT-4.9-02's targeted seam), lease end removes
  the join (row shows ended), and `system.alert` (Section 9.9
  detector) triggers a targeted task refresh covering stream misses —
  display stays client-computed per 8.6 (UI-only; the detector is
  not emitting yet), and no alert-shaped state or stall reason code
  is invented (20.5). Accessible label: visible "Stalled" text with
  the threshold in the tooltip (13.4).
  Tests: `web/tests/panels/stalled-indicators.test.tsx` (6 —
  before-threshold, after-threshold with lease/countdown co-existing,
  custom policy threshold, checkpoint clearing with one targeted
  refetch, lease-end clearing, `system.alert` intake refresh).
