# ADR-001 — Single monorepo for all packages

| Field | Value |
|---|---|
| Status | accepted |
| Decision date | 2026-10-11 |
| Parent plan | Section 23 — ADR-001 |
| Session notes | [`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md) (WP-0.4 / MT-0.4-01) |

## Context

The plan delivers backend, bridge, web, mobile, schemas, infrastructure and e2e as one
system (Section 1, Appendix A), and WP-0.1 needs a repository strategy before
scaffolding begins. The owner is a solo developer, so repository overhead is a real
cost.

## Decision

Single monorepo for all packages.

## Rationale

Shared schemas, atomic changes, simpler CI for a solo owner.

## Alternatives considered

* Multiple repos.

## Consequences

* Shared schemas and cross-package contract changes land atomically in one tree
  (Appendix A; `schemas/` holds shared contracts).
* One CI pipeline covers the whole system (Section 18), simpler for a solo owner.
* Multiple-repository isolation is unavailable: all packages evolve in one versioned
  tree — accepted trade-off for solo-owner simplicity.

## Amendments

None — MT-0.4-01 (2026-10-11) flagged no conflict with Section 23.
