# MT-1.13-05 — Implement Failure Degradation to OCR-Only Output

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.13-05 |
| Title | Implement failure degradation to OCR-only output |
| Parent WP | WP-1.13 — Visual description provider (Milestone M1) |
| Requirements | FR-ATT-02, FR-ATT-05; G-14, NFR-04 |
| Priority | M |
| Dependencies | MT-1.13-01 (failure contract), MT-1.13-03 (failure signals), MT-1.13-04 (cache), MT-1.12-07 (status/retry) |
| Parent sections | 4 (G-14), 9.5, 19.1 (WP-1.13 acceptance), 20.4, 20.5; OQ-07 |

## Context
Section 9.5 closes its description-provider paragraph with two commitments: "Cost and
failures are logged; failures degrade to OCR-only." WP-1.13's acceptance states the
operational consequence: "with provider disabled, tasks still process using OCR only."
Degradation is what keeps the vision provider strictly additive — an outage, quota
exhaustion, malformed response or credential problem in the remote provider must never
block an attachment from reaching `ready` with its OCR transcript, because OCR ran
independently (MT-1.12-02) and Section 9.5 stage 5 only fails attachments on permanent
pipeline errors. FR-ATT-05's text-only path ("OCR plus description") simply omits the
description when there is none. This micro-task wires the typed failure from
MT-1.13-01/03 into the pipeline so a provider failure logs and continues.

## Inputs / Prerequisites
* MT-1.13-01 — the typed failure signal the pipeline catches.
* MT-1.13-03 — remote provider failures and cost logging (this task consumes its
  failures).
* MT-1.13-04 — cache: a failed generation stores nothing, so degradation must not
  poison the cache.
* MT-1.12-07 — status transitions and retry/backoff: defines when the pipeline would
  otherwise mark `failed`.
* Parent plan Section 9.5 — "failures degrade to OCR-only"; stage 5 failure reasons.

## Scope (in)
* Catch provider failures at the caption step and continue the pipeline: OCR
  transcript and chunks persist as usual, the attachment reaches `ready`, and the
  description field stays empty ("no description") — degradation, not failure
  (Section 9.5).
* Log the failure through the MT-1.13-03 structured logging (Section 17) with
  correlation id, keeping the distinction between "provider failed" (degraded,
  logged) and "attachment failed" (status `failed` with a human-readable reason,
  Section 9.5 stage 5) visible in logs.
* Ensure degradation interacts correctly with MT-1.12-07 retry/backoff: transient
  provider errors may be retried by the pipeline's existing policy, but exhaustion
  degrades to OCR-only rather than setting `failed` — only non-provider pipeline
  errors may fail an attachment (Section 9.5 stage 5).
* Ensure the cache is unaffected: nothing stored on failure, so a later successful
  run (MT-1.13-04) still generates.
* Tests: remote provider raising timeout/HTTP error/malformed output → attachment
  `ready`, OCR transcript present, description empty, failure logged once, no
  `attachment.failed` event emitted (Section 9.6 catalog — degraded runs are not
  failures).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* The failure signal itself — MT-1.13-03 produces it; this task handles it.
* Caching behavior — MT-1.13-04 (coordination only).
* Choosing a second/fallback provider — not in the plan; a failed provider degrades to
  OCR-only, it does not route elsewhere (Section 9.5).
* Alerting on repeated provider failures — Section 17 alerts do not list provider
  failures; raising one is a new decision, not this task.
* Downstream rendering of "OCR plus description" without the description — WP-1.14 /
  WP-2.5 consume the empty case.

## Target paths
* `backend/apps/attachments/` (failure handling in the caption step of the pipeline)
* `backend/tests/attachments/` (degradation tests: timeout, HTTP error, malformed
  output, retry-exhaustion, event assertions)
* WP changelog entry

## Acceptance criteria
- [ ] A provider failure at any stage (timeout, non-2xx, malformed response) leaves
  the attachment `ready` with OCR transcript and empty description — Section 9.5
  "failures degrade to OCR-only" (WP-1.13 acceptance, first half generalized to
  failures).
- [ ] No `attachment.failed` event is emitted for a degraded run; the failure is
  present in structured logs with correlation id (Section 9.6 catalog; Section 17;
  NFR-10).
- [ ] Retry exhaustion on provider errors degrades rather than setting status
  `failed`; attachments still `failed` only from non-provider pipeline errors
  (Section 9.5 stage 5).
- [ ] The cache stores nothing on failure, so a subsequent run with a healthy
  provider generates the description (MT-1.13-04 contract).
- [ ] Cost logging remains accurate: degraded runs log the failed attempt without
  fabricated usage figures (Section 9.5 "cost and failures are logged").
- [ ] Tests, lint and type check green in CI (Section 20.4 item 2); changelog note
  added (item 7).

## Test command
`pytest backend/tests/attachments -k degradation or provider_failure -v` — three
failure shapes reaching `ready` OCR-only with logged failure and correct events;
`pytest backend/tests/attachments -k description_cache -v` confirms the cache was not
poisoned; full suite green.

## Attachments
* [Section 9.5 — Attachment processing (failure degradation)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [G-14 — Pluggable, disableable provider](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.6 — Event catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Do not blanket-except around the caption step: only the typed provider failure from
  MT-1.13-01 degrades — a programming error (AttributeError etc.) must still surface,
  or real pipeline bugs become invisible "successful" runs.
* Section 9.5 stage 5 says permanent failures show a human-readable reason; keep
  provider degradation out of that path entirely so `failed` reasons stay meaningful
  for WP-1.12/WP-1.14 consumers.
* Repeated degradation hides a misconfigured provider (wrong key, zero budget) —
  without an alert (Section 17 does not define one), the log is the only signal;
  record this visibility gap in the changelog rather than inventing an alert rule.
