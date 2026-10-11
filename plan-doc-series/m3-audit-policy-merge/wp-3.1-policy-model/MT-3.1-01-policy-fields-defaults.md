# MT-3.1-01 — Persist all Project Policy fields with defaults from parent plan 7.2

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.1-01 |
| Title | Persist all Project Policy fields with defaults from parent plan 7.2 |
| Parent WP | WP-3.1 — Policy model and defaults (Milestone M3) |
| Requirements | FR-PRJ-05 |
| Priority | M |
| Dependencies | WP-1.3 complete (project registry and policy endpoint exist) |
| Parent sections | 7.2 (Project Policy), 9.2 (projects/policy endpoints), 19 (WP-3.1), 20.4, 20.5 |

## Context
Section 7.2 defines the Project Policy entity with 16 fields and their defaults, and
FR-PRJ-05 makes per-project policy a mandatory feature. WP-1.3 created the project
registry; this micro-task persists every policy field exactly as Section 7.2 specifies,
applies the documented defaults to every project (including pre-existing rows), and
exposes them through `GET/PATCH /projects/{pid}/policy` (Section 9.2: owner writes,
agents read-only for own project). Every later WP — lease behavior (WP-1.6), submission
(WP-3.2), Policy Engine rules (WP-3.4), merge (WP-3.7) — reads these fields, so the
defaults are a cross-WP contract.

## Inputs / Prerequisites
* Parent plan Section 7.2 — Project Policy table: `lease_duration_minutes` (45),
  `lease_max_total_minutes` (240), `lease_extension_mode` (`checkpoint_only`), `max_retries`
  (3), `max_concurrent_tasks` (1), `autonomous_diff_threshold_lines` (250),
  `auditor_min_confidence` (4), `critical_path_globs`, `migration_path_globs`,
  `sensitive_config_globs`, `auto_complete_enabled` (true), `merge_strategy` (`squash`),
  `branch_prefix` (`feat/{PID}-`), `audit_required_default` (true),
  `stalled_after_minutes` (20).
* Parent plan Section 9.2 — `GET/PATCH /projects/{pid}/policy` caller rules.
* WP-1.3 project model and policy endpoint as they exist today.

## Scope (in)
* Add or complete the policy model/serializer so all 16 Section 7.2 fields persist with
  exactly the documented defaults.
* Migration/backfill so projects created before this task receive the defaults.
* Wire `GET/PATCH /projects/{pid}/policy` to the full field set; keep agents read-only
  for their own project (Section 9.2 caller column).
* Preserve `lease_extension_mode` as `checkpoint_only` with the Section 7.2 note that
  `checkpoint_and_liveness` depends on OQ-04 — do not enable it.
* Unit tests for defaults, round-trip persistence and role read-only behavior.
* Add a WP changelog note.

## Out of scope
* Preset glob content (Django/Next.js/Flutter) — MT-3.1-02.
* Input validation beyond type coercion (glob syntax, ranges) — MT-3.1-03.
* Enforcement of policy values by consumers (sweeper, Policy Engine, merge) — WP-1.6,
  WP-3.4, WP-3.7; this task only stores.
* Web policy editor UI — WP-4.10.
* Manifest summary of policy — WP-2.x init/manifest work.

## Target paths
* `backend/apps/projects/` (policy model fields, serializer, policy endpoint)
* `backend/` migrations (add/normalize policy fields, backfill defaults)
* `backend/tests/` (policy persistence and endpoint tests)
* WP changelog entry

## Acceptance criteria
- [ ] All 16 Project Policy fields from Section 7.2 exist and persist, each with exactly
  the Section 7.2 default value (FR-PRJ-05, Section 20.5 traceability).
- [ ] `GET /projects/{pid}/policy` returns every field and `PATCH` round-trips them;
  agent tokens remain read-only for their own project (Section 9.2).
- [ ] Pre-existing projects receive the defaults through a migration (no null policy
  state).
- [ ] `lease_extension_mode` stays `checkpoint_only`; OQ-04 is referenced, not resolved.
- [ ] `merge_strategy` accepts only the Section 7.2 values
  (`squash` / `merge_commit` / `fast_forward_only`).
- [ ] Errors use codes already in the Section 9.2 catalog (Section 20.4 item 5).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k project_policy -q` and confirm every Section 7.2 field
round-trips with its documented default on a fresh project and on a backfilled project;
then the full suite (`pytest backend/tests -q`) stays green.

## Attachments
* [Section 7.2 — Project Policy fields and defaults](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — REST API surface (projects/policy)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.1 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Defaults are a contract: later WPs read them literally; changing a default after
  WP-1.6/WP-3.4 land invalidates their tests — treat Section 7.2 as frozen input.
* Section 7.2 enumerates three `merge_strategy` values while WP-3.7's slice list also
  mentions `manual`; do not widen the enum here — raise a new open question (OQ-xx) if
  the discrepancy surfaces during WP-3.7.
* `lease_extension_mode` second value is gated on OQ-04; storing the enum member is
  acceptable, enabling the behavior is not.
