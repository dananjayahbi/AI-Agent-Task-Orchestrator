# MT-1.13-03 — Implement the Remote Vision-Model Provider With Configuration and Cost Logging

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.13-03 |
| Title | Implement the remote vision-model provider with configuration and cost logging |
| Parent WP | WP-1.13 — Visual description provider (Milestone M1) |
| Requirements | FR-ATT-02, FR-ATT-05; G-14, NFR-10 |
| Priority | M |
| Dependencies | MT-1.13-01 (interface and selector), MT-1.13-02 (disabled default untouched) |
| Parent sections | 4 (G-14), 9.5, 9.10, 12.4, 17, 19.1 (WP-1.13), 20.4, 20.5; OQ-07 |

## Context
Section 9.5 names the remote implementation "Anthropic-compatible vision model" and
requires that "cost and failures are logged". WP-1.13 lists the remote implementation
among its deliverables with "cost/error logging". G-14 identified the gap: an
LLM provider needs credentials and cost handling the original spec never mentioned.
Section 9.10 puts "description provider settings" in the configuration groups with
startup validation that fails fast on missing required values; Section 12.4 requires
secrets only in environment variables and that logs scrub tokens; Section 17 requires
structured JSON logging with correlation ids. OQ-07 (which provider, monthly budget)
has the recommended default "disabled … enable a configured vision model per project
when needed" — enabling is a deployment decision, so this task builds the capability
without changing the default.

## Inputs / Prerequisites
* MT-1.13-01 — interface, failure contract, configuration selection.
* MT-1.13-02 — the disabled default; enabling the remote provider must be an explicit
  configuration act, never the out-of-the-box state.
* Parent plan Section 9.5 — inputs available to the provider (normalized image,
  Section 9.5 stage 2) and the obligations (log cost, log failures).
* Parent plan Section 9.10 — settings group, documented defaults, fail-fast startup
  validation for missing required values.
* OQ-07 recorded decision (WP-0.4) — provider choice and budget; re-read it before
  fixing endpoint/model settings.
* MT-0.5-01 / MT-1.1-02 — environment naming conventions and structured logging with
  correlation id.

## Scope (in)
* Implement the remote provider against the Section 9.5 "Anthropic-compatible vision
  model" contract: send the normalized image, receive a layout caption (component
  list, text positions) per Section 9.5 stage 2, return it through the interface.
* Configuration: endpoint/base URL, model, credentials and any timeout settings as
  Section 9.10 entries with documented defaults; credentials come **only** from
  environment variables (Section 12.4), never committed (Section 20.4 item 3);
  startup validation fails fast when the provider is selected but required values are
  missing (Section 9.10).
* Cost logging: for every invocation log model, token/usage figures returned by the
  provider, and duration, as structured fields on the existing logging pipeline
  (Section 17, NFR-10) — the OQ-07 budget can only be managed from these numbers.
* Failure logging: transport errors, non-2xx responses and malformed outputs logged
  with the canonical correlation id (MT-0.5-03) and enough context to retry; the typed
  failure signal from MT-1.13-01 is raised for MT-1.13-05 to catch.
* Tests with a mocked/stubbed provider endpoint (no live calls in CI): success
  caption parsing, missing-config startup failure, error-path logging, and cost fields
  present in the log record.
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Default selection — stays disabled (MT-1.13-02); do not flip the default.
* Per-call caching — MT-1.13-04.
* Degradation to OCR-only when this provider fails — MT-1.13-05 (this task only
  produces the typed failure).
* Budget enforcement/stopping at a monthly cap: OQ-07 asks "what monthly budget?" but
  the plan defines no enforcement mechanism — log costs and record the OQ-07 budget
  decision; enforcement would be a new decision (Section 20.1 principle 5).
* The "local model" implementation — out of scope for the whole WP (see MT-1.13-01).
* Per-project provider toggles — no policy field exists in Section 7.2; not invented
  here.

## Target paths
* `backend/apps/attachments/` (remote implementation registered with the selector)
* `backend/tests/attachments/` (mocked-endpoint tests: success, missing config,
  failure logging, cost log fields)
* Environment template entry: provider settings with documented defaults (Section
  9.10)
* WP changelog entry

## Acceptance criteria
- [ ] With the remote provider selected and configured, an image fixture produces a
  layout caption through the interface — WP-1.13 acceptance, second half ("with
  provider enabled, descriptions are produced") (FR-ATT-02).
- [ ] Missing required configuration with the provider selected fails startup fast
  with a clear message (Section 9.10); with the provider not selected, startup needs
  no provider values (OQ-07 default preserved).
- [ ] Credentials appear only in the environment template as placeholder names, never
  as values (Section 12.4; Section 20.4 item 3).
- [ ] Every invocation emits structured cost logging (model, usage figures, duration)
  and every failure emits a structured error log with correlation id (Section 9.5
  "cost and failures are logged"; Section 17; NFR-10).
- [ ] Tests use a mocked endpoint — no live provider calls in CI (Section 20.4 item 2);
  lint and type check green.
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
`pytest backend/tests/attachments -k remote_provider -v` — success path with parsed
caption, fail-fast on missing config, cost/failure log assertions; plus
`uv run --directory backend ruff check .` and the documented mypy invocation (MT-0.1-02).

## Attachments
* [Section 9.5 — Attachment processing (description provider)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.10 — Configuration (description provider settings)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [OQ-07 — Which provider and monthly budget](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* OQ-07's "per project" enablement wording has no backing field in Section 7.2's
  Project Policy — implement backend-level configuration only (G-14, Section 9.10);
  if per-project enablement is required, it becomes a plan amendment first, not a
  silent policy column.
* The concrete vision endpoint/model is an OQ-07 decision — if WP-0.4 recorded no
  specific choice, keep the base URL/model fully configuration-driven with the
  Section 9.5 "Anthropic-compatible" shape and note it; do not hardcode a vendor.
* Usage figures depend on what the remote API returns; if a response omits them, log
  the absence explicitly rather than fabricating zeros — cost reporting feeds a budget
  decision and silent zeros would corrupt it.
