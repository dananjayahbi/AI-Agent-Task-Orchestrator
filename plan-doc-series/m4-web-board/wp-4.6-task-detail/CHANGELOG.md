# WP-4.6 — Task detail: checkpoints, resolutions, attachments: changelog

## Unreleased

- **MT-4.6-01 — task detail layout (done).**
  **Form: page** (Section 13.1 allows drawer or page — the choice is
  recorded here per the MT risk note). The route
  `/projects/{pid}/tasks/{taskId}` already existed as a placeholder
  (Section 13.1's conceptual route); making it a real page keeps the
  entry contract (task id parameter) trivially stable for WP-4.8's
  cross-links, gives deep-linkable reloads, and inherits the app
  layout's shared query cache so board → detail → board navigation
  never loses cached board state (Section 13.3 — the QueryClient lives
  in the layout, not the page; the round trip is tested).
  `web/components/task/detail/task-detail.tsx` hosts all seven
  Section 13.1 blocks: description, acceptance criteria, target scope +
  test command (all rendered from the task row), attachments
  (MT-4.6-04), checkpoint feed (MT-4.6-02), resolutions + audit
  reports and transitions history (MT-4.6-03 partial). The row loads
  through the generated client (`web/lib/queries/task-detail.ts`,
  NFR-11) with distinct loading / error states and catalog-only error
  copy (Section 20.4 item 5); `task.version` is surfaced on the root
  element (`data-task-version`) for optimistic-locking flows
  (Section 8.2 rule 3); `latest_feedback` renders when set (Section 7.2
  field — WP-3.6 starts populating it in Wave 8). The board card's
  title is now a real anchor into the detail route (keyboard +
  deep-link friendly, Section 13.4).
  Tests: `web/tests/task/task-detail.test.tsx` (7).
- **MT-4.6-02 — live checkpoint feed (done).**
  `web/components/task/detail/checkpoint-feed.tsx` renders
  reverse-chronological rows with exactly the Section 7.2 checkpoint
  fields: `message` (empty → explicit placeholder), `percent` (nullable
  — renders "Progress unknown", never a fake 0 %), `token_usage` (free
  JSON rendered defensively: primitive entries as `key: value` pairs,
  unnamed shapes collapse to nothing — no invented schema per the MT
  risk note), `kind` (progress/liveness/system labels) and the server
  `timestamp`. Data flow:
  `web/lib/queries/checkpoints.ts` owns one `{rows, nextCursor}` cache
  entry per task — the first page from `GET /tasks/{id}/checkpoints`
  (25/page, cursor-gated older pages on demand — RISK-13 bounded
  initial load), live rows via `task.checkpoint` events patched in by
  `patchCheckpointCaches` (pure `applyCheckpointEvent` reducer; zero
  refetch-per-event — the tests count checkpoint requests and assert
  none after live events). Replayed checkpoints after a reconnect
  dedupe on checkpoint id (Section 9.6 no-gaps/no-duplicates). The
  detail view's single SSE sink (`web/lib/queries/task-detail-live.ts`)
  routes checkpoint + attachment patches and a deduplicated targeted
  `GET /tasks/{id}` refetch for partially-described task events — one
  connection for the whole page (Section 13.3). Stream connection
  status (open/reconnecting/closed) shows as a live indicator without
  blocking the history already on screen. Auto-scroll: newest-at-top
  with a "Follow newest" toggle. **Recorded choice (MT risk note):**
  the toggle persists per user session via `sessionStorage`
  (`task-detail:checkpoint-follow`); account-level persistence would
  need a backend user preference that does not exist.
  Tests: `web/tests/task/checkpoint-feed.test.tsx` (13, including the
  pure reducer's dedupe/malformed-event behavior).
- **MT-4.6-04 — attachment viewer (done; depends on WP-1.13/1.14 ✅).**
  `web/components/task/detail/attachment-viewer.tsx`: the list shows
  every descriptor with size and all four `processing_status` values
  (uploaded/processing/ready/failed); `failed` rows show the
  pipeline's human-readable `failure_reason` (the contract field name
  — the plan text's `failure_detail` does not exist in
  `schemas/openapi.yaml`). Status moves live on
  `attachment.ready|failed` events through WP-4.5's
  `patchAttachmentCaches` reused verbatim in the detail sink — no poll
  (tested: zero list refetches). Images render the normalized bytes as
  a `data:` URL — the base64 comes back inside the JSON envelope
  fetched through the generated client's credentialed transport, so
  the browser never issues a cookie-less image request (the MT risk
  note's auth-aware path, §9.5/13.2). Image pane has OCR (`text_ocr`)
  and description tabs; the description tab hides entirely when the
  pipeline produced none (MT risk note). Documents page through
  `markdown` with `page_number`/`total_pages` honored — one page per
  request, never a whole-document preload (RISK-13; the tests assert
  the per-page request shape). All text-derived panes carry
  `untrusted-content-banner.tsx` (P10) and render inertly through the
  existing `MarkdownPreview`. Content queries
  (`web/lib/queries/attachment-content.ts`) cache per
  attachment × format × page. "Retry" is a content/status refetch —
  Section 9.2 exposes no manual reprocess endpoint, so none is
  invented. `ATTACHMENT_NOT_READY` / `ATTACHMENT_UNSUPPORTED_FORMAT`
  map to catalog copy only (Section 20.4 item 5).
  Tests: `web/tests/task/attachment-viewer.test.tsx` (11).
- **MT-4.6-03 — resolutions history (partial — see deferral).**
  **Available part done:** one entry per submission attempt rendered
  from `GET /tasks/{id}/resolutions` (newest attempt first; Section 7.2
  fields — branch, truncated commit sha, execution summary,
  `requires_human_attention` flag with `risk_justification`), diff
  stats shown are the backend's authoritative `{files, insertions,
  deletions}` from Section 9.7 — never recomputed client-side. Each
  entry pairs its audit report from `GET /tasks/{id}/audit-reports`
  (by `resolution_id`; verdict, confidence, auditor notes, policy
  decision); auditor-less flows render without one instead of erroring
  (Section 8.5). Fetch-on-expand keeps the first load light
  (Section 13.3/13.4 — the tests assert zero requests while
  collapsed).
  **Deferred — transitions history:** Section 9.2 publishes no
  `GET /tasks/{id}/transitions` endpoint and none exists in
  `schemas/openapi.yaml`, so the region renders an explicit
  endpoint-gap notice instead of inventing a contract (WP-4.4
  precedent: never a silent no-op, never a fabricated endpoint).
  Wire it when the backend exposes the endpoint.
  **Follow-up — `latest_feedback` population:** WP-3.6 (Wave 8) owns
  propagating review feedback into the task row's `latest_feedback`
  field; the detail view already renders the field when set
  (MT-4.6-01), so no web change is needed beyond the backend landing.
  Tests: `web/tests/task/resolutions-section.test.tsx` (6).
- **MT-4.6-03 — transition history completed (done; supersedes the
  deferral above).** The remaining half — the append-only transition
  record — now ships from the **published `GET /events` history**
  (Section 9.2 Events row, task filter; still no
  `GET /tasks/{id}/transitions` in the schema — the OQ below is answered
  by using a documented contract, never an invented endpoint): every
  state-machine dispatch writes both the Transition row and its Section
  9.6 event with the same `{from_state, to_state, reason_code,
  task_version}` payload plus `actor` and the server `occurred_at`
  (Section 8.2 rule 2), so `lib/queries/transitions.ts` collects the
  task-filtered cursor pages through the generated client (NFR-11),
  keeps only transition-shaped envelopes (checkpoints and
  `review.requested` payloads fail the gate), and serves them newest
  first. `components/task/detail/transitions-section.tsx` replaces the
  endpoint-gap stub: fetch-on-expand (Section 13.3/13.4 —
  `fetchAllPages`' page cap bounds long tasks, RISK-13), read-only rows
  with actor (type: ref), from → to state labels next to canonical
  keys, the reason code **verbatim** (Section 8.2 / 20.5) and the server
  timestamp; loading / empty / error states distinct with catalog-only
  copy. `latest_feedback` visibility was already delivered by MT-4.6-01
  and is unchanged.
  Tests: `web/tests/task/transitions-section.test.tsx` (4) —
  fetch-on-expand + `task=` filter shape, newest-first ordering with
  verbatim reason codes and actor/timestamp, non-transition envelopes
  excluded, empty and catalog-mapped error states (the superseded
  endpoint-gap stub test was removed with the stub).
  Battery: 307 web tests green; `tsc --noEmit` / `eslint .` /
  `prettier --check .` clean.
- **Shared fixtures:** `web/tests/helpers/task-detail.ts` adds
  contract-complete factories for `Checkpoint`, `Attachment`,
  `AttachmentContent`, `Resolution` and `AuditReport` (mirroring the
  generated types) so the four suites pin one field set.

### Open questions recorded by this WP

- **OQ: transitions endpoint.** `GET /tasks/{id}/transitions` is
  absent from Section 9.2's published surface and from
  `schemas/openapi.yaml`; MT-4.6-03's history block cannot be completed
  until it lands. The append-only record needs actor, states, reason
  code (Section 8.2 verbatim) and server timestamp (Section 7.2).
- **OQ: follow-toggle persistence scope.** Session-level was the safe
  default (recorded above); if product wants account-level follow
  state it needs a backend user preference.

### Notes

- **Typed-client regen (concurrent backend churn).** During this WP's
  final battery, `schemas/openapi.yaml` had moved under this WP
  (policy-engine agent adding `policy_engine_version` to `AuditReport`).
  Ran the documented `npm run generate:api`; the regenerated client is
  part of this WP's diff and the `makeAuditReport` fixture was updated
  for the new required field. Re-run regen if further schema churn
  lands before merge.
- **Design note — detail view's SSE sink.** The detail page owns one
  `useEventStream` connection (`useTaskDetailLiveUpdates`), mirroring
  the board's single-sink discipline (Section 13.3): checkpoint and
  attachment events patch caches; other events for this task trigger
  one deduplicated `GET /tasks/{id}` (partially-described payloads are
  never guessed at — MT-4.3-05 risk note). Events for other tasks are
  ignored (belt and braces; the server can filter per task).

### Convergence gate (2026-10-14)

- Web suite **234 passed**; `generate:api` re-run byte-stable against schema `4026FFCA…` — the only working-tree delta vs HEAD is the WP-3.4 `policy_engine_version` churn, so `check:api` goes green on the batch commit.
