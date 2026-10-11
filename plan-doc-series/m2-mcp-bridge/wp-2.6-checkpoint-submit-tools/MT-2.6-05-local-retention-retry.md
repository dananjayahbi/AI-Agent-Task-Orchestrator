# MT-2.6-05 — Implement local payload retention and retry across backend outages

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.6-05 |
| Title | Implement local payload retention and retry across backend outages |
| Parent WP | WP-2.6 — Tools: checkpoint and submission with Git evidence (Milestone M2) |
| Requirements | FR-MCP-07, NFR-04, ADR-012 |
| Priority | M |
| Dependencies | MT-2.6-04 (upload flow), WP-2.3 (retry/backoff and idempotency conventions) |
| Parent sections | 10.10, 9.2, 19 (WP-2.6), 18, 20.4, 20.5 |

## Context
Section 10.10 (Resilience): "Backend unreachable: tool calls fail with a retryable
error and the bridge retries with backoff; in-flight submission data (patch, summary)
is held locally until acknowledged. All mutating calls carry idempotency keys."
WP-2.6's acceptance: "backend outage during submit does not lose the payload", and
Section 18's chaos row expects no lost state when the bridge is killed mid-submission.
NFR-04 requires that backend restarts lose no state and clients/bridge reconnect with
backoff. This task makes a submission durable on the host the moment the agent hands
it over, so an outage can delay an outcome but never destroy evidence.

## Inputs / Prerequisites
* Parent plan Section 10.10 — the exact resilience contract (retryable error, local
  hold until acknowledged, idempotency keys).
* MT-2.6-04 — the assembled payload and upload path this wraps.
* WP-2.3 — established backoff/retry and idempotency-key conventions (NFR-12
  retry semantics, `retryable` flag).
* Section 9.2 catalog — `SERVER_ERROR`/`RETRY`-class handling stays in the envelope
  contract (codes from the catalog only).
* Section 18 chaos row — "kill bridge mid-submission — expect no lost state".

## Scope (in)
* A local spool: the moment a submission payload is assembled (patch, summary, flags,
  idempotency key), it is persisted under the user-level bridge data area before the
  network attempt.
* Retry with backoff on connection failures and retryable server errors (Section
  10.10, WP-2.3 conventions), reusing the original idempotency key on every attempt
  (ADR-012) so a late duplicate never double-submits.
* Acknowledgment clears the spool entry; only acknowledged submissions are
  considered complete.
* Restart recovery: on bridge startup, unacknowledged spooled submissions resume
  retry (survives "kill bridge mid-submission").
* Non-retryable responses (validation, state conflict) surface immediately to the
  agent with hint and next action and are not blindly retried; the spooled entry is
  resolved per the response (kept only where a human/agent decision is still
  pending — record the rule in the changelog).
* Spool hygiene: restrictive file permissions, no tokens or secrets in payloads,
  bounded retention for stuck entries with a clear operator message (Section 20.4
  item 3).
* Tests: outage mid-upload → payload survives process restart → retry succeeds once
  with the same key; retryable vs non-retryable classification; spool cleared on
  ack; no secrets in spool files.

## Out of scope
* Backend outage handling and idempotency-key acceptance — WP-3.2, WP-1.15.
* General transport retry for read-only calls — WP-2.3.
* Checkpoint tool payloads (small, safely retried by the agent) — MT-2.6-01.
* Merge executor crash recovery — WP-3.7.

## Target paths
* `bridge/` — submission spool module, retry integration
* `bridge/tests/` — retention/retry tests
* WP changelog entry

## Acceptance criteria
- [ ] A submission payload is persisted locally before the network attempt and held
  until the backend acknowledges it (Section 10.10).
- [ ] Backend outage during submit does not lose the payload: kill the bridge
  mid-submission, restart, and the retry completes the submission (WP-2.6 acceptance,
  Section 18 chaos row).
- [ ] Every retry attempt reuses the original idempotency key, so replays never
  double-submit (ADR-012, Section 18 concurrency row).
- [ ] Retries use backoff and respect the envelope's `retryable` semantics
  (WP-2.3 conventions); non-retryable errors surface to the agent instead of looping.
- [ ] No secrets or environment-specific paths are committed or stored in payloads
  (Section 20.4 item 3); lint/type/tests green (item 2); changelog note added
  (item 7).

## Test command
`uv run pytest bridge/tests/ -k submission_spool -q` — simulate backend outage and
process kill around the upload: assert payload persistence, restart recovery, single
idempotent success, backoff behavior, non-retryable surfacing, and secret-free spool
contents; then the full bridge suite stays green.

## Attachments
* [Section 10.10 — Resilience](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and Quality Strategy (chaos row)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Spooled patches contain the agent's diff — sensitive by nature. Store with
  restrictive permissions outside Git, scrub on acknowledgment, and document stuck-
  entry cleanup; never log payload contents (Section 12.4 log scrubbing).
* Retrying non-retryable failures forever hides real problems (a superseded
  resolution, a state conflict) — classification tests must pin which responses
  surface immediately.
* Key reuse across retries is what makes this safe; a "fresh key per retry" bug
  would create duplicate resolutions — assert key stability explicitly.
