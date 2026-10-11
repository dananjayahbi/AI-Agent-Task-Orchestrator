# MT-1.3-02 — Create Project and ProjectPolicy Models with Migrations and Defaults

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.3-02 |
| Title | Create Project and ProjectPolicy models with migrations and defaults |
| Parent WP | WP-1.3 — Project registry, policy and manifest (Milestone M1) |
| Requirements | FR-PRJ-02, FR-PRJ-05, FR-PRJ-04 (status field), FR-PRJ-01 (id column) |
| Priority | M |
| Dependencies | MT-1.3-01 (PID generator/sequence), MT-1.2-02 (token model's `project_id` FK consumer pattern) |
| Parent sections | 7.1, 7.2 (Project, Project Policy), 7.4, 9.1, 19.1 (WP-1.3), 20.3, 20.4, 20.5 |

## Context
WP-1.3's slice "models and migrations" creates the two central entities. Section 7.2
lists the Project fields (id, name, repo_path, active_status, default_branch,
system_prompt_rules, agent_policy reference, task_counter, timestamps) and the full
Project Policy table with **exact defaults** (lease_duration_minutes 45,
lease_max_total_minutes 240, lease_extension_mode `checkpoint_only`, max_retries 3,
max_concurrent_tasks 1, autonomous_diff_threshold_lines 250, auditor_min_confidence 4,
critical/migration/sensitive globs, auto_complete_enabled true, merge_strategy
`squash`, branch_prefix `feat/{PID}-`, audit_required_default true,
stalled_after_minutes 20). FR-PRJ-02/05 are the requirement anchors. Section 20.3
forbids mixing a migration with unrelated logic — this task is models + migrations
only.

## Inputs / Prerequisites
* MT-1.3-01 — sequence + check constraint for the `PID` id column.
* Parent plan Section 7.2 — Project and Project Policy field tables (verbatim).
* Parent plan Section 7.1 — relationship diagram: Project 1:1 Project Policy;
  Project 1:N Task; `task_counter` on Project.
* Parent plan Section 7.4 — integrity constraints.
* Parent plan FR-PRJ-02 (project fields), FR-PRJ-05 (policy fields), FR-PRJ-04
  (status values Active/Paused/Archived → canonical `active`/`paused`/`archived`).
* G-26 default `max_concurrent_tasks` of 1; G-09 `branch_prefix` default
  `feat/{PID}-`.

## Scope (in)
* Create the Project model with exactly the Section 7.2 fields: immutable
  `PID[0-9]{5}` id (check-constrained, Section 7.4), name, repo_path, active_status
  constrained to `active`/`paused`/`archived`, default_branch, system_prompt_rules
  (markdown), agent_policy (one-to-one policy), task_counter (integer for MT-1.4-02),
  created_at/updated_at server timestamps (Section 0.4: UTC, server clock).
* Create the ProjectPolicy model with every Section 7.2 policy field and its exact
  default; one policy per project (Section 7.1 shows 1:1).
* Create the migrations for these two models only (Section 20.3); apply and reverse
  cleanly.
* Model-level tests: defaults match Section 7.2 value-for-value; status enum limited
  to the three canonical values; id immutable after creation; task_counter starts at 0.
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Creating a default policy when a project is created — that wiring belongs to
  MT-1.3-03 (CRUD creates the pair); keep model-only here per Section 20.3.
* CRUD/policy endpoints — MT-1.3-03/04.
* Manifest rendering — MT-1.3-05.
* Consuming policy values (lease durations, thresholds) — WP-1.6/1.7/WP-3.x policy
  engine; the fields exist now, their readers come later.
* `repo_path` validation beyond storing it — informational for the backend
  (Section 7.2); path enforcement is Section 12.3/bridge concerns.

## Target paths
* `backend/apps/projects/` — Project and ProjectPolicy models
* `backend/` — migration for both models only
* `backend/tests/` — model invariant/default tests
* WP changelog entry

## Acceptance criteria
- [ ] Project fields match Section 7.2 exactly — none added, dropped or renamed
  (Section 20.5 traceability against FR-PRJ-02).
- [ ] ProjectPolicy contains every Section 7.2 policy field with the exact documented
  default (FR-PRJ-05; G-26 `max_concurrent_tasks` default 1; G-09 `branch_prefix`
  `feat/{PID}-`).
- [ ] `active_status` accepts only `active`, `paused`, `archived` (FR-PRJ-04;
  Section 7.2); id is immutable and check-constrained to `PID[0-9]{5}` (Section 7.4).
- [ ] `task_counter` exists and starts at 0, ready for MT-1.4-02 (Section 7.2).
- [ ] Migration applies/reverses cleanly; `makemigrations --check` clean
  (Section 18); no unrelated logic in the migration (Section 20.3).
- [ ] Tests, lint, type check green (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k "project and (model or policy or default)"` asserting the
field/default tables against Section 7.2, then `python manage.py migrate` and
`python manage.py makemigrations --check`.

## Attachments
* [Section 7.2 — Entities (Project, Project Policy)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.1 — Entity relationship overview](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.3](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Default drift is the main hazard: policy defaults feed the Policy Engine, leases and
  merge behavior later — a wrong default here silently changes automation semantics.
  Test each default value literally against Section 7.2.
* `critical_path_globs`/`migration_path_globs`/`sensitive_config_globs` defaults in
  Section 7.2 are described ("CI/CD, root migrations, security config",
  "framework-specific", "env files, key material, security rules"), not enumerated as
  exact glob lists — translate conservatively, document the concrete globs chosen in
  the changelog, and flag them for owner confirmation (no hidden decisions,
  Section 20.1 item 5).
