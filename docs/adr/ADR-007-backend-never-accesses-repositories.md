# ADR-007 — Backend never accesses repositories; evidence uploaded by host-side components

| Field | Value |
|---|---|
| Status | accepted |
| Decision date | 2026-10-11 |
| Parent plan | Section 23 — ADR-007 |
| Session notes | [`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md) (WP-0.4 / MT-0.4-01) |

## Context

Principle P2 fixes that the backend never reads or writes repositories, and the trust
boundaries place repositories on the developer host — a semi-trusted zone — while the
orchestrator stack may later run on a VPS (Sections 6.1, 6.4). Repository content is
untrusted input (P10).

## Decision

Backend never accesses repositories; evidence uploaded by host-side components.

## Rationale

Enables VPS hosting and strict isolation.

## Alternatives considered

* Mounting repos into containers.

## Consequences

* All Git work runs on the developer host: the bridge captures patch, changed files
  and diff stats locally and uploads them, and the Merge Executor performs merges in a
  dedicated worktree (Sections 6.3, 9.7).
* Backend containers never mount Git repositories, keeping VPS migration trivial (P2)
  and Zone D separation intact (Section 6.4).
* Mounting repositories into backend containers is excluded from the design.

## Amendments

None — MT-0.4-01 (2026-10-11) flagged no conflict with Section 23.
