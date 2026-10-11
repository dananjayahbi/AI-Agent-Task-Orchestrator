# MT-1.9-04 — Apply Insert-Only Database Permissions to Transition and Event Tables

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.9-04 |
| Title | Apply insert-only database permissions to transition and event tables |
| Parent WP | WP-1.9 — Event log and audit trail (Milestone M1) |
| Requirements | FR-SEC-03 |
| Priority | M |
| Dependencies | MT-1.9-01 (Event model exists); MT-1.5-05 (transition history model exists) |
| Parent sections | 12.5, 19.1 (WP-1.9), 20.4, 20.5 |

## Context
Section 12.5: "the application database role cannot update or delete audit rows."
Section 19 (WP-1.9) acceptance: "the application role cannot update or delete events,"
and the deliverables list "database permissions for insert-only" covering both the
transition and event tables. MT-1.5-05 created the transition history model with an
insert-only pattern; this task applies and verifies the enforcement at the database
level for both append-only tables.

## Inputs / Prerequisites
* MT-1.9-01 — Event table created.
* MT-1.5-05 — Task Transition history model (insert-only pattern, first table).
* Deployment topology Section 16.1 — the app connects as a restricted role; the
  migration/role setup runs with elevated privileges (one-shot `migrate` service).
* WP-1.1 settings — database roles/URLs are environment-driven (Section 9.10).

## Scope (in)
* Database-level privilege configuration so the application role holds INSERT (and the
  SELECT needed to read history) on the transition and event tables, but **not**
  UPDATE or DELETE.
* A migration/role-setup step that applies this safely in Compose (one-shot migrate)
  and is idempotent on re-run.
* Tests that attempt UPDATE and DELETE as the application role against both tables and
  assert denial, and that INSERT still succeeds.
* Documentation of the privilege model in the WP changelog note.

## Out of scope
* Row-level restrictions for other tables — WP-1.2 / hardening WP-6.1.
* Database superuser, backup and migration roles — Section 16.5 (backup runs with
  elevated rights by design).
* Soft-delete/retention behavior of events (retention is decided in OQ-10, applied in
  M6) — do not delete anything here.
* The API-level read-only audit viewer (Section 12.5) — web/mobile WPs.

## Target paths
* `backend/apps/events/migrations/` (privilege setup for the event table)
* `backend/apps/tasks/migrations/` (privilege setup for the transition table, if not
  already applied by MT-1.5-05)
* `backend/tests/events/test_insert_only_permissions.py`
* WP changelog entry

## Acceptance criteria
- [ ] The application role cannot UPDATE or DELETE rows in either the transition or
  the event table (Section 19 WP-1.9 acceptance; Section 12.5).
- [ ] The application role can INSERT into both tables and SELECT from them, so
  writers and the replay/history readers keep working.
- [ ] The setup step is idempotent: running the migrate service twice does not fail.
- [ ] The permission tests run against the real Compose database, not a mock.
- [ ] Lint, type check and tests green (Section 20.4 item 2); no environment-specific
  paths committed (item 3); changelog note added (item 7).

## Test command
`pytest backend/tests/events/test_insert_only_permissions.py -v` — verifies INSERT
succeeds while UPDATE/DELETE are denied on both tables as the application role.

## Attachments
* [Section 12.5 — Audit trail](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.9 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.1 — Compose services (one-shot migrate)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Privilege migrations often assume superuser at deploy time — confirm the one-shot
  migrate service connects with sufficient rights in both dev and prod profiles, and
  that the app role is the one used at runtime (Section 16.2 startup validation).
* If MT-1.5-05 already enforced insert-only on the transition table, verify rather
  than duplicate; overlapping migrations can deadlock — review existing migrations
  before writing a new one.
