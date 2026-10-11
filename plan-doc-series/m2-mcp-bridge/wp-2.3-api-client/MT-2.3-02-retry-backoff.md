# MT-2.3-02 — Implement retry policy with backoff for 5xx and timeouts

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.3-02 |
| Title | Implement retry policy with backoff for 5xx and timeouts |
| Parent WP | WP-2.3 — Backend API client (Milestone M2) |
| Requirements | NFR-04, NFR-12; ADR-012 (idempotency keys plus lease fencing make retries safe) |
| Priority | M |
| Dependencies | MT-2.3-01 (transport layer exists) |
| Parent sections | 9.2, 10.10, 19 (WP-2.3), 20.4, 20.5 |

## Context
Section 10.10 requires that when the backend is unreachable or failing, tool calls fail
with a retryable error and the bridge retries with backoff; Section 9.2's envelope
carries a `retryable` flag that drives this decision. WP-2.3's acceptance criterion is
that simulated 5xx responses and timeouts retry safely — safely meaning the retry
cannot double-apply a mutation, which is why ADR-012 pairs retries with idempotency
keys (attached in MT-2.3-03) and lease fencing. NFR-04 requires clients and bridge to
reconnect automatically with backoff and lose no state.

## Inputs / Prerequisites
* Parent plan Section 9.2 — error envelope `retryable` field; `SERVER_ERROR`,
  `RATE_LIMITED` codes.
* Parent plan Section 10.10 — resilience: retry with backoff; in-flight submission
  data held locally until acknowledged (the holding behavior itself is WP-2.6).
* Parent plan Section 23 — ADR-012 (idempotency keys plus lease fencing on all agent
  mutations; best-effort retries are acceptable because of that pairing).
* MT-2.3-01 — transport and typed envelope parsing.

## Scope (in)
* Retry loop in the API client for transient failures: 5xx responses, connection
  errors and timeouts, honoring the envelope's `retryable` flag where present.
* Exponential backoff with jitter and a bounded attempt count, exposed as named
  configuration with documented defaults (Section 9.10).
* `RATE_LIMITED` handling that respects a server-provided retry delay if the envelope
  `details` supply one, otherwise falling back to the backoff schedule.
* Non-retryable classification: 4xx client errors (for example
  `TASK_ALREADY_CLAIMED`, `VALIDATION_ERROR`) surface immediately, never retried.
* Deterministic tests using a simulated clock and a mock transport that produces 5xx,
  timeouts, and non-retryable responses.

## Out of scope
* Attaching idempotency keys — MT-2.3-03 (dependency for production safety of these
  retries, but a separate slice).
* Holding submission payloads locally across outages — WP-2.6 (MT-2.6-05).
* Backend retry behavior (queues, workers) — Section 9.9 jobs.
* Tool-level error presentation — MT-2.3-04.

## Target paths
* `bridge/src/` (retry module in the client)
* `bridge/tests/` (retry/backoff tests)
* WP changelog entry

## Acceptance criteria
- [ ] Simulated 5xx responses and timeouts are retried with bounded exponential
  backoff plus jitter; tests assert attempt counts and delay bounds deterministically
  (WP-2.3 acceptance).
- [ ] Non-retryable errors (`VALIDATION_ERROR`, `TASK_ALREADY_CLAIMED`,
  `TASK_STATE_CONFLICT`, and other 4xx codes) are surfaced after exactly one attempt.
- [ ] Retry behavior is driven by the Section 9.2 `retryable` flag when the server
  provides it.
- [ ] Retrying a mutating call is only considered safe once MT-2.3-03's idempotency
  keys are present; the dependency is documented in code and changelog.
- [ ] All error codes used exist in the Section 9.2 catalog (Section 20.4 item 5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the retry tests with the bridge suite, e.g.
`uv run pytest bridge/tests/ -k retry`; confirm simulated 5xx/timeout cases pass and
non-retryable cases assert a single attempt.

## Attachments
* [Section 10.10 — Resilience](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 23 — ADR-012](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Retrying non-idempotent POSTs without MT-2.3-03 could double-claim or
  double-submit; do not enable retries on mutating calls before that slice lands.
* Unbounded retries against a down backend would wedge agents — the attempt cap and
  final retryable failure surface must be covered by tests, per NFR-04.
