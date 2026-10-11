# MT-1.13-04 — Implement Permanent Per-Attachment Description Caching

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.13-04 |
| Title | Implement permanent per-attachment description caching |
| Parent WP | WP-1.13 — Visual description provider (Milestone M1) |
| Requirements | FR-ATT-02, FR-ATT-05; G-14 |
| Priority | M |
| Dependencies | MT-1.13-01 (interface), MT-1.13-02 (disabled), MT-1.13-03 (remote impl), MT-1.12-07 (status/retry semantics) |
| Parent sections | 4 (G-14), 9.5, 19.1 (WP-1.13 acceptance), 20.4, 20.5 |

## Context
Two plan sentences fix the caching requirement. Section 9.5: "Descriptions are
generated once and cached." G-14: "result cached permanently per attachment
(WP-1.13)." Together they make caching the cost-control that keeps a vision model
from being called on every reprocessing or retry: the description is a per-attachment,
generate-once artifact. WP-1.13's acceptance closes the loop — "with provider enabled,
descriptions are produced **once** per attachment". Section 9.5 also says derived data
is re-creatable while originals are retained, so the cache must survive re-runs of the
pipeline (retry/backoff from MT-1.12-07) without regenerating or duplicating.

## Inputs / Prerequisites
* MT-1.13-01 … MT-1.13-03 — interface, both implementations, cost/failure logging.
* MT-1.12-07 — status transitions and retry/backoff: a retried job re-enters the
  caption step, which is exactly when the cache must short-circuit the provider.
* Parent plan Section 9.5 — "generated once and cached"; derived data persisted in
  stage 4; originals retained, derived data re-creatable.
* G-14 — "cached permanently per attachment".

## Scope (in)
* Persist the generated description keyed by attachment (the attachment's own id —
  G-14 says per attachment, not per content hash), stored with the attachment's
  derived data (Section 9.5 stage 4).
* Read-through behavior: if a description already exists for the attachment, return it
  without invoking the provider (no cost, no failure risk) — this is what makes
  "produced once" testable across pipeline retries and explicit reprocessing.
* Write-once semantics: a successful generation is stored once; a failed generation
  stores nothing and leaves the next attempt free to retry (failure caching belongs
  to MT-1.13-05's degradation contract, not here).
* Disabled-provider interaction: "no description" from MT-1.13-02 is not a cached
  value — enabling the provider later must still generate for such attachments (G-14
  caches descriptions, not absence); encode and test this explicitly.
* Tests: second processing run makes zero provider calls and returns byte-identical
  text; retry-after-failure does call the provider again; disabled-then-enabled
  generates; concurrent duplicate requests cannot double-generate for one attachment
  (Section 18 concurrency spirit; keep the test bounded to this unit).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Cache invalidation/TTL — G-14 says permanently; no eviction policy is invented.
* Cross-attachment or content-hash dedup of identical files — uploads are
  de-duplicated by checksum upstream (Section 9.5 stage 1); the cache itself stays
  keyed per attachment as G-14 states.
* Choosing the storage field/column and migration details as a schema decision beyond
  "with derived data" — implement with the attachment's derived data and keep the
  migration isolated (Section 20.3: never combine a migration with unrelated logic).
* Consumption of the cached description in task payloads / `text_ocr` output —
  WP-1.14.

## Target paths
* `backend/apps/attachments/` (cache read/write in the provider call path; derived
  data persistence)
* Migration for the description storage field (kept isolated per Section 20.3)
* `backend/tests/attachments/` (generate-once, retry, disabled-then-enabled tests)
* WP changelog entry

## Acceptance criteria
- [ ] With the provider enabled, a description is produced **once** per attachment:
  re-running the pipeline makes zero additional provider calls and returns the stored
  text — WP-1.13 acceptance, second half (FR-ATT-02; G-14).
- [ ] The cache is permanent: no TTL/eviction path exists (G-14 "permanently").
- [ ] A failed generation is not cached: the retry path can still call the provider
  (Section 9.5 retry stages; MT-1.12-07).
- [ ] "No description" (disabled provider) is not stored as a cached value; enabling
  the provider afterwards generates normally (G-14 semantics).
- [ ] The migration is isolated and re-runnable per Section 20.3; no secrets or
  environment-specific paths committed (Section 20.4 item 3).
- [ ] Tests, lint and type check green in CI (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
`pytest backend/tests/attachments -k description_cache -v` — generate-once across two
processing runs, retry-after-failure regenerates, disabled-then-enabled generates,
identical stored text; full `pytest backend/tests -q` stays green.

## Attachments
* [G-14 — Cached permanently per attachment](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.5 — Attachment processing (generate once and cache)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.13 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "Permanently" versus Section 9.5's "derived data re-creatable": treat the
  description as derived-but-cached — attachment deletion may remove it (it lives
  with the attachment), but nothing else invalidates it; state this reading in the
  changelog so WP-1.14 does not assume regeneration.
* If the storage field lands on the Task Attachment model (Section 7.2), keep the
  migration additive and small; mixing it with pipeline changes would violate
  Section 20.3 and complicate review.
* A race between two concurrent caption attempts for the same attachment could still
  double-call the provider once; assert the common retry path is serialized and note
  any residual race rather than claiming perfect single-flight without a lock test.
