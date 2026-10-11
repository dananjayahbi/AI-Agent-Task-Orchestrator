# MT-1.9-03 — Implement Post-Commit Publish to the Redis Channel

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.9-03 |
| Title | Implement post-commit publish to the Redis channel |
| Parent WP | WP-1.9 — Event log and audit trail (Milestone M1) |
| Requirements | FR-SEC-03, NFR-03 |
| Priority | M |
| Dependencies | MT-1.9-02 (write helper in place) |
| Parent sections | 9.6, 19.1 (WP-1.9), 9.10, 20.4, 20.5 |

## Context
Section 9.6 states: "Every state-changing action writes an Event row; after commit it
is published to a Redis channel." The SSE gateway (WP-1.10) subscribes to that channel
for live fan-out. Publishing must therefore happen strictly after the transaction
commits, so subscribers never observe events that were later rolled back.

## Inputs / Prerequisites
* MT-1.9-02 — the write helper; publishing hooks into the same event flow via
  `transaction.on_commit` (or the framework equivalent).
* Parent plan Section 9.6 — publish-after-commit rule; envelope published as-is.
* Parent plan Section 9.10 — Redis channel name / connection settings are
  environment-driven configuration with documented defaults.
* Redis service from the Compose stack (WP-0.2 / WP-1.1 wiring).

## Scope (in)
* Post-commit publishing: register a callback on the open transaction so that, only
  after a successful commit, the event envelope (Section 9.6 field names) is published
  to the configured Redis channel.
* Configuration for the channel name/connection following Section 9.10 conventions
  (documented default, startup validation).
* Failure behavior: a publish failure is logged and never fails or re-opens the
  already-committed request; the Event row remains the source of truth for recovery.
* Tests: publish happens once per committed event; nothing is published on rollback;
  payload equals the stored envelope.

## Out of scope
* Subscribing and fan-out to HTTP connections — MT-1.10-02.
* Resume/replay from the Event table — MT-1.10-03 (replay reads rows, not Redis).
* Retry/backoff semantics for the publisher beyond "log and continue" — out of scope;
  durability for missed live publishes is covered by DB-based resume.
* Background jobs and their schedules (Section 9.9) — WP-1.7.

## Target paths
* `backend/apps/events/publisher.py`
* `backend/apps/events/services.py` (hook-up to post-commit flow)
* `backend/tests/events/test_post_commit_publish.py`
* WP changelog entry

## Acceptance criteria
- [ ] A committed event is published to the configured Redis channel exactly once,
  after commit (Section 9.6).
- [ ] A rolled-back transaction publishes nothing.
- [ ] Published payload uses the Section 9.6 envelope field names unchanged
  (Section 20.5).
- [ ] A Redis outage during publish is logged and does not fail the originating
  request; the row remains readable for resume.
- [ ] Channel configuration has a documented default per Section 9.10 (Section 20.4
  item 3 — no environment-specific values committed).
- [ ] Lint, type check and tests green (item 2); changelog note added (item 7).

## Test command
`pytest backend/tests/events/test_post_commit_publish.py -v` — asserts publish-after-
commit ordering, exactly-once, no-publish-on-rollback, and payload equality with the
stored event row.

## Attachments
* [Section 9.6 — Realtime gateway and event model](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.10 — Configuration (environment-driven)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.9 deliverables (publisher after commit)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Ordering between concurrent commits is not guaranteed by Redis alone; consumers
  must rely on the monotonic `id`, not arrival order. State this explicitly for
  MT-1.10-02 so the fan-out sorts/filters by id.
* If the framework's `on_commit` hooks run in a worker process context (e.g. Celery),
  the hook must be registered in the process owning the transaction — verify with the
  sweep and pipeline flows (Sections 9.9, 12.5) during review.
