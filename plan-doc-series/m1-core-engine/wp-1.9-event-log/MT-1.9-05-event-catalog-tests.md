# MT-1.9-05 — Write Event Catalog Tests Covering Every Required Emission (Section 9.6)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.9-05 |
| Title | Write event catalog tests covering every required emission (Section 9.6) |
| Parent WP | WP-1.9 — Event log and audit trail (Milestone M1) |
| Requirements | FR-SEC-03 |
| Priority | M |
| Dependencies | MT-1.9-02 (write helper and wired call sites), MT-1.9-03 (publish flow), MT-1.9-04 (permissions) |
| Parent sections | 9.6, 12.5, 19.1 (WP-1.9), 20.4 (item 6), 20.5 |

## Context
Section 9.6 defines the event catalog: `project.created|updated`,
`task.created|updated|transitioned|claimed|released`, `task.checkpoint`,
`task.lease_expiring`, `task.lease_expired`, `attachment.processing|ready|failed`,
`audit.claimed|passed|escalated`, `review.requested|decided`,
`merge.started|succeeded|failed`, `agent.session_started|ended`, `system.alert`.
Section 20.4 item 6 makes "events emitted where required by Section 9.6" a global DoD
check. This task builds the test harness that pins the catalog to the plan and proves
each emission site wired so far produces its event exactly once.

## Inputs / Prerequisites
* MT-1.9-02 — helper and wired call sites (transitions, token actions).
* MT-1.9-03 — publish flow to assert on.
* Parent plan Section 9.6 — the full catalog list (24 types as written) and envelope.
* Section 19 (WP-1.9) acceptance — every transition and token action produces exactly
  one event.
* Emission sites that exist at this point in delivery: project registry (WP-1.3),
  tasks/transitions (WP-1.4/1.5), leases (WP-1.6/1.7).

## Scope (in)
* A catalog reference test asserting the registered event types equal the Section 9.6
  list exactly — no additions, drops or renames (traceability, Section 20.5).
* Per-site emission tests for every M1 emission site delivered so far: project
  create/update, task create/update/transition/claim/released, checkpoint, lease
  expiring (80% mark) and expired (sweeper), asserting exactly one event with the
  correct envelope fields per action.
* A test that each required emission also triggers exactly one post-commit publish
  (MT-1.9-03 contract).
* A documented pending list inside the test module for catalog types whose producing
  WPs have not landed yet (`attachment.*` WP-1.12, `audit.*`/`review.*`/`merge.*`
  WP-3.x, `agent.session_*` WP-2.x, `system.alert` detector WP-1.7/monitoring), so the
  remaining coverage is explicit rather than silently absent.

## Out of scope
* Emission sites of later WPs — those WPs add their own tests when they adopt the
  helper (they inherit this harness).
* The SSE delivery side (gateway, resume, load test) — WP-1.10.
* Deciding the catalog question for token events — tracked as the OQ raised in
  MT-1.9-02 risk notes; the test must not invent a type.
* Catalog additions — prohibited here; Section 20.4 item 5 requires catalog-first
  changes.

## Target paths
* `backend/tests/events/test_event_catalog.py`
* `backend/tests/events/` (per-site emission test modules as needed)
* WP changelog entry

## Acceptance criteria
- [ ] The catalog test asserts the exact Section 9.6 list — none added, dropped or
  renamed (Section 20.5 traceability).
- [ ] Every emission site delivered by M1 up to WP-1.9 has an exactly-one-event test
  with a correct Section 9.6 envelope (Section 20.4 item 6).
- [ ] Each covered emission is asserted to publish once after commit.
- [ ] Not-yet-implemented catalog types are listed explicitly as pending in the test
  module, with their producing WP named.
- [ ] Acceptance demonstrably met by the named test command (Section 20.4 item 1);
  lint/type/tests green (item 2); changelog note added (item 7).

## Test command
`pytest backend/tests/events/ -v` — catalog equality test plus all per-site emission
and post-commit publish assertions.

## Attachments
* [Section 9.6 — Realtime gateway and event model (catalog)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.9 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 20.4 — Global definition of done](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The pending list can rot: a later WP might land its emission without flipping its
  pending entry. Mitigate by naming the producing WP next to each pending entry so
  review of that WP's MT checklist includes this file.
* The `task.lease_expiring` emission depends on the 80%-of-lease notifier
  (MT-1.7-04); if WP-1.7 is not merged when this task runs, mark that entry pending
  rather than weakening the test — Section 20.6 orders WP-1.7 before WP-1.10 but the
  exact interleave with WP-1.9 is not fixed by the plan.
