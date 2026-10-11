# ADR-012 — Idempotency keys plus lease fencing on all agent mutations

| Field | Value |
|---|---|
| Status | accepted |
| Decision date | 2026-10-11 |
| Parent plan | Section 23 — ADR-012 |
| Session notes | [`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md) (WP-0.4 / MT-0.4-01) |

## Context

Agents retry calls on flaky networks, and leases expire while an old owner may still
be running — a slow former owner must never overwrite reclaimed work (Section 8.6).
Replayed or retried POSTs are an explicit threat in the model (Section 12.1), and
principle P6 requires every mutating call to be idempotent and retry-safe.

## Decision

Idempotency keys plus lease fencing on all agent mutations.

## Rationale

Safe retries and safe reclaim.

## Alternatives considered

* Best-effort retries.

## Consequences

* Every claim increments an internal lease generation and mutating calls carry it, so
  a slow former owner can never overwrite state after reclaim (Section 8.6).
* Idempotency keys make retried agent mutations safe against double effects (P6,
  NFR-12); both mechanisms are covered by the WP-1.15 idempotency and race suites.
* Server-side ordering relies on the authoritative server clock (P7), never
  client-supplied timestamps.

## Amendments

None — MT-0.4-01 (2026-10-11) flagged no conflict with Section 23.
