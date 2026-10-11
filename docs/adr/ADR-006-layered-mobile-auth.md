# ADR-006 — Layered mobile auth: edge policy, device-bound token, biometric unlock

| Field | Value |
|---|---|
| Status | accepted |
| Decision date | 2026-10-11 |
| Parent plan | Section 23 — ADR-006 |
| Session notes | [`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md) (WP-0.4 / MT-0.4-01) |

## Context

The Flutter client reaches the backend over the public internet through the Cloudflare
tunnel, and a lost or stolen phone is an explicit threat in the model (Section 12.1).
No single control can be trusted to protect a device exposed in that zone.

## Decision

Layered mobile auth: edge policy, device-bound token, biometric unlock.

## Rationale

No single point of failure on a phone exposed over the internet.

## Alternatives considered

* Edge-only.
* Static bearer token.

## Consequences

* Three independent gates apply: Cloudflare edge access policy, a device-bound token
  held in secure storage and released only after biometric success, and Django token
  validation — the edge alone is never sufficient (Section 12.2).
* Device registration happens after Owner login, and devices are independently and
  remotely revocable (Sections 12.1, 12.2).
* Edge-only enforcement and a static bearer token are excluded.

## Amendments

None — MT-0.4-01 (2026-10-11) flagged no conflict with Section 23.
