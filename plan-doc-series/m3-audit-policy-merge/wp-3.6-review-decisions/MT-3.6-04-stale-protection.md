# MT-3.6-04 — Implement stale-resolution protection on approvals

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.6-04 |
| Title | Implement stale-resolution protection on approvals |
| Parent WP | WP-3.6 — Human review decisions API (Milestone M3) |
| Requirements | FR-AUD-05; ADR-012 |
| Priority | M |
| Dependencies | MT-3.6-01 (endpoint), MT-3.6-02 (`resolution_id` on decisions), WP-3.2 (current resolution) |
| Parent sections | 8.2, 14.2, 9.2, 19 (WP-3.6), 20.4, 20.5 |

## Context
WP-3.6's acceptance: "approval referencing an outdated resolution is rejected."
Section 14.2 (approve safety): "the decision is bound to the viewed `resolution` id
so a newer submission invalidates a stale approval." Mechanically: the reviewer's
client sends the `resolution_id` it displayed; if the task's current resolution
differs (the coder re-submitted while the reviewer looked away), T15 must not run
against the old evidence. The mobile review sheet's WP-5.8 acceptance ("stale
approval rejected") depends on this server-side rule; clients cannot be trusted to
notice staleness themselves (Section 12.1 posture).

## Inputs / Prerequisites
* Parent plan Section 14.2 — approve-safety binding (verbatim).
* Parent plan Section 19 WP-3.6 acceptance — outdated-resolution rejection.
* MT-3.6-01 — the approve path this protects; MT-3.6-02 — `resolution_id` recorded.
* WP-3.2 — Resolution model and the task's current resolution.
* Section 9.2 catalog — `VERSION_CONFLICT` semantics for stale resource state.
* Section 8.2 — stale `version` conflict rule for the task row itself.

## Scope (in)
* Server-side check in the approve path: the request must carry the `resolution_id`
  the reviewer saw; if it differs from the task's current resolution, reject before
  any T15 side effect (no `merge_status` change, no Review Decision row).
* The rejection response: a Section 9.2 catalog code with a human-readable message
  telling the client the resolution changed and to refresh and re-review — recorded
  code choice in the changelog (no new codes, Section 20.4 item 5).
* Interplay with the task `version` check: both guards apply — `version` staleness
  returns the existing conflict path; `resolution_id` staleness is its own distinct
  rejection (a re-submission bumps both, but the resolution check is what Section
  14.2 names).
* All three decisions covered: approve requires the binding; `request_changes`/
  `reassign` are note actions on the review state and follow the standard version
  rule (the plan binds approve to the resolution id — do not invent extra bindings).
* Tests: approve with current `resolution_id` succeeds; approve with an outdated id
  (after a new submission) rejected with zero side effects; concurrent re-submit +
  approve race produces exactly one winner; stale `version` still conflicts per
  Section 8.2.

## Out of scope
* The endpoint itself — MT-3.6-01; the model — MT-3.6-02; feedback flow —
  MT-3.6-03.
* Mobile/web confirmation UX showing task id/branch/diff stats — Section 14.2's
  display half belongs to WP-5.8/WP-4.8.
* Merge queue behavior post-approval — WP-3.7.
* Resolution creation/versioning — WP-3.2.

## Target paths
* `backend/` — approve-path stale-resolution guard
* `backend/tests/` — stale-protection tests
* WP changelog entry (documented error-code choice)

## Acceptance criteria
- [ ] An approval referencing an outdated resolution is rejected with zero T15 side
  effects (WP-3.6 acceptance; Section 14.2 approve safety; FR-AUD-05).
- [ ] The rejection tells the client the resolution changed (refresh and re-review),
  using a Section 9.2 catalog code — choice recorded in the changelog (Section 20.4
  item 5).
- [ ] Approving with the current `resolution_id` proceeds normally through T15.
- [ ] The task-`version` conflict rule from Section 8.2 still applies alongside the
  resolution binding; a race yields exactly one winner (Section 18 concurrency row).
- [ ] Only approve is resolution-bound, per Section 14.2 — no invented bindings for
  other decisions.
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`pytest backend/tests -k stale_resolution -q` — assert outdated-id rejection with
zero side effects, current-id approval, version-conflict interaction, and the
submit/approve race on real Postgres; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 14.2 — Mobile-specific behaviors (approve safety)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.6 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan does not name the specific catalog code for an outdated resolution —
  `VERSION_CONFLICT` fits the stale-resource semantics; confirm against the Section
  9.2 code descriptions during implementation and record the choice rather than
  adding a code.
* If the endpoint accepts approvals without a `resolution_id`, protection is
  silently off — make the field mandatory for approve and test its absence.
* Race windows: check-and-approve must be atomic with T15 (single transaction per
  Section 8.2), or a re-submission between check and write slips through.
