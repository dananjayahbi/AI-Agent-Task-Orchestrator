# MT-5.4-03 — Implement dedupe keys (event type, task id, state version)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.4-03 |
| Title | Implement dedupe keys (event type, task id, state version) |
| Parent WP | WP-5.4 — Push notifications (FCM) (Milestone M5) |
| Requirements | FR-MOB-04, NFR-03; ADR-012 |
| Priority | M |
| Dependencies | MT-5.4-01 (sender), MT-5.4-02 (payload carries the key fields), WP-1.9 (event ids) |
| Parent sections | 9.8, 9.9, 19 (WP-5.4), 18, 20.4, 20.5 |

## Context
Section 9.8: "per-device dedupe key `(event type, task id, state version)` prevents
duplicates on retries." Section 9.9's push job is "on event | Dedupe + retry".
WP-5.4's acceptance: "escalation produces one push within 10 s; retried event does
not duplicate." The retry story (Section 9.8 job retries, MT-5.4-01's transient
backoff, and re-publication after worker crashes) is exactly where duplicates arise —
the same event processed twice must reach a given device once.

## Inputs / Prerequisites
* Parent plan Section 9.8 — the dedupe key, verbatim, and its per-device scope.
* Parent plan Section 9.9 — push dispatch job (on event; dedupe + retry).
* MT-5.4-01 — sender and retry loop; MT-5.4-02 — payload containing event type,
  `task_id`, `task_version`.
* Section 9.6 — event envelope supplying `type`, `task_id`, and `data.task_version`.
* Section 18 concurrency row — duplicate-processing test patterns (real backend).

## Scope (in)
* A per-device dedupe record keyed exactly by `(event type, task id, state version)`
  — checked before each FCM send; a key already sent to that device suppresses the
  duplicate.
* Where the check sits: between preference/trigger evaluation and the actual send,
  so a retried job, a re-delivered event, or a worker restart mid-dispatch still
  yields one push per device per key (the acceptance's "retried event does not
  duplicate").
* Atomicity: check-and-record must be atomic per device+key (unique constraint, not
  read-then-write race) so two concurrent workers cannot both send (Section 18
  concurrency posture).
* Distinct events for the same task at different state versions are *not* duplicates
  (the state version is part of the key by design — a later escalation re-notifies).
* Retention: dedupe records persist long enough to cover retry windows; document the
  retention chosen (plan fixes the key, not the TTL — see risk notes).
* Tests: same key twice → one send; different state version → second send;
  concurrent duplicate processing → exactly one send per device; multi-device fan-out
  dedupes independently per device; worker restart between send attempts does not
  double-send.

## Out of scope
* The send itself and FCM-level retries — MT-5.4-01.
* Delivery status and token pruning — MT-5.4-04; preferences — MT-5.4-05.
* SSE/event-stream dedupe (resume by event id) — WP-1.9/WP-1.10, a different
  mechanism.
* Cross-notification digesting — OQ-13 (off by default).

## Target paths
* `backend/` — per-device dedupe check/record in the push dispatch path
* `backend/tests/` — dedupe and concurrency tests
* WP changelog entry (dedupe record retention documented)

## Acceptance criteria
- [ ] The dedupe key is exactly `(event type, task id, state version)`, scoped per
  device — Section 9.8 verbatim.
- [ ] A retried event produces one push per device ("retried event does not
  duplicate" — WP-5.4 acceptance), including across worker restarts.
- [ ] Two concurrent processings of one event yield exactly one send per device
  (atomic check-and-record; Section 18 concurrency row).
- [ ] A different state version for the same task/event type still notifies (the
  version is part of the key, not filtered away).
- [ ] Record retention is documented in the changelog (key is specified by the plan,
  TTL is this task's recorded choice — see risk notes).
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`pytest backend/tests -k push_dedupe -q` — assert one-send-per-device per key,
second-send on version change, concurrent duplicate race → single send, restart
mid-dispatch safety, and per-device independence; then `pytest backend/tests -q`
stays green.

## Attachments
* [Section 9.8 — Notifications (dedupe key)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.9 — Background jobs (push dispatch)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan fixes the key but not the dedupe-record TTL — pick a retention safely
  beyond the retry/restart window (ties into OQ-10-style retention thinking),
  document it in the changelog, and flag it for the owner rather than choosing
  silently at cleanup-job time.
* Dedupe must key on `state version`, not event row id: the Section 9.8 goal is
  suppressing *retry* duplicates, which may replay different row ids after a queue
  redelivery — test with re-delivered events, not only same-row retries.
* Scoping per device (not global) is what keeps two phones independently notified —
  a "global key" shortcut would break multi-device owners; assert fan-out behavior.
