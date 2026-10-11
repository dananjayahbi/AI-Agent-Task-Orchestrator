# Header conventions — correlation id and idempotency key

| Field | Value |
|---|---|
| Status | Published |
| Published | 2026-10-11 |
| Owner | WP-0.5 — Configuration, secrets and error conventions (MT-0.5-03) |
| Source of truth | Parent plan Sections 9.2, 9.6, 10.10, 12.5, 17; ADR-012; NFR-10/NFR-12 — the plan is authoritative; this document is the published reference |
| Applies to | Every client (web, mobile), the bridge, the backend and the worker — one header contract across clients → bridge → backend → worker |
| Sibling conventions | [`configuration.md`](./configuration.md), [`error-envelope.md`](./error-envelope.md), [`pagination.md`](./pagination.md) |
| Depends on | [`error-envelope.md`](./error-envelope.md) — this document defines the envelope's `correlation_id` field |

## Purpose

WP-0.5's goal names "correlation id, idempotency header" as conventions to fix before
code spreads. Section 9.2 requires every mutating endpoint to accept an idempotency
key header and puts `correlation_id` inside the error envelope; Section 17 propagates
the correlation id from clients and bridge through backend and worker with
token/secret scrubbing; ADR-012 commits to idempotency keys (plus lease fencing) on
all agent mutations. This is the single convention that backend (WP-1.1), bridge
(WP-2.3) and the clients implement against.

## Canonical header names

Exactly one canonical spelling per header (Section 0.4: "canonical" means the single
authoritative spelling). No aliases are accepted or defined — two spellings of one
header are exactly the drift WP-0.5 exists to prevent. HTTP header names are
case-insensitive on the wire; documentation and structured logs always use these
spellings as written:

| Concern | Canonical header name |
|---|---|
| Correlation id | `X-Correlation-ID` |
| Idempotency key | `Idempotency-Key` |

Alternative spellings that may appear in other systems (e.g. `X-Request-ID`,
`X-Idempotency-Key`) are **not** part of this contract and are never accepted as
aliases.

### Correlation id — definition

**`X-Correlation-ID`** identifies one logical exchange end-to-end for diagnostics.

* **Generation** — the caller (web, mobile, bridge) generates a correlation id when
  it has none to supply; the backend generates one when a request arrives without
  the header. The value is diagnostic data (an opaque token in the plan's example
  shape, Section 9.2) — never parsed, never treated as identity or authorization.
* **Honoring** — when the header is present, every hop honors the supplied value
  instead of generating a new one.
* **Propagation** — the id travels from clients and the bridge through the backend
  and the worker (Section 17) and appears in:
  * structured logs at every hop (Section 17; NFR-10);
  * every Event row and audit entry — the audit trail records actor **and
    correlation id** (Sections 9.6, 12.5);
  * the error envelope's `correlation_id` field on non-2xx responses
    (Section 9.2; field semantics defined here, shape in
    [`error-envelope.md`](./error-envelope.md)).
* **Scrubbing** — treated as diagnostic data and carried under the Section 17
  token/secret scrubbing rules: a correlation id never contains, and logs never
  expose, tokens or secrets (RISK-14).

### Idempotency key — definition

**`Idempotency-Key`** makes retries of mutating requests safe (NFR-12; ADR-012).

* **Contract** — every mutating endpoint on the v1 surface accepts the header
  (Section 9.2: "All mutating endpoints accept an idempotency key header" — i.e.
  all `POST`, `PATCH` and `DELETE` endpoints of the Section 9.2 table).
* **Generation** — caller-derived, one key per logical operation, reused verbatim
  for every retry of that operation. The bridge sends a key on **all** mutating
  calls (Section 10.10), generated per submission/mutation, not per attempt.
* **Safe-retry semantics** — the same key with the same request replays the
  original outcome instead of re-executing the operation (NFR-12: claim,
  checkpoint, submit and decision endpoints are safe to retry; covered by the
  "double submit with same idempotency key" concurrency test, Section 18).
* **Retry interaction** — on an unreachable backend the bridge retries with
  backoff and keeps in-flight submission data until acknowledged, reusing the same
  key (Section 10.10); the `retryable` flag in the error envelope tells clients
  which failures are worth retrying ([`error-envelope.md`](./error-envelope.md)).

### What the server stores per key

To dedupe retries, the server retains, per idempotency key, the minimum exchange
record (storage implemented in WP-1.1 / WP-1.15; the record is fixed here):

1. the key itself, in its request scope;
2. a fingerprint of the original request (method, path, payload digest) — so a
   retry can be confirmed to be *the same request* before replaying;
3. the original outcome (response status and body) — what a retry replays;
4. a creation timestamp that drives retention.

**Retention window — open point.** The plan states no retention duration for this
record, and WP-0.5 does not invent an authoritative number. The window is recorded
as an open point for owner confirmation; once decided it becomes a documented
default in the settings table under [`configuration.md`](./configuration.md)
(naming pattern `ORCHESTRATOR_<SETTING>`, duration suffix per the units rule) and
is then configured as an ordinary environment setting. Until the decision lands,
the store's lifetime is an implementation detail of WP-1.1 / WP-1.15 flagged for
review — not a contract.

**Key reuse with a different request** is not specified by the plan; the response
to it (an error drawn from the canonical catalog, chosen with the endpoint's
OpenAPI mapping) is likewise an open point for WP-1.1 — no behavior or code is
invented here.

## The three mechanisms are distinct

| Mechanism | Purpose | Where defined |
|---|---|---|
| `X-Correlation-ID` | Diagnose one logical exchange across logs, events, audit, error envelope. | This document (Sections 9.2, 12.5, 17). |
| `Idempotency-Key` | Deduplicate retries of a mutating request — one logical operation, one key. | This document (Sections 9.2, 10.10; ADR-012; NFR-12). |
| SSE resume via **event id** | Recover an event stream after reconnect: the client sends its last received event id and receives missed events, then switches to live — "no gaps, no duplicates". | Parent plan Section 9.6 — a stream-recovery concern of `GET /events/stream`, **not** a correlation or idempotency header. Event ids never substitute for either header, and neither header resumes a stream. |

## Out of scope (for this document)

* Implementing header middleware or idempotency storage — WP-1.1 / WP-1.15.
* The concurrency/fencing half of ADR-012 (lease fencing) — WP-1.6.
* Bridge retry implementation — WP-2.3.
* Client header-sending behavior in web/mobile code — WP-4.x / WP-5.x.
* Rate-limit response header shapes — not specified in the plan; open question if
  needed.

## References

* Parent plan Section 9.2 — all mutating endpoints accept an idempotency key header;
  `correlation_id` in the error envelope.
* Parent plan Section 17 — correlation id propagated clients → bridge → backend →
  worker; token/secret scrubbing (RISK-14).
* Parent plan Sections 9.6 and 12.5 — every state-changing action writes an Event
  row; audit entries carry actor and correlation id.
* Parent plan Section 10.10 — all mutating calls carry idempotency keys; retries
  with backoff. ADR-012, NFR-10, NFR-12.
* Referenced from the package documentation of `backend/`, `bridge/`, `web/` and
  `mobile/` (WP-0.5 acceptance).
