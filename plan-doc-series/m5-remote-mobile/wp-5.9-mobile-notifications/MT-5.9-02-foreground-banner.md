# MT-5.9-02 — Implement the Foreground Notification Banner

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.9-02 |
| Title | Implement the foreground notification banner |
| Parent WP | WP-5.9 — Push deep links, notification center and audit log (Milestone M5) |
| Requirements | FR-MOB-04 |
| Priority | M |
| Dependencies | MT-5.4-01, MT-5.4-02, MT-5.4-03 (FCM sender, minimal payload, dedupe), MT-5.5-04 (gate state), MT-5.9-01 (tap routing reused) |
| Parent sections | 14.2 (Foreground messages display an in-app banner), 14.1 (Notifications), 9.8 (push dispatch), 19 (WP-5.9 second slice), 20.4, 20.5 |

## Context
Section 14.2: "Foreground messages display an in-app banner." When the app is
foregrounded, the OS does not present the system notification, so the plan requires
an in-app banner instead — otherwise an escalation arriving while the owner watches
the board would be invisible (undermining NFR-03's 10 s push visibility on the
foreground path). The banner consumes the same minimal payload as the system
notification (MT-5.4-02: ids and short title only) and reuses MT-5.9-01's tap
routing so tapping the banner behaves exactly like tapping the notification.

## Inputs / Prerequisites
* MT-5.4-01 — FCM token registered per device and foreground message callback
  available; MT-5.4-02 — minimal payload shape; MT-5.4-03 — dedupe keys (event type,
  task id, state version) so a re-sent event does not double-render.
* MT-5.9-01 — notification-tap routing (banner tap targets the same destination).
* MT-5.5-04 — current gate state (locked/unlocked) to avoid showing actionable
  content while locked.
* Parent plan Section 14.2 — the verbatim requirement; Section 14.1 — the
  Notifications area the history (MT-5.9-03) will store what the banner displayed.
* Existing foreground SSE updates (MT-5.6-04): the board already live-updates; the
  banner is an additional signal, not a substitute.

## Scope (in)
* A foreground message handler that renders an in-app banner for a received FCM
  message while the app is foregrounded, showing only payload content (short title +
  what the ids resolve to on tap).
* Banner tap → same deep-link routing as a notification tap (MT-5.9-01): unlock if
  needed, then open the task's review sheet.
* Dedupe respect: a message already presented (per MT-5.4-03 dedupe keys) does not
  render twice — banner and system notification never double-fire for one event
  (foreground vs background presentation is the OS-side split; the app-side handler
  must not re-present a message it already showed).
* No actionable content while the biometric gate is locked — banner shows nothing
  sensitive pre-unlock (consistent with Section 14.2 gate semantics).
* Dismissal behavior: a defined, simple rule (e.g. tap to act, explicit dismiss, or
  auto-dismiss after a short delay — the plan does not specify; choose one, record
  it) with a transition that does not block board interaction.
* Recording the presented alert so MT-5.9-03's history can list it.
* Widget/integration tests: foreground receive → banner shown; tap → routing;
  duplicate message → no double banner; locked state → no sensitive content.
* Changelog note (Section 20.4 item 7).

## Out of scope
* Deep-link routing implementation — MT-5.9-01 (reused, not modified beyond a tap
  callback).
* Notification history list and per-type toggles — MT-5.9-03 (banner only hands it
  entries).
* Backend dispatch, dedupe keys, delivery tracking, preferences — WP-5.4.
* Background presentation (system notification tray) — OS behavior via FCM.
* Audit log viewer — MT-5.9-04.

## Target paths
* `mobile/` — foreground message handler and banner widget (notifications feature
  folder)
* `mobile/` tests — banner rendering, tap routing, dedupe and gate-state tests
* WP changelog entry

## Acceptance criteria
- [ ] A foregrounded FCM message displays an in-app banner with payload content only
  (Section 14.2 verbatim; MT-5.4-02 payload contract).
- [ ] Banner tap routes exactly like a notification tap — unlock then review sheet
  (MT-5.9-01 behavior preserved).
- [ ] A message whose dedupe key was already presented does not render a second
  banner (MT-5.4-03).
- [ ] While the gate is locked, the banner exposes no review content (Section 14.2).
- [ ] Banner presence is recorded for notification history (feeds MT-5.9-03).
- [ ] Tests green in CI (Section 20.4 items 1–2); dismissal rule recorded in the
  changelog (item 7, plus this task's chosen behavior).

## Test command
From `mobile/`: `flutter analyze` plus the mobile test suite filtered to the banner
(for example `flutter test --dart-define=test_filter=banner` or the project's
equivalent) — asserts foreground receive → banner, tap → review-sheet route, dedupe
no-double-render, locked → no sensitive content.

## Attachments
* [Section 14.2 — Mobile-specific behaviors (foreground banner)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.9 slices](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [NFR-03 — Push dispatch within 10 s](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan does not specify banner dismissal/auto-hide timing — choose the least
  intrusive rule, document it in the changelog; do not treat a chosen default as a
  plan requirement.
* Banner + SSE live update will often show the same transition twice (stream patch
  and push) — that is by design (different channels), but ensure the banner does not
  fight the gate or duplicate within itself (dedupe), or it reads as a bug.
* If the app receives messages while locked, minimal payload is the only protection —
  never enrich banner text from fetched data before unlock.
