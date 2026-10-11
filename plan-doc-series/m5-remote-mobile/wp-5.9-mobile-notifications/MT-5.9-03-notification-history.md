# MT-5.9-03 — Implement Notification History With Per-Type Toggles

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.9-03 |
| Title | Implement notification history with per-type toggles |
| Parent WP | WP-5.9 — Push deep links, notification center and audit log (Milestone M5) |
| Requirements | FR-MOB-04 |
| Priority | M |
| Dependencies | MT-5.4-05 (per-event-type notification preferences on the backend), MT-5.5-03 (generated API client), MT-5.9-02 (banner entries feed history) |
| Parent sections | 14.1 (Notifications: history of alerts, per-event-type toggles), 9.8 (preferences), 14.2 (offline behavior), 19 (WP-5.9 third slice), 20.4, 20.5; 22 (OQ-13) |

## Context
Section 14.1's Notifications screen has exactly two parts: "History of alerts,
per-event-type toggles." The history answers "what was I alerted about while I
wasn't looking" (fed by delivered pushes and the MT-5.9-02 banner); the toggles are
the mobile surface of WP-5.4's per-event-type preferences (MT-5.4-05), so one
preference set serves web account settings and the phone. OQ-13 (decided) bounds the
feature: "per-event toggles only; digests off by default" — no digest scheduling
here. NFR-03 (push dispatch) and FR-MOB-04 (push on `in_human_review`) are the
behaviors the toggles gate.

## Inputs / Prerequisites
* MT-5.4-05 — backend per-event-type notification preferences and their endpoints
  (the source of truth the toggles edit).
* MT-5.5-03 — generated typed client from the OpenAPI schema (NFR-11) for the
  preferences calls; MT-5.9-02 — banner records entries for the history.
* Parent plan Section 14.1 — the screen definition; Section 14.2 — offline behavior
  (mutating actions require connectivity, show a clear offline state, no queued
  actions).
* Parent plan OQ-13 — per-event toggles only, digests off (decided).
* Event/push types as defined by Section 9.8 and WP-5.4's preferences model — the
  toggle list mirrors them exactly; do not invent types.

## Scope (in)
* The Notifications screen: a reverse-chronological history of received alerts
  (per-event type, task reference, time), rendered from locally recorded deliveries
  (banner/system-notification receipts — the plan does not require a server-side
  notification inbox; see risk notes), with loading/empty states (Section 20.3).
* Per-event-type toggles bound to the MT-5.4-05 backend preferences: opening the
  screen loads current values; changing one persists via the API and reflects
  immediately; a failed save surfaces an error and restores the previous value.
* Offline behavior per Section 14.2: history (read-only cache) still displays;
  toggling shows the clear offline state and does not queue the mutation.
* Navigation entry to the screen per Section 14.1 (Notifications area) alongside the
  audit log entry from MT-5.9-04.
* Widget/integration tests: history rendering from fixtures, toggle load/save/failure
  paths, offline refusal.
* Changelog note (Section 20.4 item 7).

## Out of scope
* Backend preference model/endpoints and push dispatch — WP-5.4 (MT-5.4-05).
* Banner rendering and tap routing — MT-5.9-01/02 (history consumes their receipts).
* Digests or batching of notifications — explicitly out (OQ-13 decided).
* Web notification preferences UI — WP-4.x account settings (same backend data).
* Audit log viewer — MT-5.9-04.
* Read/unread state machines or per-message actions — not specified in Section 14.1;
  do not invent (see risk notes).

## Target paths
* `mobile/` — notifications feature folder (history screen, toggle widgets,
  preferences repository)
* `mobile/` tests — history, toggle persistence, offline and failure-path tests
* WP changelog entry

## Acceptance criteria
- [ ] The Notifications screen shows alert history and per-event-type toggles,
  matching Section 14.1 exactly (no additional concepts).
- [ ] Toggles edit the backend per-event-type preferences from MT-5.4-05 — one
  source of truth shared with web (FR-MOB-04; Section 9.8).
- [ ] Only the event types the backend defines appear as toggles; no invented types
  (Section 20.5 traceability).
- [ ] Offline: history readable, toggles refuse with a clear offline state, nothing
  queued (Section 14.2).
- [ ] Save failure restores prior state with an error surfaced (Section 9.2 error
  mapping discipline).
- [ ] Tests green in CI (Section 20.4 items 1–2); changelog note added (item 7).

## Test command
From `mobile/`: `flutter analyze` plus the mobile test suite filtered to
notifications (for example `flutter test --dart-define=test_filter=notifications`
or the project's equivalent) — asserts history rendering, toggle load/save/failure,
and offline refusal.

## Attachments
* [Section 14.1 — Notifications screen](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.9 slices](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 22 — OQ-13 (per-event toggles only)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan defines "history of alerts" without saying where it is stored —
  recording locally from delivered notifications is the reading consistent with
  Section 14.1 and the offline cache rule; if a server-backed inbox is expected
  instead, that is an open point to raise before building (no OQ covers it).
* "Alerts" scope is also unstated (all event types vs only pushes) — mirror the
  toggle types and record the interpretation in the changelog.
* The generated client (NFR-11) must have the preferences endpoints already in the
  OpenAPI schema; if they are missing, fix belongs in WP-5.4/backend, not by calling
  raw URLs here (contract discipline, Section 18 Contract row).
