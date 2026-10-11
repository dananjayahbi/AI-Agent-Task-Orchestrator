# MT-6.4-03 — Build the Operations Dashboard View

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.4-03 |
| Title | Build the operations dashboard view |
| Parent WP | WP-6.4 — Metrics, alerts and dashboards (Milestone M6) |
| Requirements | NFR-10 |
| Priority | M |
| Dependencies | MT-6.4-01 (metrics endpoints), MT-6.4-02 (alert rules), WP-4.x web board (Section 13 Overview exists), WP-1.10 SSE for live updates |
| Parent sections | 5.2 (NFR-10), 13.1 (Overview IA), 17 (Dashboards row), 19 (WP-6.4 deliverables, acceptance), 20.4, 20.5 |

## Context
Section 17's Dashboards row is deliberately small: "One operations view (Section 13
Overview can host a simplified version)." Section 19 (WP-6.4) lists "operations view"
among the deliverables. This final slice builds that single view — the place the
operator sees the nine metrics and six alerts from the previous slices at a glance,
fed by MT-6.4-01's endpoints and MT-6.4-02's rules. It deliberately rides the
existing Section 13 Overview rather than inventing a second dashboard surface.

## Inputs / Prerequisites
* MT-6.4-01 — metrics endpoint and the metric semantics document (units, windows,
  labels) the view must render faithfully.
* MT-6.4-02 — alert rules catalog and firing state the view must surface.
* Parent plan Section 13.1 — Overview page IA ("All projects: status cards, active
  agents, tasks needing attention, throughput") — the host for the simplified
  operations version.
* Parent plan Section 16.2/12.2 — owner-only access: operations data is owner-facing,
  behind the existing web session auth; not exposed through the agent/device
  capabilities of Section 12.2 (the matrix grants no agent access to dashboards).
* WP-1.10 SSE — live update channel; the view may refresh via the existing event
  stream or polling, choosing one and recording it.

## Scope (in)
* Add an operations section/view in the web app (Section 13 Overview hosting the
  simplified version) rendering the Section 17 metric list with the semantics from
  MT-6.4-01's document — names and units match the plan, no relabeling.
* Surface current alert state from MT-6.4-02's rules: which of the six alerts are
  firing, with enough context (signal, since when) to act, linking toward the
  MT-6.5-03 runbook that handles it where a runbook exists.
* Show health per Section 17 Health row: live/ready status plus worker/beat
  heartbeat visibility as exposed by MT-6.4-01.
* Keep the view read-only and owner-scoped (Section 12.2 matrix), with loading,
  empty and error states consistent with the web board's existing state discipline
  (Section 13.3).
* Component/integration tests for rendering metrics and firing alerts (Section 18
  Web UI row) and a changelog note (Section 20.4 item 7).

## Out of scope
* Creating or changing metric collection — MT-6.4-01 (the view consumes; it never
  computes its own numbers).
* Alert rule logic/thresholds — MT-6.4-02.
* Mobile operations view — Section 17 says one operations view; the mobile Overview
  (FR-MOB-01) is a separate product surface, not this task.
* Historical metric storage/retention and time-series graphs beyond what the
  endpoints provide — the plan asks for "basic metrics" (NFR-10) and one view, not
  a monitoring product; record any charting library/choice as a decision.
* Editing alerts, acking notifications, or runbook execution from the view —
  surfacing only (Section 17 "One operations view").

## Target paths
* `web/` — operations view/section, components, tests
* `docs/plan/` — only if the view needs a short data-source note (link to metric
  semantics and alert catalog)
* WP changelog entry

## Acceptance criteria
- [ ] One operations view exists, hosted in/near the Section 13 Overview as Section
  17's Dashboards row specifies — no second dashboard surface invented (Section 20.5).
- [ ] The view displays all Section 17 Metrics-row items as provided by MT-6.4-01's
  endpoint, with matching names/units (Section 19 WP-6.4 deliverable "operations
  view"; Section 20.4 item 1).
- [ ] Current state of all six MT-6.4-02 alerts is visible, including the "firing"
  state, and a forced alert (the acceptance test from MT-6.4-02) appears in the view.
- [ ] Health row status (live/ready, worker/beat heartbeat) is visible.
- [ ] View is owner-only and read-only per the Section 12.2 matrix; no secrets or
  attachment content rendered (Section 12.4).
- [ ] Web component/integration tests green in CI (Section 18 Web UI row; Section
  20.4 item 2); changelog note added (item 7).

## Test command
Run the web test suite for the operations view (e.g. the `web/` package test command
scoped to the operations components) confirming metrics render with plan names/units
and alert states display for both resting and forced-firing fixtures; then open the
view against local Compose while MT-6.4-02's forced alert test runs and confirm the
alert appears.

## Attachments
* [Section 17 — Observability and Operations (Dashboards row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.1 — Web information architecture (Overview)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.4 deliverables and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The view must not become a second source of truth — if a displayed number
  disagrees with the metric endpoint, the endpoint wins; test rendering against
  endpoint payloads rather than re-deriving values in the client.
* Section 13.1's Overview already has product scope (status cards, throughput); the
  operations section must not bloat or slow the default Overview — keep it a
  clearly-scoped section (or lazy-loaded route) and note the placement decision.
* Live updates via SSE add a failure mode (stale numbers look healthy) — if polling
  or SSE is chosen, show data freshness so a frozen view is recognizable as stale
  (Section 20.4 item 1 honesty).
