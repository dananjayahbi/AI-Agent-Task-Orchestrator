# MT-5.4-04 — Implement delivery tracking and invalid-token pruning

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.4-04 |
| Title | Implement delivery tracking and invalid-token pruning |
| Parent WP | WP-5.4 — Push notifications (FCM) (Milestone M5) |
| Requirements | FR-MOB-04, NFR-03 |
| Priority | M |
| Dependencies | MT-5.4-01 (sender), MT-5.4-03 (dedupe interplay), WP-5.3 (device/token records), WP-1.7 (worker) |
| Parent sections | 9.8, 17, 9.9, 19 (WP-5.4), 20.4, 20.5 |

## Context
Section 9.8: "Delivery status tracked; invalid push tokens are pruned." WP-5.4's
deliverables list "delivery tracking" and "token pruning". Section 17 makes push
operations observable: metrics include push success rate, and alerts include push
failures. Pruning protects the device registry (WP-5.3) from dead tokens FCM rejects
(uninstalled apps, expired tokens) — a stale token otherwise retried forever inflates
latency and muddies the success-rate metric.

## Inputs / Prerequisites
* Parent plan Section 9.8 — tracking and pruning requirements (verbatim).
* Parent plan Section 17 — push success-rate metric and push-failure alert rows.
* Parent plan Section 9.9 — push dispatch job (retry context for status recording).
* WP-5.3 — device registration and token storage/revocation model.
* MT-5.4-01 — sender responses (success/transient/permanent classifications).
* MT-5.4-03 — dedupe records interplay (pruning must not resurrect suppressed
  sends).

## Scope (in)
* Per-send delivery records: device, event key (event type, task id, state version —
  aligning with MT-5.4-03), send attempt outcome (accepted, transient failure,
  permanent failure), timestamp, and FCM's response classification — enough to
  compute push success rate (Section 17) without storing payload content
  (Section 12.4).
* Invalid-token handling: classify FCM responses that mean the token is dead
  (unregistered/invalid) as permanent; on such a response, prune the token from the
  device record (marking the device's push token invalid/absent) so future sends skip
  it — never delete the device's other state or auth (device revocation remains
  WP-5.3's owner-initiated action).
* Transient failures remain retryable (MT-5.4-01 backoff) with attempts recorded;
  permanent non-token failures recorded without endless retry.
* Metrics/alert hooks: expose the success-rate numerator/denominator and failure
  counts for Section 17's push success-rate metric and push-failure alert (wiring
  finalized with WP-6.4; keep a clean query interface here).
* Tests: accepted → success recorded; transient → retry with attempts recorded;
  invalid-token response → token pruned, subsequent dispatches skip the device, no
  crash; permanent non-token failure → recorded, not retried forever; no payload
  text in tracking rows; dedupe interaction unchanged after pruning.

## Out of scope
* The sender and FCM transport — MT-5.4-01; payload contents — MT-5.4-02; dedupe
  logic — MT-5.4-03.
* Device registration, revocation UI, biometric gate — WP-5.3.
* Dashboard rendering and alert delivery — WP-6.4 (Section 17) — this task provides
  the data.
* Client-side token refresh — WP-5.5/WP-5.9 (a re-registered token must be picked up
  by WP-5.3's registration path).

## Target paths
* `backend/` — delivery tracking records, invalid-token pruning in the send path
* `backend/tests/` — tracking and pruning tests
* WP changelog entry

## Acceptance criteria
- [ ] Every send records delivery status (outcome + attempt history) per device and
  event key — Section 9.8 "Delivery status tracked".
- [ ] An FCM invalid-token response prunes the token so future dispatches skip that
  device without errors — Section 9.8 "invalid push tokens are pruned".
- [ ] Pruning touches only the push token, never device auth/registration state
  (WP-5.3 remains the revocation owner).
- [ ] Transient failures retry with recorded attempts; permanent failures stop
  retrying and are recorded (Section 9.9 "Dedupe + retry").
- [ ] Push success rate and failure counts are queryable for Section 17's metric and
  alert; no payload content is stored in tracking rows (Section 12.4).
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`pytest backend/tests -k push_delivery_tracking -q` — assert success/transient/
permanent outcome recording, invalid-token pruning with subsequent skip, no
endless-retry on permanent failures, metric queries, and payload-free rows; then
`pytest backend/tests -q` stays green.

## Attachments
* [Section 9.8 — Notifications (tracking, pruning)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 17 — Observability and Operations](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Which FCM responses mean "invalid token" must follow FCM's documented codes —
  misclassifying a transient error as permanent silently drops a working device;
  keep the classification table explicit and tested.
* Tracking rows are operational data, not audit data — define retention consistent
  with the Section 12.4/OQ-10 posture and record it; do not let them accumulate
  indefinitely by default.
* Pruning on a single ambiguous failure is destructive-ish — prune only on
  definitively permanent invalid-token signals, retry ambiguity otherwise.
