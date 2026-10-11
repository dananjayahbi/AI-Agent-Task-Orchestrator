# MT-5.9-01 — Implement Deep-Link Routing to Review Sheet Behind Biometric Gate

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.9-01 |
| Title | Implement deep-link routing to review sheet behind biometric gate |
| Parent WP | WP-5.9 — Push deep links, notification center and audit log (Milestone M5) |
| Requirements | FR-MOB-04, FR-MOB-05 |
| Priority | M |
| Dependencies | MT-5.4-01, MT-5.4-02 (FCM sender and minimal payloads with ids), MT-5.5-04 (biometric gate and secure storage), MT-5.8-01 … MT-5.8-06 (review sheet complete) |
| Parent sections | 14.1 (Review sheet), 14.2 (Push deep link after unlock; biometric gate), 9.8 (push), 19 (WP-5.9 first slice and acceptance), 20.4, 20.5; ADR-006 |

## Context
Section 14.2 fixes the behavior: "tapping a notification deep-links to the task's
review sheet after unlock." Section 19 (WP-5.9) makes it the WP's acceptance:
"notification tap lands on the correct review sheet after unlock, in cold and warm
start." This is the tap-to-review flow — the mobile half of success criterion 4 in
Section 1.4 (push within 10 s, approve from the phone) — so routing must work from a
killed app (cold start) and a backgrounded app (warm start), and it must never bypass
the biometric gate that protects the device-bound token (Section 14.2; ADR-006).

## Inputs / Prerequisites
* MT-5.4-01/02 — FCM registered per device; payloads carry ids and short title only,
  so routing keys off the task id in the payload (no other data may be assumed).
* MT-5.5-04 — biometric gate: token in platform secure storage, released only after
  biometric success; cold start and configurable inactivity timeout both require
  unlock.
* MT-5.8-04/05 — the review sheet and its resolution-bound confirmation, the
  destination screen.
* Parent plan Section 14.1 — Review sheet screen; navigation shell from MT-5.5-01.
* Parent plan Section 14.2 — deep-link rule and biometric gate wording.
* Local stack with a task that escalates to `in_human_review` (or a fixture event) so
  a real push can be triggered end to end.

## Scope (in)
* Notification-tap handling in both app states: **cold start** — app launches,
  presents the biometric gate before any screen content, then routes to the review
  sheet for the payload's task id; **warm start** — app resumes, applies the unlock
  rule (immediate if freshly unlocked, gate if inactivity timeout fired), then routes.
* Route resolution: fetch the task from the payload id after unlock and open its
  review sheet; while loading, show the standard loading state (Section 20.3 state
  discipline).
* Safe fallback when the task no longer in review is no longer `in_human_review`
  (decided elsewhere first): land the user on a clear state with an explanation
  rather than a broken sheet — the plan does not specify this destination (see risk
  notes).
* Guarantee that no review content or action renders before unlock (gate precedence
  over routing — Section 14.2 "after unlock").
* Widget/integration tests for cold and warm paths with the gate mocked, asserting
  destination and gate ordering; real-device confirmation deferred to MT-5.10-05.
* Changelog note (Section 20.4 item 7).

## Out of scope
* The foreground banner — MT-5.9-02 (it may reuse this routing, but banner rendering
  is separate).
* Notification history/toggles — MT-5.9-03; audit log viewer — MT-5.9-04.
* FCM registration, dedupe, delivery tracking, payload minimization — WP-5.4.
* The review sheet implementation and approve safety — WP-5.8.
* The biometric gate itself — MT-5.5-04 (consumed, not modified).
* Background/remote notification presentation UI beyond tap handling — platform
  defaults.

## Target paths
* `mobile/` — notification tap routing and deep-link resolution module (feature
  folder per Section 14.3)
* `mobile/` tests — cold-start, warm-start and gate-ordering tests (mocked gate)
* WP changelog entry

## Acceptance criteria
- [ ] Tapping a push notification opens the **correct** task's review sheet after
  unlock on cold start — Section 19 WP-5.9 acceptance verbatim.
- [ ] Same on warm start (app backgrounded → tap → resume → unlock → sheet).
- [ ] No review content or action is reachable before biometric success (Section
  14.2; ADR-006 token-release rule).
- [ ] Routing uses only payload ids (ids and short title only — MT-5.4-02 payload
  contract) and fetches the rest post-unlock.
- [ ] A stale/deep-linked task no longer in review degrades to a clear explained
  state instead of an error dead-end (documented behavior).
- [ ] Cold and warm tests green in CI (Section 20.4 items 1–2); real-device check
  listed for MT-5.10-05; changelog note added (item 7).

## Test command
From `mobile/`: `flutter analyze` plus the mobile test suite filtered to deep-link
routing (for example `flutter test --dart-define=test_filter=deeplink` or the
project's equivalent) — asserts gate-before-content ordering, correct destination on
cold and warm fixtures, and the stale-task fallback.

## Attachments
* [Section 14.2 — Mobile-specific behaviors (push deep link, biometric gate)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.9 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 1.4 — Success criterion 4 (push + phone approve)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan does not name the stale-task fallback destination — pick the least
  surprising one (e.g. home with a message), record the choice in the changelog; do
  not invent a new screen in this task.
* OS notification tap semantics differ between Android and iOS (cold-start payload
  delivery timing especially) — test both platforms' cold start; MT-5.10-05 is the
  real-device backstop.
* Payload ids must never carry review content (MT-5.4-02 minimization) — if routing
  seems to need more than an id, the fix belongs in WP-5.4's payload contract, not
  here.
