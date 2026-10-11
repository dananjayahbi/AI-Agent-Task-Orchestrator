# MT-1.8-03 — Implement the Checkpoint Endpoint Returning New Lease Expiry

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.8-03 |
| Title | Implement the checkpoint endpoint returning new lease expiry |
| Parent WP | WP-1.8 — Checkpoints and token usage (Milestone M1) |
| Requirements | FR-LEA-03, NFR-11, NFR-12, ADR-005, ADR-012, G-17 |
| Priority | M |
| Dependencies | MT-1.8-01, MT-1.8-02 (model + gate); MT-1.6-03 (extension) |
| Parent sections | 6.5 (Flow B), 8.6, 9.2 (Progress endpoints), 9.6, 10.5, 19 (WP-1.8), 20.4, 20.5 |

## Context
Section 9.2 exposes `POST /tasks/{id}/checkpoints` (Agent caller). Flow B is the
sequence: verify lease owner + not expired → store checkpoint;
`lease_expires_at` = now + policy lease bounded by cap → publish event to realtime
fan-out → return the new `lease_expires_at` to the bridge. The tool contract
(Section 10.5 `log_task_checkpoint`) says the response "Returns new expiry;
`LEASE_EXPIRED` instructs the agent to stop and re-claim" — the expiry in the
response is also what feeds the bridge's `next_checkpoint_due` hint (RISK-02
mitigation) and the web/mobile checkpoint feeds (G-11).

## Inputs / Prerequisites
* MT-1.8-01 (model) and MT-1.8-02 (ownership/fencing gate) complete.
* MT-1.6-03 — extension function with hard-cap semantics.
* Parent plan Section 9.2 — Progress endpoint row; Section 9.6 — `task.checkpoint`
  event in the catalog and the event envelope.
* WP-0.5 conventions — error envelope (MT-0.5-02), idempotency/correlation headers
  (MT-0.5-03), cursor conventions (MT-0.5-04, listing is MT-1.8-04).
* Section 7.2 — checkpoint fields (`message`, `percent`, `token_usage`, `kind`,
  `session_id`, `attempt_number`) accepted from the caller.
* WP-1.9 — event write-in-transaction + post-commit publish for realtime (Section
  9.6).

## Scope (in)
* Implement `POST /tasks/{id}/checkpoints`: agent authentication (project-scoped
  token), request validation of Section 7.2 fields (`percent` 0–100 bounds, `kind`
  enum), then the MT-1.8-02 gate, then store the checkpoint and apply the MT-1.6-03
  extension — all in one transaction.
* Update `Task.last_checkpoint_at` and copy the current `attempt_number` onto the
  row at write time (Section 7.2 semantics).
* Emit `task.checkpoint` in-transaction (Section 9.6 catalog; Section 20.4 item 6)
  so WP-1.10 streams it to web/mobile feeds.
* Response: the new `lease_expires_at` (plus the stored checkpoint identity) per
  Section 10.5's "Returns new expiry"; refusals use catalog codes with the Section
  9.2 envelope — `LEASE_EXPIRED` must be recognizable by the bridge as "stop and
  re-claim".
* Idempotency-key handling per Section 9.2/ADR-012 (NFR-12); OpenAPI updated and
  schema diff reviewed (NFR-11, Section 20.4 item 4).
* API tests: happy path fields and response; percent/kind validation errors
  (`VALIDATION_ERROR`); expired/stale/foreign rejections; idempotent replay returns
  the same result without a duplicate row or double extension; extension respects
  the cap end-to-end (WP-1.8 acceptance).
* Add a WP changelog note.

## Out of scope
* The bridge `log_task_checkpoint` tool wrapper — WP-2.6 (consumes this endpoint).
* SSE streaming of the event — WP-1.10; event-log storage — WP-1.9.
* Listing endpoint — MT-1.8-04.
* Liveness-ping mode (OQ-04) — off by default; seam only.
* Push notifications — checkpoints are not a Section 9.8 push trigger.

## Target paths
* `backend/apps/tasks/` (checkpoint endpoint: serializer, view, permissions)
* `schemas/openapi` generated snapshot (contract update)
* `backend/tests/` (endpoint tests)
* WP changelog entry

## Acceptance criteria
- [ ] `POST /tasks/{id}/checkpoints` exists per Section 9.2, appears in the
  generated OpenAPI document (ADR-005), and its non-2xx responses use the Section
  9.2 envelope with catalog codes (Section 20.4 item 5).
- [ ] A valid owner checkpoint stores the row, updates `last_checkpoint_at`, extends
  the lease by `min(now + duration, acquired + cap)`, and returns the new
  `lease_expires_at` (FR-LEA-03; Section 8.6; Section 10.5).
- [ ] Extension never exceeds the hard cap end-to-end (WP-1.8 acceptance).
- [ ] `percent` bounds and `kind` enum enforced with `VALIDATION_ERROR`
  (WP-1.8 acceptance: percent bounds enforced).
- [ ] Expired/stale/foreign callers receive `LEASE_EXPIRED` / `LEASE_NOT_OWNED` with
  zero writes (MT-1.8-02 proven through the API).
- [ ] `task.checkpoint` event written in the same transaction (Section 9.6,
  Section 20.4 item 6); idempotent retry safe (NFR-12).
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k checkpoint_endpoint -q` and confirm the success
response shape (new expiry), validation and lease error paths, cap enforcement,
idempotent replay and the event row; regenerate/validate the OpenAPI snapshot;
full suite stays green.

## Attachments
* [Section 6.5 Flow B — Checkpoint and lease extension](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — REST API surface (Progress)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Tool catalog (`log_task_checkpoint`)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The response contract ("new expiry") is consumed by WP-2.6's `next_checkpoint_due`
  hint — freeze it in the OpenAPI snapshot now; any additional response fields need
  an OQ, not ad-hoc additions.
* Transaction length: gate + insert + extension + event must stay one short
  transaction to hold NFR-02 (p95 under 300 ms) — avoid extra reads after the lock.
* Bridge retries with the same idempotency key must not double-extend the lease —
  the replay path must return the stored outcome (verify explicitly in tests).
