# MT-5.6-01 — Implement dashboard summary consumption and project cards

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.6-01 |
| Title | Implement dashboard summary consumption and project cards |
| Parent WP | WP-5.6 — Overview dashboard and mobile Kanban (Milestone M5) |
| Requirements | FR-MOB-01, FR-MOB-02 |
| Priority | M |
| Dependencies | WP-5.5 complete (MT-5.5-03 typed client; MT-5.5-04 secure storage/biometric gate) |
| Parent sections | 9.2 (GET /dashboard/summary), 14.1 (Home / Overview), 14.2 (offline cache), 19 (WP-5.6), 20.3, 20.4, 20.5 |

## Context
FR-MOB-01: "Overview dashboard: per-project status cards, velocity, active agent
counts." Section 14.1's Home / Overview row specifies "Project cards (counts per
state, velocity, active agents), 'needs review' banner". The backend surface is
`GET /dashboard/summary` (Section 9.2, Owner). Section 19 WP-5.6 lists "dashboard
endpoint usage, project cards" as deliverables. This micro-task builds the mobile
home screen's data consumption and card UI, behind the biometric gate from WP-5.5.

## Inputs / Prerequisites
* Parent plan Section 9.2 — `GET /dashboard/summary` (Owner) endpoint.
* Parent plan Section 14.1 — Home / Overview contents (project cards with per-state
  counts, velocity, active agents; "needs review" banner).
* Parent plan Section 14.2 — offline behavior: read-only cache of the last overview;
  mutating actions require connectivity (no queued decisions).
* WP-5.5 — generated typed client (MT-5.5-03) and biometric gate (MT-5.5-04).

## Scope (in)
* Home/Overview screen consuming `GET /dashboard/summary` through the generated typed
  client (single source: OpenAPI — NFR-11).
* Project cards rendering per Section 14.1: per-state counts, velocity, active agent
  count; card tap navigates toward that project's board (navigation target is
  MT-5.6-02's selector context — wire the handoff, not the board itself).
* "Needs review" banner driven by the summary's `in_human_review` signal
  (Section 14.1; ties to FR-MOB-04's escalation visibility).
* Screen states kept separate (Section 20.3): loading skeleton, empty (no projects),
  error (canonical codes mapped to friendly messages), and stale-from-cache
  presentation when offline (Section 14.2 read-only cache).
* Read-only offline cache of the last successful overview (Section 14.2).
* Widget/unit tests: card content from summary fixtures, banner presence/absence,
  loading/empty/error/offline states.
* Add a WP changelog note.

## Out of scope
* Push notifications and deep links — WP-5.4 / WP-5.9 (banner here is passive).
* The project selector and board — MT-5.6-02 / MT-5.6-03.
* Live updates on the dashboard — MT-5.6-04 (initial version renders fetched data;
  stream patching comes with the board slice unless trivially shared).
* Velocity computation — comes from the summary payload; do not recompute client-side
  (Section 9.2 is the source).
* Web overview route — Section 13.1 (M4).

## Target paths
* `mobile/` (home/overview screen, project card widgets, summary repository/cache)
* `mobile/` tests (dashboard and card tests)
* WP changelog entry

## Acceptance criteria
- [ ] The Home / Overview screen shows project cards with per-state counts, velocity
  and active agent counts, plus the "needs review" banner — Section 14.1 verbatim
  contents; FR-MOB-01.
- [ ] Data comes from `GET /dashboard/summary` via the generated typed client — no
  bespoke fetch paths or hand-built response types (Section 9.2; NFR-11).
- [ ] Loading, empty, error and offline-stale states are separate and testable
  (Section 20.3; Section 14.2 read-only offline cache).
- [ ] Errors map from canonical codes to friendly messages (Section 9.2 catalog;
  Section 20.4 item 5).
- [ ] The screen sits behind the WP-5.5 biometric gate (Section 14.2 — secure token
  released only after unlock).
- [ ] Read-only offline: last overview shown from cache with no mutating affordance
  (Section 14.2).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the mobile test suite filtered to the dashboard (for example
`flutter test --dart-define=test_filter=dashboard` or the project's equivalent) and
confirm: card fields from a summary fixture, banner logic, loading/empty/error
offline states, and gate gating; then the full mobile suite stays green.

## Attachments
* [Section 14.1 — Navigation and screens (Home / Overview)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — Dashboard endpoint](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.6 deliverables](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The exact JSON shape of `/dashboard/summary` is not detailed in the plan — treat
  the generated OpenAPI client as the contract; if the backend response lacks
  Section 14.1 fields (velocity, active agents), that is a backend gap to raise
  (OQ-xx), not a reason to assemble numbers client-side from extra calls.
* Offline cache freshness is unspecified — show cached data with a clear
  stale/offline indication (Section 14.2's "clear offline state") and never present
  it as live.
