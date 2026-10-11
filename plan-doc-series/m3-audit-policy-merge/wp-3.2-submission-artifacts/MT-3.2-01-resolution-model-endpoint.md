# MT-3.2-01 — Create the Task Resolution model and submission endpoint

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.2-01 |
| Title | Create the Task Resolution model and submission endpoint |
| Parent WP | WP-3.2 — Submission handling and artifacts (Milestone M3) |
| Requirements | FR-AUD-01, FR-TSK-03 |
| Priority | M |
| Dependencies | MT-3.1-01 (policy persisted); WP-1.6 complete (claim/lease owner checks); MT-1.5-01 (transition registry) |
| Parent sections | 7.2 (Task Resolution), 8.2 (T7 guard inputs), 9.2 (submission endpoints), 19 (WP-3.2), 20.4, 20.5 |

## Context
Section 7.2 defines Task Resolution — one record per submission attempt holding branch,
commit, summaries, stats, changed files, the risk flag and the submitting session.
Section 9.2 exposes `POST /tasks/{id}/resolution` (agent, lease owner) and
`GET /tasks/{id}/resolutions` (owner), with idempotency keys on all mutating endpoints.
This is the backend half of submission (the bridge captures and uploads evidence in
WP-2.6); without the model and endpoint, transitions T7/T8/T10 (MT-3.2-05) have
nothing to store and the auditor flow (WP-3.3) has nothing to review.

## Inputs / Prerequisites
* Parent plan Section 7.2 — Task Resolution fields: `id`, `task_id`, `attempt_number`,
  `branch_name`, `commit_sha`, `execution_summary`, `diff_summary` (files, insertions,
  deletions), `changed_files`, `requires_human_attention`, `risk_justification`,
  `submitted_by_session`, `submitted_at`.
* Parent plan Section 9.2 — Submission endpoints and idempotency-key rule; caller is
  the Agent (lease owner).
* MT-3.1-01 — the project whose policy the submission runs under (`audit_required_default`).
* MT-1.5-01 — the state-machine service through which the eventual transition fires
  (Section 9.1: `tasks` owns state changes).
* WP-2.6 (MT-2.6-04) — bridge resolution upload shape; align the request contract with
  it rather than inventing a parallel one.

## Scope (in)
* Task Resolution model per Section 7.2, linked to task and `attempt_number` so there
  is exactly one resolution per submission attempt.
* `POST /tasks/{id}/resolution`: accepts the lease-owner agent's payload (branch, sha,
  summaries, requires_human_attention, risk_justification), stores the resolution row,
  honors the idempotency key header (retried POST returns the stored resolution).
* Authorization: only the current lease owner (agent token) may submit; other callers
  get catalog errors (`ROLE_NOT_PERMITTED`, `TASK_STATE_CONFLICT`, `LEASE_NOT_OWNED`
  as applicable) — never new codes.
* `GET /tasks/{id}/resolutions` for owners listing a task's attempts.
* Persisting the attempt linkage so a later attempt cannot overwrite an earlier
  resolution.
* Unit tests: storage, idempotency, ownership and per-attempt uniqueness.
* Add a WP changelog note.

## Out of scope
* Patch artifact upload and storage — MT-3.2-02.
* Authoritative stats/changed-file computation from the patch — MT-3.2-03.
* Scope violation evaluation — MT-3.2-04.
* Firing T7/T8/T10 — MT-3.2-05 (this task stores the resolution the transitions use).
* Bridge-side evidence capture, branch/sha verification, patch upload — WP-2.6.
* Serving the stored patch — `GET /resolutions/{id}/patch` in MT-3.2-02.

## Target paths
* `backend/apps/tasks/` (Task Resolution model, submission and list endpoints)
* `backend/` migrations (resolution table)
* `backend/tests/` (submission endpoint tests)
* WP changelog entry

## Acceptance criteria
- [ ] Task Resolution persists exactly the Section 7.2 field set with no extras
  (Section 20.5 traceability).
- [ ] One resolution exists per (`task_id`, `attempt_number`); a repeated idempotent
  POST returns the same row rather than creating a duplicate.
- [ ] Only the lease owner may `POST /tasks/{id}/resolution`; non-owners and
  non-lease-holders are rejected with catalog codes (Section 9.2 catalog;
  Section 20.4 item 5).
- [ ] `GET /tasks/{id}/resolutions` lists attempts for the owner, newest usable for
  the auditor flow (FR-AUD-01 input).
- [ ] Public contract (OpenAPI) updated for the endpoints with schema diff reviewed
  (Section 20.4 item 4).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k resolution_submission -q` and confirm: happy-path store
with Section 7.2 fields, idempotent replay, lease-owner-only rejection using catalog
codes, and per-attempt uniqueness; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 7.2 — Task Resolution entity](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — Submission endpoints](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.2 slices and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The bridge (WP-2.6) and this endpoint must agree on the payload; the plan fixes the
  server-side model but not the wire shape in detail — derive it from Section 10.5
  `submit_task_resolution` inputs and flag any gap as OQ-xx rather than diverging.
* `diff_summary` and `changed_files` arrive empty or provisional until MT-3.2-03
  recomputes them authoritatively from the patch (Section 9.7); make the sequencing
  explicit so the Policy Engine never sees dual sources of truth.
