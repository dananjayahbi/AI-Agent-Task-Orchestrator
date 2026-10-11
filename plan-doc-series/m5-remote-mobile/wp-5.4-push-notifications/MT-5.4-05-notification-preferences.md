# MT-5.4-05 — Implement per-event-type notification preferences

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.4-05 |
| Title | Implement per-event-type notification preferences |
| Parent WP | WP-5.4 — Push notifications (FCM) (Milestone M5) |
| Requirements | FR-MOB-04; NFR-03 |
| Priority | M |
| Dependencies | MT-5.4-01 (sender), MT-5.4-03 (dedupe interplay), WP-1.1 (model/migration conventions), WP-5.9 (toggle UI consumer) |
| Parent sections | 9.8, 13.1, 14.1, 19 (WP-5.4), 22 (OQ-13), 20.4, 20.5 |

## Context
Section 14.1's Notifications screen has "per-event-type toggles"; Section 13.1's
Account settings include "notification preferences". Section 9.8's triggers define
the event types involved: `in_human_review` entry (all reasons), merge failure,
retry exhaustion, and an optional digest of completions. OQ-13 (Section 22):
"Notification digests for completed work?" — recommended default "Off by default;
per-event toggles only." So preferences are per-event-type switches over the
Section 9.8 trigger set, consulted before every send — with the digest staying off
unless the owner opts in.

## Inputs / Prerequisites
* Parent plan Section 9.8 — trigger set (verbatim) and dispatch flow.
* Parent plan Sections 13.1, 14.1 — where preferences are edited (web account
  settings; mobile Notifications screen toggles).
* OQ-13 (Section 22) — digest default off; per-event toggles only.
* WP-1.1 — model/migration conventions; MT-5.4-01 — the dispatch path that consults
  preferences; MT-5.4-03 — dedupe interplay.
* WP-5.9 — the mobile toggle UI consuming an endpoint (and WP-4.x account settings
  on web).

## Scope (in)
* A preference record: per event type, enabled/disabled, for the Section 9.8 trigger
  set (`in_human_review` entry, merge failure, retry exhaustion, and the optional
  completion digest — digest defaulting to **off** per OQ-13; escalation triggers
  defaulting to **on** so FR-MOB-04 works out of the box).
* Scope of application: account-level per-event-type preferences (the Section 13.1
  Account settings surface; mobile toggles edit the same record) — one source of
  truth both clients read/write via the API.
* Consultation in the dispatch path: preferences are checked after trigger
  selection and before dedupe/send, so a disabled type records no send attempt;
  re-enabling later does not retro-fire suppressed events.
* A read/update endpoint for preferences with schema-diff review (Section 20.4
  item 4), authorized per Section 12.2 (Owner; Device may read/adjust notification
  preferences as the mobile toggles require — confirm against the matrix and record
  the choice).
* Tests: defaults (escalations on, digest off); disabling a type suppresses sends
  and leaves other types unaffected; enabling restores sends for new events only;
  per-event isolation; endpoint read/update round trip; dispatch-path consultation
  ordering (no FCM call for disabled types).

## Out of scope
* The sender, dedupe, tracking, payloads — MT-5.4-01..04.
* Toggle UIs (web account settings, mobile Notifications screen) — WP-5.9 (mobile)
  and the web settings owner WP-4.2/WP-4.x; this task is storage, endpoint and
  dispatch consultation.
* Building the completion digest itself — OQ-13 keeps it off; when built, it is a
  separate task.
* In-app banner/history behavior — WP-5.9 (preferences govern push dispatch here).

## Target paths
* `backend/` — notification preference model, endpoint, dispatch-path consultation
* `backend/tests/` — preference and consultation tests
* OpenAPI document (endpoint; schema diff reviewed)
* WP changelog entry

## Acceptance criteria
- [ ] Per-event-type preferences exist for the Section 9.8 trigger set, with
  escalation triggers defaulting on and the completion digest defaulting off
  (FR-MOB-04 works by default; OQ-13 default honored).
- [ ] The dispatch path consults preferences before dedupe/send: a disabled type
  produces zero FCM attempts, other types unaffected (Section 9.8 flow).
- [ ] Preferences are one account-level record read and written by both web
  (Section 13.1) and mobile (Section 14.1) surfaces via the documented endpoint.
- [ ] Re-enabling a type notifies only future events — suppressed events are not
  retro-fired.
- [ ] Endpoint authorization follows the Section 12.2 matrix; OpenAPI updated with
  schema diff reviewed (Section 20.4 item 4); lint/type/tests green (item 2);
  changelog note added (item 7).

## Test command
`pytest backend/tests -k notification_preferences -q` — assert defaults, per-type
suppression and isolation in the dispatch path, no-FCM-call for disabled types,
endpoint round trip and authorization; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 9.8 — Notifications (triggers)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 22 — OQ-13 (digest default)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan places preference *surfaces* in Section 13.1/14.1 but does not fix the
  storage granularity (account vs per-device) — account-level fits both named
  surfaces; if per-device preferences are wanted, that is an owner decision, not an
  implementation detail.
* Consultation ordering matters: checking preferences after dedupe could record a
  suppressed send in tracking and skew the Section 17 success-rate metric — test the
  order.
* Allowing every escalation type to be disabled could mute FR-MOB-04 entirely;
  the plan gives toggles for event types without carving out mandatory ones — keep
  defaults on and raise a "mandatory escalation" policy question rather than
  hard-coding one.
