# MT-1.3-04 — Implement Policy Read/Patch Endpoints with Validation

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.3-04 |
| Title | Implement policy read/patch endpoints with validation |
| Parent WP | WP-1.3 — Project registry, policy and manifest (Milestone M1) |
| Requirements | FR-PRJ-05; G-09, G-26 |
| Priority | M |
| Dependencies | MT-1.3-02 (ProjectPolicy model/defaults), MT-1.3-03 (project routes and Owner-only permissions), MT-1.2-05 |
| Parent sections | 9.2 (Projects row: `GET/PATCH /projects/{pid}/policy`), 7.2, 12.2, 19.1 (WP-1.3), 20.4, 20.5 |

## Context
FR-PRJ-05 defines per-project policy: lease duration, max retries, autonomy diff
threshold, critical path globs, max concurrent tasks, merge strategy — each with the
Section 7.2 defaults. Section 9.2 provides `GET/PATCH /projects/{pid}/policy`
(caller Owner). The web policy editor (FR-WEB-09) and the Policy Engine (WP-3.x),
lease sweeper (WP-1.7) and claim concurrency limit (WP-1.6) all read these values, so
this task fixes a validated, documented write path — the only supported way to change
policy (Section 12.5: policy edits are state changes; audit/event emission follows
WP-1.9's helper — record the hook).

## Inputs / Prerequisites
* MT-1.3-02 — the ProjectPolicy model with Section 7.2 defaults.
* MT-1.3-03 — `{pid}` route, boundary validation, Owner-only permission wiring.
* Parent plan Section 7.2 — policy field table: types, defaults, enums
  (`lease_extension_mode`, `merge_strategy`).
* Parent plan FR-PRJ-05 — the six named policy dimensions.
* Parent plan Section 9.2 — endpoint pair and caller.
* OQ-04 — `lease_extension_mode = checkpoint_and_liveness` is a per-project option
  (default `checkpoint_only`); the endpoint must accept the enum without deciding the
  OQ's product default (already recommended).

## Scope (in)
* Implement `GET /projects/{pid}/policy`: returns the full policy with current values
  and documented defaults (response shape mirrors Section 7.2 field names).
* Implement `PATCH /projects/{pid}/policy`: partial update of Section 7.2 fields with
  per-field validation:
  * enums: `lease_extension_mode` ∈ {`checkpoint_only`, `checkpoint_and_liveness`},
    `merge_strategy` ∈ {`squash`, `merge_commit`, `fast_forward_only`} (Section 7.2);
  * numeric bounds sanity: positive durations/retries/thresholds;
    `auditor_min_confidence` within 1–5 (Section 7.2 says 1-5);
    `max_concurrent_tasks` ≥ 0-policy semantics per G-26 default 1;
  * glob lists (`critical_path_globs`, `migration_path_globs`,
    `sensitive_config_globs`, `branch_prefix`) accepted as string lists/strings —
    validate as non-empty when supplied; glob *semantics* are the Policy Engine's
    concern (WP-3.x), not this endpoint's.
  * Unknown fields or type errors return `VALIDATION_ERROR` in the standard envelope.
* Owner-only enforcement via MT-1.2-05; catalog codes only.
* Document endpoints in the OpenAPI snapshot (Section 20.4 item 4).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Semantics/validation of glob matching against real files — Section 12.3/9.4 (Policy
  Engine, WP-3.x).
* Consumers of policy values (claim limits, sweeper, merge) — WP-1.6/1.7/3.x; they
  read the rows this endpoint writes.
* Audit-trail/event emission for policy edits — WP-1.9 (record the hook; Section 12.5
  requires policy edits in the audit trail eventually).
* Policy editor UI — FR-WEB-09 (WP-4.x).

## Target paths
* `backend/apps/projects/` — policy serializers/views/routes with validation
* `backend/tests/` — policy GET/PATCH validation tests
* `schemas/` — OpenAPI snapshot updated
* WP changelog entry

## Acceptance criteria
- [ ] `GET/PATCH /projects/{pid}/policy` exist per Section 9.2; GET returns all
  Section 7.2 fields with their current values (FR-PRJ-05 field coverage).
- [ ] PATCH validates enums and bounds per Section 7.2 (merge strategy, extension mode,
  confidence 1–5, positive durations/retries/thresholds); invalid input returns
  `VALIDATION_ERROR` (Section 9.2 catalog; Section 20.4 item 5).
- [ ] Defaults are never silently rewritten: patching one field leaves all others at
  their current values (partial-update semantics documented in OpenAPI).
- [ ] Endpoint is Owner-only; mismatched token returns `AUTH_FORBIDDEN_PROJECT` /
  `ROLE_NOT_PERMITTED` (Section 12.2; ADR-004).
- [ ] OpenAPI snapshot updated, schema diff reviewed (Section 20.4 item 4);
  tests/lint green (item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests/test_project_policy_api.py` covering: GET equals Section 7.2
defaults for a fresh project; PATCH of `max_retries` changes only that field; invalid
enum/bounds produce `VALIDATION_ERROR`; non-Owner is rejected; unknown field is
rejected rather than ignored.

## Attachments
* [Section 7.2 — Project Policy fields and defaults](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — REST API surface (policy endpoints)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.3](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Bounds not stated numerically in the plan (e.g. max sensible
  `lease_max_total_minutes`) must not be invented as hard policy — validate only what
  Section 7.2 states (positivity, enums, 1–5 confidence) and flag anything else to the
  owner rather than silently clamping values the Policy Engine will later depend on.
* `branch_prefix` interacts with G-09 (canonical branch name = prefix + task index
  part) — changing it via PATCH affects bridge branch naming (WP-2.x); document that
  the prefix is applied per Section 7.2's `feat/{PID}-` default pattern.
