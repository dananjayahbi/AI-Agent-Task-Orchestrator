# ADR-003 — Celery (worker and beat) on Redis for background jobs

| Field | Value |
|---|---|
| Status | accepted |
| Decision date | 2026-10-11 |
| Parent plan | Section 23 — ADR-003 |
| Session notes | [`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md) (WP-0.4 / MT-0.4-01) |

## Context

The system depends on recurring and asynchronous work: the lease sweeper reclaims
expired leases every 60 s, the attachment pipeline processes uploads, push dispatch
delivers notifications, and retention/backup jobs run on schedule (Section 9.9). These
must run outside the request/response cycle of the ASGI backend.

## Decision

Celery (worker and beat) on Redis for background jobs.

## Rationale

Needed for sweeper, OCR, push; mature scheduling.

## Alternatives considered

* Django-Q.
* Custom loops.
* In-process threads.

## Consequences

* The Compose stack runs dedicated `worker` and `beat` containers with Redis as
  broker (Sections 6.3, 9.9).
* Scheduled jobs (lease sweeper, lease-expiring notifier, stalled-task detector,
  retention cleanup, backup trigger) are owned by beat (Section 9.9).
* Django-Q, custom loops and in-process threads are excluded from the design.

## Amendments

None — MT-0.4-01 (2026-10-11) flagged no conflict with Section 23.
