# MT-3.6-03 — Implement latest_feedback propagation into get_task_details

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.6-03 |
| Title | Implement latest_feedback propagation into get_task_details |
| Parent WP | WP-3.6 — Human review decisions API (Milestone M3) |
| Requirements | FR-AUD-05 |
| Priority | M |
| Dependencies | MT-3.6-01 (T16 sets `latest_feedback`), MT-3.6-02 (decision records), WP-2.4 (`get_task_details` tool) |
| Parent sections | 7.2, 8.2 (T16), 10.5, 11.5, 19 (WP-3.6), 20.4, 20.5 |

## Context
Section 7.2 adds `latest_feedback` **(new)**: "Text from auditor/human, shown to the
next coder." T16's side effect sets it (Section 8.2), and Section 11.5: a
request-changes note "becomes `latest_feedback`, returns to `pending`". Section 10.5's
`get_task_details` includes "feedback from previous attempts". WP-3.6's acceptance:
"feedback appears in the next coder's task details." This task closes that loop —
the human's note must travel from the review decision to the agent's orientation
call, so the next attempt starts informed instead of guessing.

## Inputs / Prerequisites
* Parent plan Section 7.2 — `latest_feedback` field semantics (verbatim).
* Parent plan Section 8.2 T16 — who sets it and when.
* Parent plan Section 10.5 — `get_task_details` responsibilities ("feedback from
  previous attempts") and output discipline.
* MT-3.6-01 — the endpoint whose T16 path writes `latest_feedback`.
* WP-2.4 (MT-2.4-03) — existing `get_task_details` implementation and response
  schema to extend.

## Scope (in)
* Persisting `latest_feedback` on the Task as set by T16 (`request_changes`; also
  populated per Section 11.5's wording for the reassign path where a note is
  provided — the plan sets `latest_feedback` under T16 as the side effect; follow
  T16 exactly).
* Surfacing `latest_feedback` in `get_task_details`' structured output so the next
  coder sees the most recent human/auditor note, including the decision context it
  came from (the latest feedback is the current T16 note; "most recent wins"
  overwrite semantics — the field name is the contract).
* Contract updates: `get_task_details` response schema (public tool contract —
  schema diff reviewed, Section 20.4 item 4), and the backend task-details payload
  if separate.
* Tests: after T16 request-changes, the next `get_task_details` call returns the
  note; a subsequent decision overwrites it (latest wins); tasks with no feedback
  return an empty/absent value without breaking existing consumers; coder role sees
  it, other callers unaffected by the change.

## Out of scope
* Endpoint and T16 side-effect implementation — MT-3.6-01.
* The Review Decision model — MT-3.6-02 (the decision row is the record; the Task
  field is the fast read path per Section 7.2).
* Rendering feedback in web/mobile UIs — WP-4.6/WP-5.7 detail views.
* Historical feedback lists (all attempts) — the plan specifies `latest_feedback`
  only; older notes live in Review Decision rows/audit log.

## Target paths
* `backend/` — task-details payload including `latest_feedback`
* `bridge/` — `get_task_details` output schema and assembly
* `backend/tests/`, `bridge/tests/` — propagation tests
* Contract/OpenAPI updates (schema diff reviewed)
* WP changelog entry

## Acceptance criteria
- [ ] After an Owner request-changes (T16), the next coder's `get_task_details`
  includes the note as `latest_feedback` (WP-3.6 acceptance, Section 11.5,
  FR-AUD-05).
- [ ] A newer T16 note overwrites the previous one (Section 7.2 "latest" semantics),
  with no accumulation invented.
- [ ] Tasks that never received feedback return the field empty/absent without
  breaking consumers; no plan-unspecified feedback history is exposed.
- [ ] Tool contract updated and schema diff reviewed (Section 20.4 item 4); only
  catalog codes used anywhere in new error paths (item 5); lint/type/tests green
  (item 2); changelog note added (item 7).

## Test command
`pytest backend/tests -k latest_feedback -q` and
`uv run pytest bridge/tests/ -k task_details_feedback -q` — assert propagation from
T16 to the tool response, overwrite semantics, empty-state safety, and schema
snapshot update; both suites stay green.

## Attachments
* [Section 7.2 — `latest_feedback` field](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Tool catalog (`get_task_details`)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Where exactly `latest_feedback` lives (Task field vs joined read) must match
  Section 7.2's entity placement — check the field's owning entity before modeling;
  do not store it only on the decision row if the plan puts it on the Task.
* Feedback text is human-authored and may contain sensitive context — it flows to
  agents as data (P10 posture applies to agent-consumed text) and must not be logged
  in full (Section 12.4 scrubbing).
* If T16's write happens in MT-3.6-01 later than this task, land the read path
  against the contract with a gated integration test rather than a fake writer.
