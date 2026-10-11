# Mobile (`mobile/`)

The Flutter mobile client — monitoring, approvals, and push handling (parent plan
Section 14). It is an API-only client of the backend; authentication follows the
layered model in ADR-006.

* Package boundaries and tooling commands:
  [CONTRIBUTING.md — Mobile (Flutter)](../CONTRIBUTING.md#mobile-flutter)

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
