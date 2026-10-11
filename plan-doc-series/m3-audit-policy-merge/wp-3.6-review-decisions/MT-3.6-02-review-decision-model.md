# MT-3.6-02 — Create the Review Decision model with decided_via fields

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.6-02 |
| Title | Create the Review Decision model with decided_via fields |
| Parent WP | WP-3.6 — Human review decisions API (Milestone M3) |
| Requirements | FR-AUD-05 |
| Priority | M |
| Dependencies | WP-1.1 (Django skeleton, model/migration conventions), WP-3.2 (Resolution model referenced by `resolution_id`) |
| Parent sections | 7.2, 12.5, 8.2 (T15), 19 (WP-3.6), 20.3, 20.4, 20.5 |

## Context
Section 7.2 fixes the Review Decision entity's fields verbatim: `id`, `task_id`,
`resolution_id`, `decision` (`approve` / `request_changes` / `reassign`), `note`,
`decided_by`, `decided_via` (`web` / `mobile`), `decided_at`. T15 records a Review
Decision as its side effect (Section 8.2), Section 11.5 says "All decisions are
recorded", and Section 12.5 requires every review decision to write an Event row with
actor and correlation id — with the application database role unable to update or
delete audit rows. `decided_via` distinguishes the web board from the mobile review
sheet (Section 13/14 channels), which is why the endpoint consumers differ.

## Inputs / Prerequisites
* Parent plan Section 7.2 — the exact field list (verbatim).
* Parent plan Sections 12.5, 8.2 — audit-trail and T15 recording obligations.
* WP-1.1 — Django app layout, model and migration conventions.
* WP-3.2 — Resolution model that `resolution_id` references.
* MT-3.6-01 — the endpoint that will persist these rows (depends on this task).

## Scope (in)
* A `Review Decision` model in the backend with exactly the Section 7.2 fields:
  `id`, `task_id`, `resolution_id`, `decision` (`approve` / `request_changes` /
  `reassign`), `note`, `decided_by`, `decided_via` (`web` / `mobile`), `decided_at` —
  no extra fields, no renames.
* Constraints that keep the contract honest: `decision` restricted to the three
  values; `decided_via` restricted to `web`/`mobile`; `task_id` FK to Task,
  `resolution_id` FK to Resolution; `decided_by` recording the acting user/principal.
* Migration created in this task alone (Section 20.3: never combine a migration with
  unrelated logic), written to be reversible where practical (Section 16.5).
* Append-only discipline consistent with Section 12.5 — decisions are recorded, not
  edited; the audit-trail Event row remains the WP-1.9 mechanism (no duplicate audit
  system invented here).
* Model-level tests: field set matches Section 7.2; enum/choice constraints reject
  out-of-contract values; migration applies and reverses cleanly.

## Out of scope
* Endpoint behavior and transition handling — MT-3.6-01.
* Writing the `review.decided` Event row — WP-1.9 conventions consumed by
  MT-3.6-01 (this task only defines the decision record).
* `latest_feedback` propagation — MT-3.6-03; stale-resolution protection —
  MT-3.6-04.
* Retention of decisions — OQ-10 territory (set elsewhere).

## Target paths
* `backend/` — Review Decision model
* `backend/` — migration for the model (standalone)
* `backend/tests/` — model tests
* OpenAPI/docs if the model is exposed in schemas (schema diff reviewed)
* WP changelog entry

## Acceptance criteria
- [ ] The model carries exactly the Section 7.2 fields with the specified value
  sets (`decision`: `approve`/`request_changes`/`reassign`; `decided_via`:
  `web`/`mobile`) — none added, dropped or renamed (Section 20.5 traceability).
- [ ] `task_id` and `resolution_id` reference existing Task and Resolution rows;
  `decided_at` is set server-side.
- [ ] The migration is its own change, applies cleanly, and reverses where practical
  (Sections 20.3, 16.5).
- [ ] Model tests reject out-of-contract `decision` and `decided_via` values.
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`pytest backend/tests -k review_decision_model -q` — assert field set and value
constraints against Section 7.2, FK integrity, and a migrate/reverse round trip;
then `pytest backend/tests -q` stays green.

## Attachments
* [Section 7.2 — Entities and key fields](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.5 — Audit trail](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan's field list is the contract — adding "helpful" fields (IP, user agent,
  channel free-text) drifts from Section 7.2; raise additions as a decision first
  (Section 20.1).
* `resolution_id` must be populated for every approve (it enables MT-3.6-04's
  stale-protection); a nullable column used as optional would silently disable
  protection — enforce presence for `approve` at the endpoint (MT-3.6-01/04).
* Decisions feed the audit trail (Section 12.5) — deleting rows via normal ORM
  flows would violate it; document the append-only expectation for future queries.
