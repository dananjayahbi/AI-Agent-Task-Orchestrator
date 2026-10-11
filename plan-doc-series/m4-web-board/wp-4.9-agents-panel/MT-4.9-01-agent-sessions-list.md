# MT-4.9-01 — Implement the live agent sessions list

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.9-01 |
| Title | Implement the live agent sessions list |
| Parent WP | WP-4.9 — Agents and leases panel (Milestone M4) |
| Requirements | FR-WEB-07 |
| Priority | S |
| Dependencies | WP-4.3 complete (stream hook MT-4.3-04/05); WP-1.6 complete (claims/sessions); WP-4.1 complete (auth, API client) |
| Parent sections | 13.1 (Agents route), 7.2 (Agent Session), 9.6 (`agent.session_started|ended`, `task.claimed|released`), 19 (WP-4.9), 20.3, 20.4, 20.5 |

## Context
Section 13.1's Agents route shows "Live sessions, current leases, countdowns, stalled
markers" — this micro-task delivers the first element: the live sessions list. The
data model is the Agent Session entity (Section 7.2: `agent_label`, `client_name`,
`capability` `vision`/`text_only`/`unknown`, `transport` `stdio`/`http`,
`started_at`, `last_seen_at`, `ended_at`), and liveness events are
`agent.session_started|ended` plus `task.claimed`/`task.released` (Section 9.6
catalog). Lease countdowns and stalled markers are the sibling tasks MT-4.9-02/03.

## Inputs / Prerequisites
* Parent plan Section 13.1 — Agents route scope.
* Parent plan Section 7.2 — Agent Session fields.
* Parent plan Section 9.6 — session and claim events; WP-4.3 hook delivers them.
* Parent plan Section 9.2 — task listing for current-lease joins; session read
  surface (see Risk notes).
* WP-1.6 — claim/session lifecycle writing these records.

## Scope (in)
* The Agents page listing sessions: active (no `ended_at`) and recently ended, per
  project, showing `agent_label`, `client_name`, `capability`, `transport`,
  `started_at`, `last_seen_at`.
* Live maintenance via SSE: `agent.session_started` adds rows, `agent.session_ended`
  marks them ended, `task.claimed`/`task.released` attach the current task/lease to a
  session row (Sections 9.6, 13.3 cache patching through the WP-4.3 hook).
* Session-to-task join: which task (id, role coder/auditor) a session currently holds
  — from task worker fields (`worker_session_id`, `claimed_role`, Section 7.2) —
  which feeds MT-4.9-02/03.
* Loading/empty ("no active sessions")/error states with catalog-only error codes
  (Sections 20.3, 20.4 item 5); reconnect reconciliation via last-event-id resume
  (Section 9.6).
* Component tests: fixture sessions render, started/ended event handling, claim join,
  empty/error states, reconnect dedupe.
* A WP changelog note.

## Out of scope
* Lease countdown timers — MT-4.9-02.
* Stalled indicators — MT-4.9-03.
* Session creation/termination — bridge/WP-2.x, WP-1.6.
* Token/session management UIs — WP-4.2 (API tokens are a different concept from
  agent sessions).
* Overview page active-agent cards — WP-5.6 territory (mobile) / WP-4.2 overview.

## Target paths
* `web/` (Agents route page and session list components)
* `web/` tests (session list tests with fixture events)
* WP changelog entry

## Acceptance criteria
- [ ] The Agents page lists sessions with the Section 7.2 Agent Session display
  fields and separates active from ended sessions.
- [ ] The list is live: `agent.session_started|ended` and `task.claimed|released`
  update rows through the WP-4.3 hook and cache patching — no polling
  (Sections 9.6, 13.3).
- [ ] Each active session shows its current task/lease join from canonical task
  fields (`worker_session_id`, `claimed_role`) — no invented identifiers
  (Section 7.2; Section 20.5).
- [ ] Reconnect replay does not duplicate or drop session rows (Section 9.6
  no-gaps/no-duplicates).
- [ ] Loading, empty and error states handled (Section 20.3); catalog-only error
  codes (Section 20.4 item 5).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to sessions (for example `npm test -- -t session`)
and confirm fixture rendering, start/end event handling, claim join, dedupe after
replay, and empty/error states; then the full web suite stays green.

## Attachments
* [Section 13.1 — Information architecture (Agents row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Entities (Agent Session)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.6 — Event catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Section 9.2 documents `POST /agent-sessions` (bridge) but no Owner-facing
  `GET /agent-sessions` list endpoint — the initial page load needs a read source.
  Options: derive from task/lease state plus `GET /events` history, or add a
  read endpoint (OpenAPI contract change, Section 20.4 item 4). Confirm what exists
  before building; do not fan out undocumented requests.
* "Live" depends on session liveness events that only fire on transitions —
  `last_seen_at` staleness display must come from polled/claim data, not invented
  heartbeats (Section 13.1 says live sessions, not heartbeats).
* Ended-session retention/limits for the list are unspecified — paginate newest-first
  rather than unbounded growth (RISK-13).
