# MT-1.4-01 — Create the Task Model with Fields and Check Constraints for Id Patterns

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.4-01 |
| Title | Create the Task model with fields and check constraints for id patterns |
| Parent WP | WP-1.4 — Task model, id sequencing and CRUD (Milestone M1) |
| Requirements | FR-TSK-01, FR-TSK-02; G-01, ADR-010 |
| Priority | M |
| Dependencies | MT-1.3-02 (Project model FK and `task_counter`), MT-1.3-03 (project API exists), MT-1.3-05 (WP-1.3 complete) |
| Parent sections | 7.1, 7.2 (Task), 7.3, 7.4, 8.1, 9.1 (`tasks` module), 19.1 (WP-1.4), 20.3, 20.4, 20.5 |

## Context
WP-1.4's first slice is "models and constraints". Section 7.2 fixes the Task field
table (id `{PID}-T{index}`, project FK, title, description, acceptance_criteria,
target_scope, test_command, priority, state, version, worker/lease fields,
failure_retry_count, attempt_number, audit_required, review_reason, latest_feedback,
merge_status, archived_at, timestamps). FR-TSK-01 demands ids of pattern
`PID[0-9]{5}-T[0-9]{3,}`, unique and gap-tolerant; Section 7.4 requires validation at
API boundaries and by DB check constraint; G-01/ADR-010 fix the six canonical state
values (`draft`, `pending`, `in_progress`, `to_be_audited`, `in_human_review`,
`completed`). Per Section 20.3 this is a model-plus-migration task with no unrelated
logic; the state-machine service (WP-1.5) will own writes to `state`, and this task
records that contract.

## Inputs / Prerequisites
* MT-1.3-02 — Project model: FK target, `task_counter` (used by MT-1.4-02), and the
  `PID` id the task id embeds.
* Parent plan Section 7.2 — Task field table (verbatim authority).
* Parent plan Section 7.3 — task id rule: `{PID}-T{index}`, index ≥ 3 digits growing
  naturally (`T1000`); ids validated at every API boundary and by check constraint.
* Parent plan Section 7.4 — integrity constraints.
* Parent plan Section 8.1 — canonical six states (G-01); Section 8.4 — review_reason
  enum (nullable on the model).
* Parent plan FR-TSK-01 (id pattern), FR-TSK-02 (field list), FR-TSK-05 (priority
  enum `urgent`/`high`/`medium`/`low`).

## Scope (in)
* Create the Task model with exactly the Section 7.2 fields and canonical names;
  `priority` constrained to the four FR-TSK-05 values; `state` constrained to the six
  G-01 values with initial value `draft` (Section 8.2 T1: create → `draft`).
* Add DB check constraints: id matches `PID[0-9]{5}-T[0-9]{3,}` (Section 7.3/7.4,
  FR-TSK-01); `version` ≥ 1 (initial 1, FR-TSK-06 optimistic locking field from
  Section 7.2); `failure_retry_count` ≥ 0; `attempt_number` ≥ 0.
* Store `state` as canonical machine value separate from display labels (ADR-010,
  G-01) — no display strings in the column.
* Record the write contract in code comments/tests: `state` is written only by the
  state-machine service from WP-1.5 (Section 9.1 dependency rule: `tasks` owns state
  changes, others call the service) — here the model exists; the enforcement test
  arrives with WP-1.5, so this task adds the model-level documentation note only.
* Model tests: field/enum/constraint coverage; id constraint rejects malformed ids.
* Create the migration for this model only (Section 20.3).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Id sequencing/counter logic — MT-1.4-02.
* Endpoints — MT-1.4-03.
* Dependencies (`depends_on` relation) — MT-1.4-05 (separate relation/constraint).
* Soft-archive behavior — MT-1.4-06 (the `archived_at` field exists here as Section
  7.2 requires; behavior is that task's scope).
* Transition history, checkpoints, resolutions, audit reports — their WP-1.5/1.8/1.9
  and M3 models (Section 7.2 shows them as separate entities).
* Lease behavior reading these fields — WP-1.6.

## Target paths
* `backend/apps/tasks/` — Task model with constraints
* `backend/` — migration for the Task model only
* `backend/tests/` — model constraint tests
* WP changelog entry

## Acceptance criteria
- [ ] Task fields match Section 7.2 exactly — canonical names, no additions or
  omissions (FR-TSK-02; Section 20.5).
- [ ] Check constraint enforces `PID[0-9]{5}-T[0-9]{3,}`; malformed ids rejected at
  the DB (FR-TSK-01; Section 7.4).
- [ ] `state` constrained to the six G-01 canonical values, defaults to `draft`;
  `priority` constrained to `urgent`/`high`/`medium`/`low` (FR-TSK-05;
  ADR-010).
- [ ] `version`, `failure_retry_count`, `attempt_number` constraints present
  (Section 7.2; FR-TSK-06 foundation).
- [ ] `archived_at` and `merge_status` fields exist per Section 7.2 (readers come in
  MT-1.4-06 / merge WPs).
- [ ] Migration applies/reverses cleanly, model-only (Section 20.3; Section 18
  migration check); tests/lint green (item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k "task and (model or constraint)"` asserting every
Section 7.2 field exists with correct type/default, the id check constraint rejects
`PID1-T1`/`PID00001-T1`(2-digit) style violations, enum columns reject out-of-set
values; then `python manage.py migrate` and `makemigrations --check`.

## Attachments
* [Section 7.2 — Task entity](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.3 — Identifier generation rules](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.1 — Canonical state diagram](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The id regex `[0-9]{3,}` grows past three digits (`T1000`) — a constraint written
  for exactly 3 digits would break Section 7.3's natural growth; test `T1000` and a
  long index explicitly.
* The model includes lease/merge fields whose owning services do not exist yet
  (WP-1.6, M3) — acceptable because Section 7.2 defines the entity once; do not add
  behavior for them (Section 20.3: one concept per task).
