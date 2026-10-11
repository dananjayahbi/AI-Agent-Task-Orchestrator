# MT-5.2-04 — Write the Blocked-vs-Allowed Route Verification Checklist

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.2-04 |
| Title | Write the blocked-vs-allowed route verification checklist |
| Parent WP | WP-5.2 — Edge policies and route allowlist (Milestone M5) |
| Requirements | FR-NET-01, FR-SEC-05 |
| Priority | M |
| Dependencies | MT-5.2-01, MT-5.2-02, MT-5.2-03 (policy, allowlist, limits complete) |
| Parent sections | 15.2, 15.3, 19.1 (WP-5.2), 18, 20.4, 20.5 |

## Context
Section 19 (WP-5.2) acceptance: "blocked routes return denial from the public
hostname and succeed on LAN." Section 15.2's table is the matrix to verify. Section
20.4 item 1 requires acceptance to be demonstrably met by a named verification. This
closing task produces the executable checklist that walks every route group from
both network vantage points and records the results.

## Inputs / Prerequisites
* MT-5.2-01/02/03 — Access policy, allowlist and rate limits deployed.
* WP-5.1 — working tunnel (public hostname) and LAN address (Section 15.1).
* Parent plan Section 15.2 — the route-group table (the checklist's row set).
* Section 9.2 — concrete endpoint paths used in the requests.

## Scope (in)
* A checklist document enumerating **every** Section 15.2 row mapped to concrete
  endpoint paths, each with two checks: request via the public tunnel hostname
  (expect the documented allow/deny outcome) and request via the LAN address
  (expect success for LAN-only routes, unchanged behavior otherwise).
* Checks for the edge layers exercised together: Access gate denial for
  unauthenticated public requests (MT-5.2-01), route denial for LAN-only groups
  (MT-5.2-02), and rate-limit behavior on auth/device endpoints (MT-5.2-03,
  `RATE_LIMITED` observed).
* Expected-outcome column filled for every row — no blank expectations (the
  Section 15.2 table is authoritative; "Could" rows record the OQ-12 default).
* A results template (date, environment, pass/fail per row, notes) so the checklist
  can be re-run after any edge change, and an explicit re-run instruction in the
  WP changelog.

## Out of scope
* Implementing any policy change the checklist might reveal — file follow-up tasks.
* Full-stack smoke suite — Section 18 smoke tests (separate).
* CI automation of the live checks — the live checks need deployed Cloudflare state;
  only the table-to-checklist completeness assertion is automatable here.
* Mobile app behavior — WP-5.x.

## Target paths
* `infra/cloudflare/route-verification-checklist.md`
* Optional repo test asserting checklist covers every Section 15.2 row
* WP changelog entry

## Acceptance criteria
- [ ] Every Section 15.2 row appears with concrete endpoint paths and explicit
  expected outcomes for public and LAN vantage points (Section 20.5 traceability —
  no row missing).
- [ ] The acceptance of Section 19 WP-5.2 is directly executable from the checklist:
  blocked routes show denial from the public hostname and success on LAN.
- [ ] Access-gate, allowlist and rate-limit checks are all represented
  (Section 15.3 layers 1 and 4 exercised).
- [ ] A completed results run is recorded (or the template plus a scheduled re-run
  instruction exists), satisfying Section 20.4 item 1 for this WP; changelog note
  added (item 7).

## Test command
`pytest backend/tests/test_route_checklist_coverage.py -v` — asserts the checklist
covers every Section 15.2 row with both vantage points; live execution is manual per
the checklist itself (documented in its header).

## Attachments
* [Section 15.2 — Route policy on the tunnel hostname](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-5.2 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and quality strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "Succeed on LAN" assumes the LAN address reaches the same backend with LAN-only
  routes enabled (Section 15.1) — if the LAN path shares edge config in a given
  deployment, the expected outcome diverges; record the environment assumptions at
  the top of the checklist.
* Checklist drift: after any `infra/cloudflare/` change the results are stale — the
  changelog re-run instruction is part of the deliverable; treat skipped re-runs as
  unverified acceptance.
