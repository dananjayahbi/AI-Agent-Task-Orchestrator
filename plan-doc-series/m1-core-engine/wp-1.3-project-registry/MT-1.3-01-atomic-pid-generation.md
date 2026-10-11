# MT-1.3-01 — Implement Atomic PID Identifier Generation (PID[0-9]{5})

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.3-01 |
| Title | Implement atomic PID identifier generation (PID[0-9]{5}) |
| Parent WP | WP-1.3 — Project registry, policy and manifest (Milestone M1) |
| Requirements | FR-PRJ-01 (auto-assigned PID ids; Section 7.3 identifier rules) |
| Priority | M |
| Dependencies | MT-1.2-07 (WP-1.2 complete — caller identity and permissions exist) |
| Parent sections | 3 (Glossary), 7.3, 7.4, 9.1 (`projects` module), 19.1 (WP-1.3), 20.4, 20.5 |

## Context
WP-1.3's first slice is the id generator. Section 7.3 fixes the rule: the project id
is assigned from a database sequence and rendered as `PID` plus five zero-padded
digits, capacity 99,999, with exhaustion raising a clear error; ids are validated
against their regular expression at every API boundary and by a database check
constraint (Section 7.4). FR-PRJ-01 requires auto-assigned `PID` ids. Everything in
M1 keys on this identifier — tasks embed it (`PID00007-T004`), tokens scope to it,
manifests carry it.

## Inputs / Prerequisites
* Parent plan Section 7.3 — identifier generation rules (verbatim authority).
* Parent plan Section 7.4 — integrity constraints; validation at API boundary and DB
  check constraint.
* Parent plan Section 9.1 — `projects` module owns registry and ids.
* Parent plan Glossary — `PID` pattern `PID[0-9]{5}`.
* MT-1.2-05 — permission classes exist; the generator itself is not endpoint-facing
  yet (endpoints arrive in MT-1.3-03).
* MT-1.1-05 — database available for sequence-backed generation.

## Scope (in)
* Implement PID generation per Section 7.3: a database sequence supplies the number;
  the renderer formats `PID` + five zero-padded digits (e.g. `PID00007`).
* Enforce the pattern with a database check constraint on the project id column
  (Section 7.4) and expose a reusable validator for API-boundary use (Section 7.3 —
  every API boundary validates; the validator here is consumed by MT-1.3-03/04).
* Define exhaustion behavior: when the sequence would exceed five digits, raise a
  clear, catalog-mapped error (Section 7.3 "exhaustion raises a clear error" — map it
  to `VALIDATION_ERROR` or `SERVER_ERROR` per Section 9.2 rather than inventing a
  code; record which one in the changelog).
* Unit tests: format, uniqueness under concurrent allocation, boundary values
  (`PID00000` must not be issued if the sequence starts at 1 — pick and test the
  starting value), constraint rejection of malformed ids.
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* The Project model itself — MT-1.3-02 (the sequence exists; the model column that
  consumes it is that task's migration; if sequencing needs the table, coordinate the
  sequence creation here and the FK/constraint there — do not merge the migrations,
  Section 20.3).
* API endpoints creating projects — MT-1.3-03.
* Task ids (`{PID}-T{index}`) — MT-1.4-02 (per-project counter, Section 7.3).
* Optimistic concurrency (`version`) — WP-1.4/1.5 as scoped there.

## Target paths
* `backend/apps/projects/` — PID generator + validator
* `backend/` — sequence creation migration (generator support only)
* `backend/tests/` — generator/constraint tests
* WP changelog entry

## Acceptance criteria
- [ ] Generated ids match `PID[0-9]{5}` exactly — five zero-padded digits after `PID`
  (Section 7.3; Glossary).
- [ ] Generation is atomic: concurrent allocations never reuse a number (Section 7.3
  database-sequence authority; mirrors FR-PRJ-01 "auto-assigned").
- [ ] A database check constraint rejects malformed project ids (Section 7.4); a
  boundary validator exists for reuse by MT-1.3-03/04 (Section 7.3).
- [ ] Exhaustion beyond 99,999 raises a clear error mapped to a Section 9.2 catalog
  code — no invented codes (Section 20.4 item 5).
- [ ] Tests green; migration applies cleanly; lint/type check green (item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k "pid or project_id"` covering format, concurrent unique
allocation, constraint rejection, and exhaustion; run `python manage.py migrate` to
confirm the sequence migration applies.

## Attachments
* [Section 7.3 — Identifier generation rules](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.4 — Integrity constraints](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.3](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Sequence-based ids leak project count (not sensitive) but gaps are expected — do not
  "fix" gaps later; Section 7.3 accepts them (gap tolerance is stated for task ids;
  the same expectation applies here).
* If the sequence is created in its own migration, a later Project-model migration
  must reference it — note the dependency in the changelog so migration order cannot
  be silently changed (Section 18 migration check guards this).
