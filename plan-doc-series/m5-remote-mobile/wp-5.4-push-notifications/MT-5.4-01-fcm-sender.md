# MT-5.4-01 — Configure FCM credentials and the worker-side sender

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.4-01 |
| Title | Configure FCM credentials and the worker-side sender |
| Parent WP | WP-5.4 — Push notifications (FCM) (Milestone M5) |
| Requirements | FR-MOB-04, NFR-03; ADR-003 |
| Priority | M |
| Dependencies | WP-3.9 (escalation events as the trigger source), WP-1.7 (workers), WP-5.3 (device tokens), WP-1.7/9.10 (config conventions) |
| Parent sections | 9.8, 9.9, 9.10, 19 (WP-5.4), 20.4, 20.5 |

## Context
Section 9.8: "Dispatch via FCM from the worker" — push never goes from the web
process or an end-user device; the Celery worker (ADR-003) sends. Section 9.9's
background-job table has "Push dispatch | on event | Dedupe + retry". Section 9.10
lists FCM credentials among the environment-driven config groups, with startup
validation that fails fast on missing required values. WP-5.4's acceptance:
"escalation produces one push within 10 s" (NFR-03: push dispatch within 10 s of the
triggering transition). This first slice establishes the credentials, the config
contract, and the sender that the later payload/dedupe/tracking tasks build on.

## Inputs / Prerequisites
* Parent plan Section 9.8 — FCM-from-worker dispatch rule.
* Parent plan Section 9.9 — the push dispatch job (on event; dedupe + retry).
* Parent plan Section 9.10 — FCM credentials in environment config; fail-fast
  startup validation.
* WP-3.9 — `review.requested` events (primary trigger per Section 9.8).
* WP-5.3 — device registration and device-bound tokens supplying FCM tokens per
  device.
* WP-1.7 — worker/beat infrastructure; WP-0.2 — Compose service environment.

## Scope (in)
* FCM credentials as environment-driven configuration per Section 9.10: variable
  names documented in the environment template, real values only outside Git
  (Section 16.2, Section 20.4 item 3), fail-fast validation when push is enabled.
* The worker-side sender module: given an event and a device token, dispatch a push
  via FCM with retry/backoff for transient failures (Section 9.9 "Dedupe + retry" —
  the dedupe decision itself is MT-5.4-03).
* Wiring the Section 9.9 push-dispatch job: consuming relevant events
  (`in_human_review` entry per Section 9.8; merge failure; retry exhaustion) and
  invoking the sender — trigger selection honors WP-5.4's preferences task
  (MT-5.4-05) as a downstream filter, with all triggers active until then.
* Latency posture: dispatch starts on event, aiming at NFR-03's 10-second window —
  no batching delays in the critical path.
* Tests: credentials validation (missing → fail fast when enabled, clean skip when
  push disabled); sender unit tests against a mocked FCM transport (success,
  transient-failure retry, permanent failure classification stub for MT-5.4-04);
  job-to-sender wiring for an escalation event.

## Out of scope
* Payload field minimization — MT-5.4-02.
* Dedupe keys — MT-5.4-03; delivery tracking and token pruning — MT-5.4-04;
  preferences — MT-5.4-05.
* Event emission — WP-3.9; device registration/token lifecycle — WP-5.3.
* The Flutter side (FCM token registration, message handling) — WP-5.5/WP-5.9.
* Real FCM project setup in CI — credentials stay local/prod environment concerns.

## Target paths
* `backend/` — FCM configuration, worker-side sender, push dispatch job wiring
* `backend/tests/` — configuration and sender tests
* Environment template (variable names only)
* WP changelog entry

## Acceptance criteria
- [ ] FCM credentials are environment-driven per Section 9.10 with documented
  variable names; startup fails fast when push is enabled and credentials are
  missing/weak (Sections 9.10, 16.2).
- [ ] No credential values are committed (Section 20.4 item 3) — template contains
  names and placeholders only.
- [ ] The sender runs in the worker (ADR-003 posture; Section 9.8 "dispatch via FCM
  from the worker") with transient-failure retry/backoff per Section 9.9.
- [ ] The push-dispatch job consumes an escalation event (`review.requested`,
  Section 9.6/9.8) and invokes the sender — with an end-to-end path testable for
  the NFR-03 10-second target.
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`pytest backend/tests -k fcm_sender -q` — assert fail-fast config validation,
sender retry behavior against a mocked transport, and job wiring from a
`review.requested` event to a send attempt; then `pytest backend/tests -q` stays
green.

## Attachments
* [Section 9.8 — Notifications](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.10 — Configuration (environment-driven)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* FCM setup requires an external project/service account — real credential
  provisioning is an operator step outside the repo; the task ships config shape and
  validation, not secrets (Section 20.4 item 3).
* Choosing the FCM client library/transport is a dependency decision — record the
  pick in the changelog; keep it behind the sender interface so MT-5.4-02..04 stay
  testable without it.
* If push is disabled (no credentials), the system must run cleanly without
  degrading non-notification flows — a fail-fast that bricks the whole stack on a
  push-only setting would be wrong; scope validation to enabled push.
