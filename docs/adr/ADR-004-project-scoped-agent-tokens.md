# ADR-004 — Agent tokens scoped to exactly one project at the backend

| Field | Value |
|---|---|
| Status | accepted |
| Decision date | 2026-10-11 |
| Parent plan | Section 23 — ADR-004 |
| Session notes | [`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md) (WP-0.4 / MT-0.4-01) |

## Context

Zero-Bleed (GOAL-2) guarantees that sessions and data of one project never leak into
another. Gap G-07 found that enforcing this only in the MCP bridge could be bypassed by
a modified or malicious client (Sections 1, 4); the bridge runs in the semi-trusted
developer-host zone (Section 6.4).

## Decision

Agent tokens scoped to exactly one project at the backend.

## Rationale

Zero-Bleed cannot depend on a bridge alone.

## Alternatives considered

* Bridge-only enforcement.

## Consequences

* Defense in depth (P3): bridge binding **and** backend token scoping **and**
  audit-time scope checks all apply together (Sections 6.1, 12.1).
* The backend enforces project scope on every agent-facing endpoint and event filter;
  a token for one project receives `AUTH_FORBIDDEN_PROJECT` on another project's
  resources (Section 12.1, WP-1.2 acceptance).
* The bridge's project binding remains a convenience, never the authority (Section 4,
  G-07).

## Amendments

None — MT-0.4-01 (2026-10-11) flagged no conflict with Section 23.
