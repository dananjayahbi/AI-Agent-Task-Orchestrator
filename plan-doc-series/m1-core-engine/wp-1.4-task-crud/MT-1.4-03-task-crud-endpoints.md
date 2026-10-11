# MT-1.4-03 — Implement Task CRUD Endpoints

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.4-03 |
| Title | Implement task CRUD endpoints |
| Parent WP | WP-1.4 — Task model, id sequencing and CRUD (Milestone M1) |
| Requirements | FR-TSK-02, FR-TSK-06; ADR-012 (idempotency for create) |
| Priority | M |
| Dependencies | MT-1.4-01 (model), MT-1.4-02 (allocator), MT-1.3-03 (project routes), MT-1.2-05 (permissions), MT-1.1-04 (OpenAPI), MT-0.5-04 (pagination) |
| Parent sections | 9.2 (Tasks row), 7.2, 7.3, 8.2 (T1), 12.2, 19.1 (WP-1.4), 20.4, 20.5 |

## Context
Section 9.2 defines the Tasks surface: `GET/POST /projects/{pid}/tasks` and
`GET/PATCH /tasks/{id}`, caller Owner. FR-TSK-02 fixes the creatable/editable fields
(title, markdown description, acceptance criteria list, target scope globs, test
command, priority, …). Creation is transition T1 (new → `draft`, actor Owner,
side effects: allocate task id; emit `task.created` — Section 8.2), so this task's
create path must call the MT-1.4-02 allocator and set `state = draft` initially;
full transition orchestration belongs to WP-1.5, but a task cannot exist without T1's
first step. FR-TSK-06 provides optimistic concurrency: PATCH carries the `version` the
client saw; a stale version returns `VERSION_CONFLICT` (WP-1.4 acceptance).

## Inputs / Prerequisites
* MT-1.4-01/02 — Task model, constraints and the single id allocator.
* MT-1.3-03 — project route pattern and `{pid}` validation.
* MT-1.2-05 — Owner-only permission classes (Section 12.2: create draft tasks =
  Owner; Decomposer/Device rows noted as deferred — see Risk notes).
* Parent plan Section 9.2 — endpoint list, caller Owner, mutating endpoints accept an
  idempotency key header (Section 9.2 rule; ADR-012).
* Parent plan Section 8.2 T1 — create semantics (draft, allocate id, emit
  `task.created`).
* Parent plan Section 8.2 rules — "The UI sends the `version` it saw; a stale version
  returns a conflict" (FR-TSK-06).
* MT-0.5-03/04 — idempotency and cursor-pagination conventions; MT-0.5-02 — error
  envelope.

## Scope (in)
* Implement `POST /projects/{pid}/tasks`: creates a task in `draft` (T1's model-level
  step) with an allocated id; accepts the FR-TSK-02 fields (title, description,
  acceptance_criteria, target_scope, test_command, priority); validates
  `target_scope` globs at creation (Section 12.3: "target_scope globs are validated on
  creation"); honors the idempotency key header per MT-0.5-03; response includes
  `version` (=1) and the generated id.
* Implement `GET /tasks/{id}`: full task detail (Section 9.2).
* Implement `PATCH /tasks/{id}`: updates FR-TSK-02 editable fields; requires the
  client-sent `version` to match the stored one — mismatch returns `VERSION_CONFLICT`
  in the standard envelope (FR-TSK-06; WP-1.4 acceptance); on success increments
  `version` (Section 7.2 "incremented on every change").
* Enforce permissions (Owner) and validate `{id}` against the Section 7.3 pattern at
  the boundary; unknown id → `TASK_NOT_FOUND` (Section 9.2 catalog).
* Register endpoints in the OpenAPI snapshot (Section 20.4 item 4).
* Record the `task.created` emission hook point for WP-1.9 (Section 9.6 event
  catalog includes `task.created`).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* List with filters and ordering — MT-1.4-04.
* Dependencies — MT-1.4-05.
* Soft-archive/read-only behavior — MT-1.4-06.
* Publish/unpublish/claim transitions (`POST /tasks/{id}/transition`) — WP-1.5/WP-1.6
  (Section 9.2 lists the transition endpoint; its guards are the state machine's).
* Emitting `task.created` — WP-1.9 provides the event store; record the hook only.
* Agent work endpoints (`/work`, claim) — WP-1.6.

## Target paths
* `backend/apps/tasks/` — serializers/views/routes for task CRUD
* `backend/tests/` — create/read/update + version-conflict tests
* `schemas/` — OpenAPI snapshot updated
* WP changelog entry

## Acceptance criteria
- [ ] `POST /projects/{pid}/tasks`, `GET /tasks/{id}`, `PATCH /tasks/{id}` exist per
  Section 9.2 with the FR-TSK-02 field set; create yields `state = draft` and an id
  matching `PID[0-9]{5}-T[0-9]{3,}` (Section 8.2 T1; FR-TSK-01).
- [ ] A PATCH with a stale `version` returns `VERSION_CONFLICT`; a matching-version
  PATCH succeeds and increments `version` (FR-TSK-06; **WP-1.4 acceptance**).
- [ ] Mutating endpoints accept the idempotency key header and retrying create with
  the same key does not duplicate the task (Section 9.2; ADR-012; NFR-12).
- [ ] `target_scope` globs validated at creation (Section 12.3); invalid input returns
  `VALIDATION_ERROR`; unknown id returns `TASK_NOT_FOUND` — catalog codes only
  (Section 20.4 item 5).
- [ ] Owner-only enforcement per Section 12.2 (ADR-004 discipline preserved).
- [ ] OpenAPI snapshot updated with schema diff reviewed (item 4); tests/lint green
  (item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests/test_task_api.py` covering: create returns allocated id in
`draft` with `version` 1; read round-trips FR-TSK-02 fields; matching-version PATCH
increments `version` and stale-version PATCH returns `VERSION_CONFLICT` in the
envelope; duplicate idempotency key replays without a second row; malformed task id
and unknown id return catalog codes; non-Owner receives `ROLE_NOT_PERMITTED`.

## Attachments
* [Section 9.2 — REST API surface (Tasks row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.2 — Transition table (T1)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.4 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Section 12.2 allows Decomposer (and Device as Could) to create draft tasks — with no
  distinct decomposer token kind yet (see MT-1.2-05 risk), enforce Owner-only now and
  record the deferred rows explicitly so WP-2.x/M5 must revisit; do not silently claim
  matrix coverage.
* PATCH must not become a state-changing backdoor: fields like `state`, `version`,
  lease and merge fields are not client-settable — enforce an explicit writable-field
  allowlist from FR-TSK-02, tested, or the state machine (WP-1.5) can be bypassed.
