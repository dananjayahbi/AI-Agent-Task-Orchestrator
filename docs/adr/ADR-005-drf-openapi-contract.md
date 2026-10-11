# ADR-005 — DRF with generated OpenAPI as the contract

| Field | Value |
|---|---|
| Status | accepted |
| Decision date | 2026-10-11 |
| Parent plan | Section 23 — ADR-005 (embodies decided OQ-02) |
| Session notes | [`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md) (WP-0.4 / MT-0.4-01) |

## Context

The backend serves REST under `/api/v1` (Section 9.2) to three clients (web, mobile,
bridge) and must publish a machine-readable contract validated in CI (WP-1.1,
NFR-11). OQ-02 asked DRF or Django Ninja; the review session decided DRF on
2026-10-11.

## Decision

DRF with generated OpenAPI as the contract.

## Rationale

Ecosystem and schema tooling.

## Alternatives considered

* Django Ninja.

## Consequences

* Permissions, throttling and schema generation are built on DRF's mature ecosystem,
  serving the authorization matrix (Section 12.2) and the error/endpoint surface
  (Section 9.2).
* The OpenAPI document is generated from the code, served by the backend and
  validated in CI (WP-1.1 acceptance).
* Django Ninja is excluded from the design.

## Amendments

None — MT-0.4-01 (2026-10-11) flagged no conflict with Section 23.
