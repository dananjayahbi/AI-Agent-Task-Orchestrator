# MT-5.2-02 — Implement the Route Allowlist per Parent Plan Section 15.2

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.2-02 |
| Title | Implement the route allowlist per parent plan Section 15.2 |
| Parent WP | WP-5.2 — Edge policies and route allowlist (Milestone M5) |
| Requirements | FR-NET-01, FR-SEC-05 |
| Priority | M |
| Dependencies | MT-5.2-01 (Access policy defined) |
| Parent sections | 15.2, 15.1, 12.1, 19.1 (WP-5.2), 20.4, 20.5 |

## Context
Section 15.2 fixes the route policy on the tunnel hostname: exposed — auth/devices,
read projects/tasks, review, dashboard, events stream; Could-exposed — task
create/publish (FR-MOB-08, OQ-12: out of v1 default); LAN-only — agent token
creation, policy editing, admin; conditional — agent work endpoints (claim,
checkpoints, submit) and merge queue **only** for remote scenarios with a service
token; health — internal only. Section 19 (WP-5.2) acceptance: "blocked routes
return denial from the public hostname and succeed on LAN." Section 12.1: public
exposure mitigated by "tunnel hostname route allowlist."

## Inputs / Prerequisites
* MT-5.2-01 — edge gate in place; route rules layer on top of it.
* WP-5.1 (MT-5.1-02) — cloudflared ingress mapping to web and backend.
* Parent plan Section 15.2 — the authoritative route-group table.
* Section 9.2 — the concrete endpoint paths each route group maps to.

## Scope (in)
* Enforcement of the Section 15.2 table on the tunnel hostname: route groups marked
  "No (LAN only)" are denied at the edge for tunnel requests; "Internal only"
  (health) is not reachable through the tunnel; conditional groups (agent work,
  merge queue) are gated by service token as the table specifies; the default v1
  posture treats "Could" rows (task create/publish) per OQ-12 (not in v1) —
  documented explicitly either way.
* Configuration living in `infra/cloudflare/` (and/or tunnel ingress config where
  route matching belongs), reproducing the table as explicit allow/deny rules — no
  implicit defaults: anything not explicitly allowed for the tunnel is denied.
* The LAN path (Section 15.1 direct address) remains unaffected — LAN-only routes
  keep working there.
* Unit/consistency test: every row of the Section 15.2 table maps to an explicit
  rule in the configuration (traceability, Section 20.5).

## Out of scope
* The Access identity policy — MT-5.2-01.
* Rate limiting — MT-5.2-03.
* Executing the full blocked-vs-allowed matrix — MT-5.2-04 (checklist).
* Django-side permission classes — WP-1.2 (the allowlist is defense in depth, not a
  replacement).
* Changing any endpoint's API surface — Section 9.2 stays authoritative.

## Target paths
* `infra/cloudflare/route-allowlist.md` (rule set mirroring Section 15.2)
* `infra/compose/` cloudflared ingress configuration (if route matching is enforced
  there)
* `backend/tests/` or repo test validating table-to-rule coverage
* WP changelog entry

## Acceptance criteria
- [ ] Every Section 15.2 row is represented by an explicit allow/deny rule; default
  is deny for the tunnel hostname (Section 15.2; Section 20.5 traceability test).
- [ ] LAN-only groups (agent token creation, policy editing, admin) are denied from
  the tunnel and remain reachable on the LAN (Section 19 WP-5.2 acceptance).
- [ ] Health is not exposed through the tunnel (Section 15.2 "Internal only").
- [ ] Conditional groups require a service token exactly as Section 15.2 states; the
  OQ-12 decision on task create/publish is recorded in the allowlist file, not
  silently defaulted.
- [ ] No secrets committed (Section 20.4 item 3 — service-token references only);
  changelog note added (item 7).

## Test command
`pytest backend/tests/test_route_allowlist_coverage.py -v` — parses
`infra/cloudflare/route-allowlist.md` (or its machine-readable form) and asserts a
one-to-one mapping with the Section 15.2 rows; live blocked-vs-allowed execution is
MT-5.2-04's checklist.

## Attachments
* [Section 15.2 — Route policy on the tunnel hostname](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.1 — Threat model (public exposure)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-5.2 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Route matching at the edge vs. path prefixes at the app can diverge (e.g. `/api/v1/
  tokens/agent` blocked at edge but reachable if ingress routes the whole `/api`
  prefix) — enumerate concrete paths from Section 9.2 when writing rules; the
  coverage test is the guard.
* Blocking "Could" rows (task create/publish) is the OQ-12 default; flipping them on
  later is a one-line config change but must update this file and the checklist —
  note that coupling in the changelog.
