# MT-1.6-03 — Implement Lease Extension Rules with Hard Total-Age Cap

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.6-03 |
| Title | Implement lease extension rules with hard total-age cap |
| Parent WP | WP-1.6 — Lease and claim service (Milestone M1) |
| Requirements | FR-LEA-03, ADR-012, G-17 |
| Priority | M |
| Dependencies | MT-1.6-01 (lease record and acquisition semantics) |
| Parent sections | 7.2 (Project Policy), 8.6, 19 (WP-1.6), 20.4, 20.5 |

## Context
Section 8.6 fixes extension precisely: "Extend: each valid checkpoint sets
`lease_expires_at` = min(now + duration, `lease_acquired_at` +
`lease_max_total_minutes`). After the hard cap, the owner must submit or release; the
sweeper then reclaims." FR-LEA-03 states the same rule — a checkpoint from the lease
owner extends the lease by the full policy duration, bounded by a maximum total lease
age. Defaults: `lease_duration_minutes` 45, `lease_max_total_minutes` 240
(Section 7.2). G-17 confirms extension is checkpoint-driven by default
(`lease_extension_mode` = `checkpoint_only`; OQ-04 liveness mode is off).

## Inputs / Prerequisites
* MT-1.6-01 — claim writes `lease_acquired_at` / `lease_expires_at` /
  `lease_generation`; the extension function operates on that record.
* Parent plan Section 8.6 — the exact `min(now + duration, acquired + cap)` formula.
* Section 7.2 — Project Policy fields `lease_duration_minutes` (45),
  `lease_max_total_minutes` (240), `lease_extension_mode` (default
  `checkpoint_only`).
* Section 8.6 "Acquire" and "Expire" — extension never resurrects an expired lease
  (that rejection lands in MT-1.8-02 but shares this function's guard).
* FR-LEA-03 (WP-1.6 requirement row) and WP-1.8 acceptance "extension never exceeds
  hard cap".

## Scope (in)
* Implement the lease extension function: given the current owner's valid (unexpired)
  lease, set `lease_expires_at` = min(now + `lease_duration_minutes`,
  `lease_acquired_at` + `lease_max_total_minutes`).
* Enforce the hard cap exactly: once the computed cap is reached, the value never
  moves past `lease_acquired_at + lease_max_total_minutes`, regardless of how many
  checkpoints arrive; expose a flag/result indicating the cap was reached so callers
  (checkpoint endpoint, bridge `next_checkpoint_due` hint) can tell the owner to
  submit or release (Section 8.6).
* Guard: extension is refused when the lease is expired or the caller generation is
  stale (delegated rejections use `LEASE_EXPIRED` / `LEASE_NOT_OWNED`); extension is
  a no-op for `lease_extension_mode` other than valid-owner requests per OQ-04's
  default — liveness mode itself is out of scope.
* Read policy values from the project's Project Policy (never hardcoded); defaults
  documented in Section 7.2.
* Unit tests: fresh extension, extension near the cap clamping exactly to the cap,
  repeated extensions never exceeding the cap, expired-lease refusal, custom policy
  durations honored.
* Add a WP changelog note.

## Out of scope
* Calling this function from the checkpoint endpoint — MT-1.8-03 (WP-1.8 consumes
  it; WP-1.8's acceptance "extension never exceeds hard cap" is proven there too).
* `checkpoint_and_liveness` mode (OQ-04) — off by default; implement only if OQ-04
  was decided otherwise in WP-0.4, otherwise leave a documented seam.
* Bridge-side `next_checkpoint_due` hint — WP-2.6 (uses the returned expiry).
* Stall detection (`stalled_after_minutes`) — UI-only indicator (Section 8.6),
  WP-4.x.
* Sweeper reclaim of capped leases — WP-1.7.

## Target paths
* `backend/apps/leases/` (extension function and policy lookup)
* `backend/tests/` (extension and cap tests)
* WP changelog entry

## Acceptance criteria
- [ ] Extension computes `lease_expires_at` = min(now + `lease_duration_minutes`,
  `lease_acquired_at` + `lease_max_total_minutes`) exactly as Section 8.6 states
  (FR-LEA-03).
- [ ] No sequence of extensions ever sets `lease_expires_at` beyond the hard cap
  (WP-1.8 acceptance cross-check; Section 7.2 defaults 45/240 honored).
- [ ] Expired or stale-generation callers are refused with catalog lease errors
  (Section 9.2, Section 20.4 item 5); no lease resurrection (Section 8.6).
- [ ] Policy values come from Project Policy with Section 7.2 defaults — no
  hardcoding (Section 20.5 traceability).
- [ ] Cap-reached outcome is distinguishable by the caller so "submit or release"
  guidance can be surfaced (Section 8.6).
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k lease_extension -q` and confirm the formula, exact cap
clamping across repeated extensions, refusal on expired/stale leases, and custom
policy values; full suite (`pytest backend/tests -q`) stays green.

## Attachments
* [Section 8.6 — Lease semantics in detail](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Project Policy fields](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Clock skew between app instances can make `min()` clamp inconsistently — use the
  database clock consistently for now/cap math or document the chosen clock source;
  deviation from the plan becomes an OQ.
* Cap semantics interact with sweeper timing (Section 8.6: after the cap the sweeper
  reclaims) — coordinate with WP-1.7 so a capped-but-not-yet-expired lease is not
  swept early; the sweeper acts only on `lease_expires_at` < now.
