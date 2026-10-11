# MT-1.4-05 — Implement Task Dependency Relation (depends_on)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.4-05 |
| Title | Implement task dependency relation (depends_on) |
| Parent WP | WP-1.4 — Task model, id sequencing and CRUD (Milestone M1) |
| Requirements | FR-TSK-07 |
| Priority | S |
| Dependencies | MT-1.4-01 (Task model), MT-1.4-03 (task endpoints exist), MT-1.4-04 (list endpoint context) |
| Parent sections | 7.1 (TASK DEPENDENCY N:N), 7.2, 9.2, 19.1 (WP-1.4), 20.3, 20.4, 20.5 |

## Context
FR-TSK-07 (priority S): "Task dependencies: a task is offered only when all
dependencies are `completed`." Section 7.1 shows TASK —N:N— TASK DEPENDENCY; the
enforcement point ("offered") is the work/claim path — `GET /projects/{pid}/work`
(Section 9.2) and the T4 claim guard (Section 8.2: "dependencies completed"), both
WP-1.6 — and the canonical `DEPENDENCY_UNMET` error exists for that enforcement
(Section 9.2 catalog). This micro-task builds the relation and its write-side rules
now, plus the reusable "all dependencies completed?" query the WP-1.6 work selection
will consume, so the guard has one implementation to call.

## Inputs / Prerequisites
* MT-1.4-01/03 — Task model and CRUD endpoints (dependency edges attach to tasks
  created through `POST /projects/{pid}/tasks`).
* Parent plan Section 7.1 — TASK DEPENDENCY join entity between tasks (N:N).
* Parent plan FR-TSK-07 — offer rule; Section 8.2 T4 guard "dependencies completed";
  Section 9.2 `DEPENDENCY_UNMET` catalog code.
* Parent plan Section 9.3 — re-validation of dependencies "inside the lock" at claim
  time (WP-1.6) — the query built here must be callable inside a locked transaction.
* Parent plan Section 7.4 — integrity constraints.

## Scope (in)
* Create the TaskDependency relation (N:N per Section 7.1) with its own migration
  (Section 20.3: migration not mixed with unrelated logic).
* Write-side API: express a task's dependencies — either as a field on task
  create/PATCH (accepting dependency task ids) or a dedicated representation; choose
  the shape that fits Section 9.2's task resources, fix it in the OpenAPI snapshot,
  and record the choice (Section 12.3's discipline applies: reject ids outside the
  project — dependencies are always same-project; a cross-project dependency would
  violate Zero-Bleed, GOAL-2).
* Validation on write: referenced tasks exist and belong to the same project;
  self-dependency rejected; cycles rejected (FR-TSK-07's "all dependencies completed"
  is unsatisfiable in a cycle — cycle prevention is implied; note the reading in the
  changelog since the plan does not state it explicitly).
* Provide the single readiness query: "all dependencies of task X are in state
  `completed`" (canonical state per G-01) — the one implementation WP-1.6's work
  selection and claim guard will call (Section 8.2 T4 guard; Section 9.3 step 4).
* Tests: valid/invalid edges, self and cycle rejection, cross-project rejection with
  catalog codes (`VALIDATION_ERROR` for structure, `DEPENDENCY_UNMET` reserved for
  offer/claim-time enforcement), readiness query true/false cases.
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Enforcing the rule at offer/claim time (`/work` selection, T4 guard,
  `DEPENDENCY_UNMET` responses) — WP-1.6; this task only delivers the relation and
  the readiness query it calls.
* UI dependency visualization — WP-4.x.
* Cascade behavior on archive of a dependency — MT-1.4-06 defines archive semantics;
  coordinate there, do not invent cascade rules here.
* Changing the state of a dependency task — WP-1.5 owns state writes.

## Target paths
* `backend/apps/tasks/` — TaskDependency model + write validation + readiness query
* `backend/` — migration for the relation only
* `backend/tests/` — relation validation and readiness tests
* `schemas/` — OpenAPI snapshot updated if the dependency field/endpoint is exposed
* WP changelog entry

## Acceptance criteria
- [ ] A TaskDependency relation exists per Section 7.1 (N:N) with a standalone
  migration (Section 20.3; Section 18 migration check).
- [ ] Writing dependencies validates existence, same-project scope (GOAL-2/ADR-004
  spirit) and rejects self/cycles with catalog codes (Section 20.4 item 5).
- [ ] One readiness implementation answers "all dependencies `completed`?" per
  FR-TSK-07 / Section 8.2 T4 guard; tested against: no deps (ready), mixed states
  (not ready), all completed (ready).
- [ ] The query is documented as the contract for WP-1.6's work selection and claim
  guard (Section 9.3 step 4 revalidation).
- [ ] If the dependency shape is exposed on task resources, the OpenAPI snapshot is
  updated (item 4); tests/lint green (item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests/test_task_dependencies.py` covering: edge creation
validation (missing task, other project's task, self, two-node cycle), readiness query
for the three state cases, and migration apply/reverse.

## Attachments
* [Section 7.1 — Entity relationship overview (Task Dependency)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.2 — Transition table (T4 guard)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.4](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* FR-TSK-07 is priority S but the readiness query is load-bearing for WP-1.6's claim
  guard — schedule it before WP-1.6 regardless of priority (Section 19 dependency
  chain); a missing query would push guard logic into WP-1.6 and bloat it.
* Cycle prevention is a reading of the plan, not a stated rule — document the reading
  (a cyclic dependency set can never be offered, deadlocking tasks) and flag it for
  owner confirmation rather than presenting it as spec text.
