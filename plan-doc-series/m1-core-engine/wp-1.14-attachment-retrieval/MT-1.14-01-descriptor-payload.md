# MT-1.14-01 — Define the Attachment Descriptor Payload Shape for Task Payloads

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.14-01 |
| Title | Define the attachment descriptor payload shape for task payloads |
| Parent WP | WP-1.14 — Attachment retrieval API (Milestone M1) |
| Requirements | FR-ATT-03 |
| Priority | M |
| Dependencies | MT-1.11-04 (descriptor fields on attachment listing), MT-1.12-08 (pipeline fills token count, description), MT-1.13-05 (description may be absent) |
| Parent sections | 9.2, 9.5, 19.1 (WP-1.14), 20.4, 20.5 |

## Context
FR-ATT-03: "Default task payload contains only attachment descriptors (id, filename,
size, token count, short description)." Section 19 (WP-1.14) lists "descriptor shape"
as the first slice — the contract that keeps task payloads small and lazy: a task
response embeds descriptors only, never attachment content, which is fetched on demand
from the `content` endpoint (FR-ATT-04, implemented by MT-1.14-02). MT-1.11-04 already
fixed the descriptor field names on the attachment listing endpoints and explicitly
left "embedding descriptors in the task payload" to a later task — this is that task,
and it must reuse the same field names so there is one descriptor shape across the API
(Section 20.5 traceability; G-01-style drift prevention).

## Inputs / Prerequisites
* MT-1.11-04 — descriptor fields already exposed by `GET /tasks/{id}/attachments`
  and `GET /attachments/{id}` (id, filename, size, processing_status, plus token count
  and short description as null until the pipeline fills them).
* MT-1.12-08 — token count and short description produced by the pipeline for
  `ready` attachments.
* MT-1.13-05 — descriptions may be legitimately absent (OCR-only degradation); the
  shape must tolerate an empty/null short description without failing serialization.
* Parent plan Section 9.2 — task endpoints that must carry the descriptors; Section
  9.5 — derived data each descriptor summarizes.
* MT-0.5-04 — cursor pagination conventions (unchanged; descriptors ride inside task
  payloads, they are not a new list endpoint).

## Scope (in)
* Define the descriptor object embedded in task payloads with exactly the FR-ATT-03
  fields — `id`, `filename`, `size`, `token count`, `short description` — using the
  field names established by MT-1.11-04 (one shape, no aliases).
* Embed descriptors in the task payload wherever a task is returned (task detail and
  any response that represents a task per Section 9.2), replacing any raw content,
  storage paths or oversized fields.
* Nullable semantics preserved: token count and short description are null until the
  pipeline fills them (MT-1.11-04 behavior) and stay null after OCR-only degradation
  (MT-1.13-05).
* Serialization tests: a task with attachments serializes descriptors only; a task
  with `processing` attachments shows nulls; no content bytes or derived text appear
  in the payload.
* OpenAPI updated, schema diff reviewed (Section 20.4 item 4); changelog note (item 7).

## Out of scope
* The attachment listing endpoints — MT-1.11-04 already delivered them.
* The content endpoint, format resolution, pagination and banner — MT-1.14-02 …
  MT-1.14-05.
* Producing token counts and summaries — WP-1.12 (this task only exposes fields).
* Bridge-side response shaping of `get_task_details` — WP-2.4 (it will consume this
  payload shape).
* Web/mobile rendering of descriptors — WP-4.x / WP-5.x.

## Target paths
* `backend/apps/tasks/` (task serializers embedding the descriptor)
* Shared descriptor serializer referenced from `backend/apps/attachments/` (single
  shape source from MT-1.11-04)
* `backend/tests/` (task payload descriptor tests)
* `schemas/` — OpenAPI snapshot updated (MT-1.1-04 pipeline)
* WP changelog entry

## Acceptance criteria
- [ ] Task payloads contain attachment descriptors with exactly the FR-ATT-03 fields
  under the MT-1.11-04 field names — one descriptor shape across listing and task
  payloads (FR-ATT-03; Section 20.5).
- [ ] No attachment content, derived text or storage path appears in a task payload
  (FR-ATT-03 "only attachment descriptors").
- [ ] Token count and short description are null before `ready` and after OCR-only
  degradation without breaking serialization (MT-1.11-04, MT-1.13-05).
- [ ] OpenAPI snapshot updated and schema diff reviewed (Section 20.4 item 4).
- [ ] Error codes used exist in the Section 9.2 catalog (item 5); no secrets or
  environment-specific paths committed (item 3).
- [ ] Tests, lint and type check green in CI (item 2); changelog note added (item 7).

## Test command
`pytest backend/tests -k task_descriptor or attachment_descriptor -v` — descriptor
field set on task payloads matches MT-1.11-04's serializer field set exactly,
null-before-ready and null-after-degradation cases, absence of content fields; then
regenerate the OpenAPI snapshot and confirm a reviewed diff (MT-1.1-04 flow).

## Attachments
* [FR-ATT-03 — Descriptor-only task payload](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — REST API surface (Tasks)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.14 deliverables](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Two serializers drifting apart (listing vs. task payload) is the exact G-01 failure
  mode — derive both from one serializer/shape definition and assert field-set parity
  in tests rather than trusting review.
* "Default task payload" is ambiguous about which task responses embed descriptors
  (detail only, or also create/transition responses) — default to every response that
  returns a task object, and note the interpretation in the changelog so WP-2.4 and
  WP-4.x build against a settled contract.
* Size and token-count units are whatever MT-1.11-04 and WP-1.12 already established —
  do not redefine units here; link to those documents.
