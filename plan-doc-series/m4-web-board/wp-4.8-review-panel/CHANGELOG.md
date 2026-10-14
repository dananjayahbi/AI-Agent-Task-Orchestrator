# WP-4.8 — Human review panel and queue: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).
All commands run from `web/`: `npx vitest run` (307 tests across 37
files green), `npx tsc --noEmit`, `npx eslint .`, `npx prettier --check .`
— all green; no backend/schema change (no `check:api` drift).

## Unreleased

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

### Deferred

- **MT-4.8-02 — review panel (deferred).** Reasons, rule table and
  evidence panel: not yet implemented; scheduled batch 10. Its concrete
  dependency MT-4.6-03 (resolution/transition context in task detail)
  completed in batch 9 — WP-4.6's changelog records it as completed,
  superseding its own deferral — and WP-4.7's diff viewer has landed in
  full, so no external dependency remains; the panel component and its
  tests simply have not been built yet (`web/components/review/` holds
  the queue and dialogs only; `web/tests/review/` likewise).

### Open questions recorded by this WP

- **OQ: queue age precision.** Age uses `updated_at` (above); if a
  dedicated "entered `in_human_review` at" field or the transitions
  endpoint lands, the queue should switch to it.
- **OQ: review panel entry.** Rows currently navigate to task detail
  (the MT's allowed entry point); the review-panel href joins with
  MT-4.8-02 without changing the row contract.
