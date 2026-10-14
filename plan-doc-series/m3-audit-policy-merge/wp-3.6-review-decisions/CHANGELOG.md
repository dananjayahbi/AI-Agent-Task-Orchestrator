# WP-3.6 — Human review decisions API (T15/T16)

## Unreleased

### Done — MT-3.6-02 → 01 → 03 → 04 (all four, in the plan's dependency order)

- **MT-3.6-02 Review Decision model.** `apps/audit/models.py` gains
  `ReviewDecision` with the Section 7.2 field set **verbatim** — `id`
  (UUID, the §7.2-new-entity pattern precedent), `task_id`,
  `resolution_id`, `decision` (`approve`/`request_changes`/`reassign`),
  `note`, `decided_by`, `decided_via` (`web`/`mobile`), `decided_at`
  (server clock) — none added, dropped or renamed (asserted
  field-for-field in `tests/test_review_decision_model.py`). Every
  value set is DB-checked (`CheckConstraint`s on `decision`,
  `decided_via`), and an `approve` without a `resolution_id` is refused
  **by the database** (MT-3.6-02's risk note — a silently optional
  column would disable MT-3.6-04's protection). `resolution_id` is
  nullable so T9-anchored note actions record honestly. The row is
  append-only (Section 12.5): the `TaskResolution` P8 discipline
  (insert-only `save`, refused `update`/`bulk_update`/`delete`). Standalone
  migration `audit.0003_reviewdecision` (Section 20.3), applied and
  reversed in its own test (Sections 20.3, 16.5).
- **MT-3.6-01 review endpoint.** `POST /tasks/{id}/review`
  (`apps/audit/views.ReviewDecisionView` + `apps/audit/review.py`)
  implements the three Section 9.2 decisions through the state machine:
  **T15** `approve` (flag-only — merge-pending is the Section 8.1
  sub-status, T13's recorded reading; `merge_status = pending` + the
  Review Decision record) and **T16** `request_changes`/`reassign`
  (to `pending`; note required for request_changes — missing note
  answers `VALIDATION_ERROR` with the T16 hint; `latest_feedback` set;
  `attempt_number` preserved; worker cleared). Registered lazily via
  the MT-1.5-04 seam (`ensure_review_wired`, same discipline as WP-3.3;
  dispatcher/registry/loader untouched). Each accepted decision writes
  Transition row + `review.decided` event (Section 9.6 catalog) +
  Review Decision record in the dispatch transaction (Section 8.2
  rule 2), with `Idempotency-Key` replay. Authorization is the
  Section 12.2 *Review decisions* row (Owner + Device via
  `CanReviewDecisions`; agents `ROLE_NOT_PERMITTED`, scope-first
  `AUTH_FORBIDDEN_PROJECT`); the matrix row **landed on the real
  route** — its probe retired, the deferred-endpoint entry removed,
  and the two allowed actors walk two seeded tasks (one mutable task
  per probe). Catalog-first: `approve`/`request_changes`/`reassign`
  added to `TransitionReason` (migration `tasks.0009`).
  **Recorded decisions:** 201 on accept (a record was created —
  matching the verdict endpoint's precedent); `decided_via` derived
  server-side (owner session → `web`, device token → `mobile`;
  Section 8.2's legend *O = Owner (web/mobile)* keeps one actor
  column); `decided_by` = owner user id / device id; the endpoint
  carries `DeviceEndpointThrottle` (the row's non-owner cell is
  Device; the owner request rides the same per-token budget — the
  WP-1.8/WP-3.2/WP-3.3 shared-row recording, once more).
- **MT-3.6-03 latest_feedback propagation.** T16 writes
  `Task.latest_feedback` (Section 7.2 "latest wins" overwrite); the
  field was already served by `GET /tasks/{id}` — the backend half of
  the bridge's `get_task_details` (Section 10.5) — and its help text
  now documents the contract. `tests/test_latest_feedback.py` closes
  the loop: after an Owner request-changes the next coder-agent read
  carries the note; a newer note overwrites; a note-less reassign
  keeps the prior feedback (recorded reading — T16's side-effect
  column sets the field, but wiping a reviewer's context because the
  card was reshuffled loses Section 11.5's meaning); tasks without
  feedback return `""` without breaking consumers. Bridge-side tool
  schema/tests are WP-2.4/bridge-owner territory (not touched here).
- **MT-3.6-04 stale-resolution protection.** The approve path binds
  the decision to the `resolution_id` the reviewer saw (Section 14.2
  approve safety; ADR-012): the service compares it to the current
  attempt's resolution **under the row lock, inside the dispatch
  transaction** — an outdated id answers `VERSION_CONFLICT` (409; the
  catalog's stale-resource semantics — **code choice recorded here**,
  per MT-3.6-04's risk note: no new code, Section 20.4 item 5) with a
  "refresh and re-review" message and **zero** T15 side effects; a
  missing `resolution_id` on approve is `VALIDATION_ERROR`; a foreign
  task's resolution id is `VALIDATION_ERROR` (malformed, not stale);
  the stale `version` rule still applies alongside (both guards
  observed). Only approve is resolution-bound (Section 14.2 names the
  approval — no invented bindings for the note actions). The race
  proofs run on **real Postgres** in
  `tests/integration/test_review_decision_postgres.py`: concurrent
  approvals and approve-vs-request-changes each yield exactly one
  winner (one 201, one 409, one record, one transition), the outdated
  binding loses cleanly, and the NFR-12 decision class (MT-1.15-03's
  recorded deferral) now has its sequential + concurrent
  same-`Idempotency-Key` replays — one stored record either way.

### Notes

- `schemas/openapi.yaml` regenerated byte-stable ×2 (new
  `submit_review_decision` operation + `latest_feedback` help text).
- The bridge catalog (`bridge/src/orchestrator_bridge/endpoints.py`)
  needs **no** stale-flag flip: `POST /tasks/{id}/review` is an
  Owner/Device REST surface the bridge never speaks, and
  `PENDING_BACKEND` is empty — nothing to retire (verified against the
  bridge contract test).
- MT-3.6-03's bridge-half test command (`bridge/tests -k
  task_details_feedback`) belongs to the bridge owner; the backend
  propagation half is proven here.
