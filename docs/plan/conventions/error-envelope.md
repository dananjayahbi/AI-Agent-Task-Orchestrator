# Error conventions — canonical envelope and error-code catalog

| Field | Value |
|---|---|
| Status | Published |
| Published | 2026-10-11 |
| Owner | WP-0.5 — Configuration, secrets and error conventions (MT-0.5-02) |
| Source of truth | Parent plan Section 9.2 (envelope + catalog) and Section 20.4, item 5 (global DoD) — the plan is authoritative; this document is the published reference |
| Applies to | Every non-2xx response on the v1 REST surface (base path `/api/v1`), by every component that produces or consumes API errors |
| Sibling conventions | [`configuration.md`](./configuration.md), [`headers.md`](./headers.md), [`pagination.md`](./pagination.md) |

## Purpose

Section 9.2 fixes the standard error envelope and the canonical error-code catalog;
Section 20.4, item 5 makes "error codes exist in the catalog" a global
definition-of-done check for every micro-task. This document publishes both so the
backend, bridge, web and mobile map errors identically — the bridge especially needs
canonical codes to translate API failures into tool errors (WP-2.3), and the typed
contract needs one shape to express (NFR-11, ADR-005).

## The error envelope (Section 9.2)

Every non-2xx response uses the standard envelope **by reference to parent plan
Section 9.2** — the shape is stated there and is not re-derived here. Its five
fields:

| Field | Role (as fixed by Section 9.2) |
|---|---|
| `code` | The canonical error code from the catalog below — the stable machine-readable contract. |
| `message` | A human-readable sentence about this occurrence. |
| `retryable` | Whether a retry can succeed; drives client and bridge retry behavior (see rules below). |
| `details` | Structured context for this occurrence (Section 9.2 example: `task_id`, `state`). |
| `correlation_id` | Correlation identifier for this exchange — semantics defined in [`headers.md`](./headers.md). |

Quoted verbatim from the parent plan (Section 9.2) so the wire contract is fixed
precisely (Section 0.4):

```json
{
  "error": {
    "code": "TASK_ALREADY_CLAIMED",
    "message": "Task PID00007-T004 is held by another worker.",
    "retryable": false,
    "details": { "task_id": "PID00007-T004", "state": "in_progress" },
    "correlation_id": "c0a8-4f2e-91d7"
  }
}
```

The parent plan stays authoritative: if this document and Section 9.2 ever diverge,
Section 9.2 wins and this document is corrected.

## Canonical error-code catalog (Section 9.2)

All 19 canonical codes, in the plan's order. None added, none dropped, none renamed:

| # | Code |
|---|---|
| 1 | `AUTH_REQUIRED` |
| 2 | `AUTH_FORBIDDEN_PROJECT` |
| 3 | `VALIDATION_ERROR` |
| 4 | `TASK_NOT_FOUND` |
| 5 | `TASK_STATE_CONFLICT` |
| 6 | `TASK_ALREADY_CLAIMED` |
| 7 | `LEASE_EXPIRED` |
| 8 | `LEASE_NOT_OWNED` |
| 9 | `DEPENDENCY_UNMET` |
| 10 | `CONCURRENCY_LIMIT_REACHED` |
| 11 | `SCOPE_VIOLATION` |
| 12 | `ROLE_NOT_PERMITTED` |
| 13 | `AUDITOR_SAME_AS_CODER` |
| 14 | `ATTACHMENT_NOT_READY` |
| 15 | `ATTACHMENT_UNSUPPORTED_FORMAT` |
| 16 | `POLICY_VIOLATION` |
| 17 | `RATE_LIMITED` |
| 18 | `VERSION_CONFLICT` |
| 19 | `SERVER_ERROR` |

The catalog is closed: some codes (e.g. `RATE_LIMITED`, `VERSION_CONFLICT`) have no
implementation until later work packages — the catalog is never pruned to only the
codes currently in use.

## Rules the catalog implies

1. **Codes are the stable contract.** Clients and the bridge switch on `code`; a
   published code is never renamed, removed, or reused with a different meaning.
   Changing the catalog means changing the parent plan Section 9.2 first, then this
   mirror.
2. **Messages are for humans.** `message` text is human-readable and may be reworded
   or localized; clients must never parse it. Only `code` is machine-readable
   contract.
3. **`retryable` drives retries.** Client and bridge retry behavior reads the
   `retryable` flag (NFR-12 safe retries; ADR-012; the bridge retries with backoff —
   Section 10.10). Retrying a non-retryable failure is a client bug.
4. **Add a code here first.** Global definition of done (Section 20.4, item 5): an
   implementation may only emit codes that already exist in this catalog. A new code
   is added to the catalog — parent plan Section 9.2, then mirrored here — before any
   code emits it; never the reverse. Using an uncatalogued code fails the DoD.
5. **No invented fields.** The envelope has exactly the five fields above
   (Section 20.5 traceability); nothing is added here that Section 9.2 does not
   fix.

## OpenAPI obligation (NFR-11, ADR-005)

When the backend lands (WP-1.1), the envelope becomes a reusable schema in the
generated OpenAPI document — the single typed source for the web and mobile clients
(NFR-11). The schema models the wire nesting exactly: an `ErrorEnvelope` component
whose single required property `error` refs `ErrorEnvelopeBody` — the five fields
above, `details` optional (the earlier flat top-level rendering was a contract bug;
corrected and the snapshot regenerated at the Wave 2 end-of-wave gate — backend
`apps/core/serializers.py::ErrorEnvelopeSerializer` is the source of truth).
Contract changes are guarded by schema diff in CI (Section 18 quality
gates; Section 20.4, item 4), so any drift from this document shows up as a reviewed
schema diff, not a silent change.

## Out of scope (for this document)

* HTTP status mapping per endpoint — defined by the OpenAPI contract in WP-1.1, not
  invented here.
* Implementing the envelope in Django exception handlers — WP-1.1 / WP-1.15.
* Bridge error-to-tool-error mapping — WP-2.3 (consumes this catalog).
* Web/mobile error UI handling — WP-4.x / WP-5.x.
* `correlation_id` field semantics — [`headers.md`](./headers.md) (MT-0.5-03).

## References

* Parent plan Section 9.2 — REST API surface, envelope shape, canonical codes.
* Parent plan Section 20.4, item 5 — global DoD: error codes used must exist in the
  catalog; item 4 — schema diff reviewed for public-contract changes.
* Referenced from the package documentation of `backend/`, `bridge/`, `web/` and
  `mobile/` (WP-0.5 acceptance).
