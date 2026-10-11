# MT-1.1-02 — Add Structured JSON Logging with Correlation-ID Propagation

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.1-02 |
| Title | Add structured JSON logging with correlation-id propagation |
| Parent WP | WP-1.1 — Django project skeleton (Milestone M1) |
| Requirements | NFR-10 |
| Priority | S |
| Dependencies | MT-1.1-01 (project and settings exist), MT-0.5-03 (correlation-id conventions) |
| Parent sections | 17, 9.10, 12.4, 19.1 (WP-1.1), 20.4, 20.5 |

## Context
WP-1.1's slice "logging with correlation id" implements Section 17's logging row:
structured JSON with the correlation id propagated from clients and bridge through the
backend, and token/secret scrubbing. Section 12.4 additionally requires logs to scrub
tokens and truncate attachment text. MT-0.5-03 already fixed the canonical correlation
header name and propagation rules; this task is the backend implementation of that
convention so every later WP logs consistently from day one.

## Inputs / Prerequisites
* MT-1.1-01 — the settings structure where logging is configured.
* MT-0.5-03 — canonical correlation-id header name, generation and propagation rules.
* Parent plan Section 17 — structured JSON logs, correlation id propagated through
  backend and worker, token/secret scrubbing.
* Parent plan Section 12.4 — logs scrub tokens and truncate attachment text.
* Parent plan Section 9.10 — logging configuration belongs to the documented
  environment-driven settings groups.

## Scope (in)
* Configure the backend to emit structured JSON logs (per Section 17) for all
  request/service logging.
* Implement correlation-id middleware per the MT-0.5-03 conventions: honor the incoming
  header when present, generate when absent, and include it in every log line for the
  request's scope; the same id must appear in the error envelope's `correlation_id`
  (Section 9.2) when an error is returned.
* Implement scrubbing per Sections 17 and 12.4: tokens/secrets never appear in logs;
  attachment text is truncated.
* Log levels and output destination configurable via the Section 9.10 settings groups.
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Propagation into the Celery worker — configured when the worker lands (background-job
  WPs); the convention is already fixed by MT-0.5-03.
* Events/audit rows — WP-1.9.
* Metrics — Section 17 "basic metrics" has no micro-task in this WP; do not invent an
  exporter here.
* Alerting rules (Section 17) — operational WPs in M6.

## Target paths
* `backend/` — logging configuration and correlation-id middleware (under `core`)
* `backend/tests/` — tests for JSON shape, correlation propagation, scrubbing
* WP changelog entry

## Acceptance criteria
- [ ] Log output is structured JSON containing the correlation id on every line emitted
  within a request scope (Section 17).
- [ ] Correlation-id behavior matches MT-0.5-03 exactly (same header name, honor-or-
  generate rule); the id reaches the error envelope field (Section 9.2).
- [ ] Tokens/secrets are scrubbed from log output and attachment text is truncated
  (Sections 17, 12.4), covered by a test.
- [ ] Behavior is driven by Section 9.10 settings with documented defaults.
- [ ] Tests, lint and type check green (Section 20.4 item 2).
- [ ] No secrets or environment-specific paths committed (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k "log or correlation"` asserting: a request produces one
log record per line in JSON form with the correlation id, an incoming header is honored,
a generated id is stable across the request, and a token value in the message is
scrubbed.

## Attachments
* [Section 17 — Observability and Operations](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.4 — Data protection](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.1](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Exact log field spellings are not fixed verbatim by the plan — define them once (the
  conventions document is the single authority) to avoid G-01-style spelling drift.
* Scrubbing must be tested against the canonical error codes that can echo values
  (e.g. `VALIDATION_ERROR` details) so no token leaks through an error path.
