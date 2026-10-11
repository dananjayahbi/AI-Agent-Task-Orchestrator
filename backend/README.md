# Backend (`backend/`)

The Django control plane — API, task state machine, leases, events, policy,
notifications, and persistence (parent plan Sections 8–9). The backend never touches
Git repositories or host filesystem content (Principle P2, ADR-007).

* Package boundaries and tooling commands:
  [CONTRIBUTING.md — Backend (Python)](../CONTRIBUTING.md#backend-python)

## Shared conventions (WP-0.5)

Every configuration value this package reads follows the shared conventions:

* [Configuration conventions](../docs/plan/conventions/configuration.md) —
  environment variable naming, grouping and secret handling (parent plan
  Sections 9.10, 16.2)
* [Error conventions](../docs/plan/conventions/error-envelope.md) — canonical
  error envelope and the 19-code catalog (parent plan Section 9.2)
* [Header conventions](../docs/plan/conventions/headers.md) — correlation id and
  idempotency key headers (parent plan Sections 9.2, 9.6, 17; ADR-012)
* [Pagination conventions](../docs/plan/conventions/pagination.md) — cursor-based
  lists for every list endpoint, plus the Section 9.5 attachment `content`
  exception (parent plan Sections 9.2, 9.5)
