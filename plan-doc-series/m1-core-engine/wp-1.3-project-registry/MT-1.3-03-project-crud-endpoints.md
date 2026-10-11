# MT-1.3-03 — Implement Project CRUD Endpoints with Active/Paused/Archived Status

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.3-03 |
| Title | Implement project CRUD endpoints with Active/Paused/Archived status |
| Parent WP | WP-1.3 — Project registry, policy and manifest (Milestone M1) |
| Requirements | FR-PRJ-01, FR-PRJ-02, FR-PRJ-04; ADR-004 |
| Priority | M |
| Dependencies | MT-1.3-01 (PID generator), MT-1.3-02 (models), MT-1.2-05 (Owner-only permissions), MT-1.2-07 (cross-project tests extend here) |
| Parent sections | 9.2 (Projects row), 7.2, 12.2, 19.1 (WP-1.3), 20.4, 20.5 |

## Context
Section 9.2 defines the Projects surface: `GET/POST /projects`, `GET/PATCH
/projects/{pid}` with caller Owner (agents read-only for their own project — the agent
read path matters from WP-2.x; implement the Owner half now and keep the permission
class row reserved). FR-PRJ-01 is create/read/update/pause/archive with auto-assigned
`PID`; FR-PRJ-02 fixes the stored fields; FR-PRJ-04 says a `Paused`/`Archived` project
offers no work to agents — for this WP the status field and its transitions are the
deliverable; "no work" enforcement at claim time is WP-1.6's guard (T4: "Project
active"), referenced here so behavior is not left dangling.

## Inputs / Prerequisites
* MT-1.3-02 — Project + ProjectPolicy models (creation must also create the default
  policy pair per Section 7.1's 1:1 relationship).
* MT-1.3-01 — id validator for path-parameter validation (Section 7.3: validate at
  every API boundary).
* MT-1.2-05 — permission classes: endpoints are Owner-governed (Section 12.2
  "Manage projects/policy" = Owner only).
* Parent plan Section 9.2 — endpoint list and caller column.
* Parent plan FR-PRJ-01/02/04 — requirement anchors.
* Parent plan Section 9.6 — event catalog includes `project.created|updated`
  (events module lands WP-1.9; emit via the Section 20.4 item 6 hook only once the
  helper exists — otherwise note the future emission point in the changelog).

## Scope (in)
* Implement `GET /projects` (list, cursor-paginated per MT-0.5-04) and `POST /projects`
  (create: name, repo_path, default_branch, system_prompt_rules; server assigns the
  `PID` from MT-1.3-01 and creates the default ProjectPolicy from Section 7.2
  defaults).
* Implement `GET /projects/{pid}` and `PATCH /projects/{pid}` for the FR-PRJ-02 fields
  including `active_status` transitions among `active`/`paused`/`archived`
  (FR-PRJ-01 "pause, and archive" — PATCH, not DELETE; projects are never deleted,
  mirroring Section 7.3's task-id continuity intent; record this reading).
* Validate `{pid}` at the boundary with the MT-1.3-01 validator; malformed or unknown
  ids return catalog codes (`VALIDATION_ERROR`, and for unknown pid the plan provides
  no `PROJECT_NOT_FOUND` — use the closest catalog handling and flag: see Risk notes).
* Enforce Owner-only access via MT-1.2-05 permission classes; cross-project/mismatched
  access returns `AUTH_FORBIDDEN_PROJECT`.
* Document endpoints in the OpenAPI snapshot (Section 20.4 item 4).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Policy read/patch endpoints — MT-1.3-04.
* Manifest endpoint — MT-1.3-05.
* "Paused/Archived offers no work" enforcement in claim/work selection — WP-1.6 (T4
  guard); this task stores and transitions the status that guard reads.
* Agent read-only access to their own project — WP-2.x consumes it; keep the
  permission hook available but the endpoint stays Owner-only until then (note in
  OpenAPI description).
* Event emission implementation — WP-1.9 (record the hook point only).

## Target paths
* `backend/apps/projects/` — serializers/views/routes for project CRUD
* `backend/tests/` — CRUD, status transition, permission tests
* `schemas/` — OpenAPI snapshot updated
* WP changelog entry

## Acceptance criteria
- [ ] `GET/POST /projects` and `GET/PATCH /projects/{pid}` exist per Section 9.2 with
  cursor pagination per MT-0.5-04 (Section 9.2 pagination rule).
- [ ] Creation assigns a `PID[0-9]{5}` id atomically and creates the default policy
  pair; no client-supplied id is accepted (FR-PRJ-01; Section 7.3).
- [ ] `active_status` transitions among the three canonical values only; `Paused` and
  `Archived` states are storable and returned (FR-PRJ-04 foundation).
- [ ] All FR-PRJ-02 fields readable and PATCH-updatable; id immutable
  (Section 7.2/7.4).
- [ ] Endpoints are Owner-only; a mismatched/absent token returns catalog codes
  (`AUTH_REQUIRED`/`AUTH_FORBIDDEN_PROJECT`/`ROLE_NOT_PERMITTED`) — Section 12.2,
  ADR-004 (Section 20.4 item 5 satisfied).
- [ ] OpenAPI snapshot updated with schema diff reviewed (item 4); tests/lint green
  (item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests/test_project_api.py` covering: create returns a generated
`PID`, fetch/patch round-trips every FR-PRJ-02 field, status cycles through all three
values, invalid pid and unknown pid return catalog codes, non-Owner receives
`ROLE_NOT_PERMITTED`, and list pagination follows the MT-0.5-04 shape.

## Attachments
* [Section 9.2 — REST API surface (Projects row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Project entity](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.3](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The Section 9.2 catalog has no `PROJECT_NOT_FOUND` code — for an unknown `{pid}`
  decide once between a 404 with `VALIDATION_ERROR` and `SERVER_ERROR`-free generic
  handling; follow how the plan treats unknown task ids (`TASK_NOT_FOUND` exists for
  tasks) and raise the asymmetry in the changelog rather than inventing
  `PROJECT_NOT_FOUND` (Section 20.4 item 5 forbids uncatalogued codes).
* Agent read-only access (Section 9.2 caller note) must not be accidentally enabled
  for all agents — until WP-2.x, the permission row stays Owner-only; note this
  explicitly in the OpenAPI description to avoid a false expectation.
