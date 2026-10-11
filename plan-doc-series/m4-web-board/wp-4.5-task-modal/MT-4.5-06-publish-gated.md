# MT-4.5-06 — Implement the publish action gated on attachment readiness

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.5-06 |
| Title | Implement the publish action gated on attachment readiness |
| Parent WP | WP-4.5 — Task creation/edit modal and attachment uploader (Milestone M4) |
| Requirements | FR-WEB-03, FR-ATT-07 |
| Priority | M |
| Dependencies | MT-4.5-01 (modal), MT-4.5-05 (uploader statuses), WP-1.4 (publish endpoint), WP-1.12 (readiness source), WP-4.3 (stream events) |
| Parent sections | 8.2 (T2), 13.2, 9.5, 9.2, 19 (WP-4.5), 20.4, 20.5 |

## Context
T2 (Section 8.2): `draft` → `pending`, trigger Publish, actor O, guards — "Required
fields valid; attachments `ready` (or override); dependencies exist". FR-ATT-07:
"tasks can be published only when attachments are `ready` or explicitly overridden."
WP-4.5's acceptance: "task with three attachments reaches `pending` only when all
are ready (or override chosen)." Section 9.2 serves publishing via
`POST /tasks/{id}/transition` (publish, unpublish, archive). This final slice builds
the publish action and its readiness gate — the moment where modal, uploader and
state machine meet.

## Inputs / Prerequisites
* Parent plan Section 8.2 — T2 guards (verbatim) and the "UI sends the `version` it
  saw" rule.
* Parent plan FR-ATT-07 and Section 9.5 — `ready` semantics; `failed` is not ready.
* Parent plan Section 9.6 — `attachment.ready|failed` events keeping the gate state
  live.
* Parent plan Section 9.2 — `POST /tasks/{id}/transition` publish action.
* MT-4.5-01 (modal), MT-4.5-05 (uploader and per-file statuses); WP-1.4's publish
  enforcement is the authority.

## Scope (in)
* A publish action in the task modal/board context that sends T2 via
  `POST /tasks/{id}/transition` (publish) with the `version` the client saw.
* Readiness gate: publish is blocked while any attached file's status is `uploaded`
  or `processing` — the button shows why (per-file statuses from MT-4.5-05's stream
  events) and becomes available when all are `ready`; a `failed` file blocks with its
  reason visible.
* Explicit override path: an "publish anyway" choice where the operator consciously
  overrides non-ready attachments — surfaced only when the backend's T2 policy
  allows override for this task, never a silent bypass (FR-ATT-07's "explicitly
  overridden").
* Other T2 guards surfaced: missing required fields (from MT-4.5-01..04 validation)
  and non-existent dependencies block publish with friendly reasons; server
  `VALIDATION_ERROR` / `ATTACHMENT_NOT_READY` / `TASK_STATE_CONFLICT` /
  `VERSION_CONFLICT` responses map to actionable messages (Section 13.3).
* Live gating: `attachment.ready|failed` events update the gate without manual
  refresh (Section 9.6).
* Component tests: blocked while any file non-ready; unblocks when the last file
  reports `ready`; three-attachment scenario matches WP-4.5 acceptance; explicit
  override flow; failed-file blocking; stale-version conflict handling.

## Out of scope
* Uploader mechanics and status plumbing — MT-4.5-05.
* Server-side readiness enforcement and override policy — WP-1.4 (the gate there is
  authoritative; the client mirrors it).
* Unpublish/archive (same endpoint, different actions) — not part of this slice's
  acceptance.
* Agent-visible behavior after publish (`pending`, claimable) — WP-2.4.

## Target paths
* `web/` — publish action, readiness gate, override affordance
* `web/tests/` — publish gating tests
* WP changelog entry

## Acceptance criteria
- [ ] A task with three attachments reaches `pending` only when all three report
  `ready`, or after an explicit override is chosen (WP-4.5 acceptance, FR-ATT-07,
  T2 guard).
- [ ] While any attachment is `uploaded`/`processing`, publish is blocked with the
  per-file status explaining why; `attachment.ready|failed` events update the gate
  live (Sections 9.5, 9.6).
- [ ] Publish sends T2 with the client's `version`; `VERSION_CONFLICT` and
  `TASK_STATE_CONFLICT` map to friendly refresh guidance (Section 8.2).
- [ ] Required-field and dependency guards surface before the server call, and server
  rejections (`VALIDATION_ERROR`, `ATTACHMENT_NOT_READY`) map to actionable messages
  (Sections 8.2, 13.3).
- [ ] The override choice is explicit and recorded in the UI flow — never the default
  (FR-ATT-07 "explicitly overridden").
- [ ] Only catalog error codes used (Section 20.4 item 5); lint/type/tests green
  (item 2); changelog note added (item 7).

## Test command
`npm test -- -t publish-gating` — drive the three-attachment scenario: publish blocked
until all `ready`, unblock on the final `attachment.ready` event, explicit-override
path, failed-file block, and conflict mappings; then the full web suite stays green.

## Attachments
* [Section 8.2 — Transition table (T2)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.5 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The server is the real gate — client gating is UX; a bypassed client must still
  fail server-side, so assert both layers in the test (WP-1.4's behavior under
  WP-4.5's acceptance).
* Override semantics ("or override") are the one soft spot in T2: if WP-1.4 defines
  the override mechanism differently (flag on the transition call), conform to it —
  do not invent a second mechanism; record any gap as an open question.
* Live gating depends on the stream; if events are missed (reconnect), the gate must
  re-read statuses rather than trust a stale "ready" — test a missed-event recovery.
