# MT-1.12-07 — Implement Processing Status Transitions with Retry/Backoff

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.12-07 |
| Title | Implement processing status transitions with retry/backoff |
| Parent WP | WP-1.12 — Attachment pipeline: parse, OCR, chunk, tokens (Milestone M1) |
| Requirements | FR-ATT-07, FR-ATT-02 |
| Priority | M |
| Dependencies | MT-1.12-06 (pipeline stages complete) |
| Parent sections | 9.5, 9.9, 9.6, 19.1 (WP-1.12), 20.4, 20.5 |

## Context
Section 9.5 stages 4-5: "Persist derived data, set `processing_status`, emit
`attachment.ready` or `attachment.failed`; retry transient failures with backoff;
permanent failures show a human-readable reason." FR-ATT-07: statuses `uploaded`,
`processing`, `ready`, `failed` are visible. Section 9.9: the attachment pipeline
retries with backoff. Section 9.6 catalog: `attachment.processing|ready|failed`.

## Inputs / Prerequisites
* MT-1.12-01 through MT-1.12-06 — the stages this status machine orchestrates.
* MT-1.9-02 — the write-in-transaction event helper (event emission requirement,
  Section 20.4 item 6).
* Parent plan Sections 9.5, 9.6, 9.9 — transition and retry rules.
* Section 9.2 canonical code `ATTACHMENT_NOT_READY` — consumed later by WP-1.14;
  this task guarantees the status values it keys off.

## Scope (in)
* A status state machine over `uploaded → processing → ready | failed` (FR-ATT-07),
  with transitions persisted on the attachment record and protected against
  out-of-order worker completion (stale stage results cannot overwrite a terminal
  status).
* Emission rules: exactly one `attachment.processing` on entry to processing,
  exactly one `attachment.ready` or `attachment.failed` at the end — written
  in-transaction via the event helper (Section 9.6, Section 20.4 item 6).
* Retry classification: transient failures retried with backoff (per Section 9.9
  schedule semantics; configurable attempt cap and backoff with documented
  defaults); permanent failures set `failed` immediately with a human-readable
  reason stored on the record.
* Reason visibility: `failed` records expose the reason through the descriptor
  (FR-ATT-07 "visible").
* Tests: legal/illegal transition matrix, exactly-one terminal event, transient
  retry reaching `ready`, retry exhaustion reaching `failed` with reason, stale
  completion rejected.

## Out of scope
* Scheduling/beat configuration — WP-1.7 owns Celery scheduling; retry is applied
  through the pipeline task's retry policy here.
* Publishing gating on `ready`/override (second half of FR-ATT-07) — task transition
  guard work (WP-1.5/WP-1.4); this task only supplies the status values.
* Retry of OCR/provider calls inside stages — stage-level error mapping feeds this
  task's classification only.
* Status display UI — WP-4.x / WP-5.x (descriptor shape from MT-1.11-04).

## Target paths
* `backend/apps/attachments/status.py`
* `backend/apps/attachments/pipeline.py` (retry wiring)
* `backend/tests/attachments/test_processing_status.py`
* WP changelog entry

## Acceptance criteria
- [ ] Only the Section 9.5/FR-ATT-07 statuses exist and only legal transitions
  succeed; illegal transitions are rejected by test (mirrors the Section 20.3
  "each state-machine transition gets its own test" rule).
- [ ] Each processed attachment emits exactly one `attachment.processing` and
  exactly one terminal `attachment.ready` or `attachment.failed`
  (Section 9.6; Section 20.4 item 6).
- [ ] Transient failures retry with backoff up to the configured cap, then land in
  `failed` with a human-readable reason; permanent failures fail immediately
  (Section 9.5 stage 5; Section 9.9).
- [ ] The reason is exposed on the descriptor (FR-ATT-07 visible).
- [ ] Retry/backoff settings have documented defaults (Section 20.4 item 3); error
  codes from the catalog (item 5); changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_processing_status.py -v` — transition matrix,
event exactly-once assertions, retry/backoff simulation, stale-completion rejection.

## Attachments
* [Section 9.5 — Attachment processing (stages 4-5)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.9 — Background jobs (retry with backoff)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.12 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Terminal-state races (a retry finishing after a manual failure, or two workers on
  one attachment) must be handled by compare-and-set on status, not read-modify-
  write; this is the likeliest source of duplicate events — cover it in tests.
* Backoff values are not specified in the plan; choose documented defaults consistent
  with the Section 9.9 schedules and record them — do not present them as plan facts.
