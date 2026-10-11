# MT-2.6-04 — Implement resolution upload with idempotency

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.6-04 |
| Title | Implement resolution upload with idempotency |
| Parent WP | WP-2.6 — Tools: checkpoint and submission with Git evidence (Milestone M2) |
| Requirements | FR-MCP-07, ADR-012 |
| Priority | M |
| Dependencies | MT-2.6-02 (verified branch/sha), MT-2.6-03 (captured patch), WP-3.2 (resolution endpoint), WP-1.5 (state machine transitions) |
| Parent sections | 10.5, 10.10, 9.2, 8.2 (T7, T8), 19 (WP-2.6), 20.4, 20.5 |

## Context
Section 10.5: `submit_task_resolution` uploads the verified evidence and the bridge's
outcome states are `to_be_audited` or `in_human_review`. Section 8.2 defines the
transitions: T7 (`in_progress` → `to_be_audited`, guards: lease owner and not
expired, resolution valid, `audit_required` true, not self-flagged, scope check ok)
and T8 (`in_progress` → `in_human_review` when `requires_human_attention` is true or
changed files are outside scope, with `review_reason` `self_flagged` or
`scope_violation`). Section 9.2's submission row is `POST /tasks/{id}/resolution`, and
"all mutating endpoints accept an idempotency key header" — reinforced by Section
10.10 ("all mutating calls carry idempotency keys") and ADR-012. The parent plan's
WP-2.6 dependency note records that the patch endpoint may be built jointly with
WP-3.4.

## Inputs / Prerequisites
* Parent plan Section 10.5 — submission inputs and outcome states.
* Parent plan Section 8.2 — T7/T8 guards and side effects.
* Parent plan Section 9.2 — `POST /tasks/{id}/resolution`, idempotency key header,
  catalog codes.
* Parent plan Section 10.10 — resilience contract for in-flight submissions.
* MT-2.6-02, MT-2.6-03 — verified branch/sha and captured patch + file list.
* WP-3.2 — backend resolution model, endpoint, scope check, transition application.
* Section 18 concurrency row — "double submit with same idempotency key" test layer.

## Scope (in)
* Assembling the submission payload: `task_id`, verified `git_branch`, `commit_sha`,
  `execution_summary`, `requires_human_attention`, `risk_justification`, plus the
  captured patch and changed-file list, from one submission attempt.
* Uploading to `POST /tasks/{id}/resolution` with an idempotency key (Section 9.2,
  ADR-012); a replay with the same key returns the original result instead of a
  second transition (Section 18 concurrency row).
* Reporting the outcome to the agent: `to_be_audited` or `in_human_review` per T7/T8,
  including the `review_reason` when escalated, in compact structured form.
* Mapping backend failures to catalog codes with hint and next action:
  `LEASE_EXPIRED` / `TASK_STATE_CONFLICT` tell the agent to stop and re-orient
  (Section 11.1 step 7), never a blind retry loop.
* Success acknowledgment handoff to MT-2.6-05 (the payload is "sent" only when the
  backend acknowledges).
* Tests: first submit transitions once; same-key replay returns the same outcome with
  no second transition; self-flagged submit lands in `in_human_review` with
  `self_flagged`; normal submit lands in `to_be_audited`; stale lease rejected with
  hint.

## Out of scope
* Branch/sha verification — MT-2.6-02; patch capture — MT-2.6-03.
* Local retention and retry during outages — MT-2.6-05.
* Backend endpoint, scope check (R2 input), transition storage — WP-3.2, WP-1.5.
* The audit/verdict path after `to_be_audited` — WP-3.5.
* Server-side idempotency middleware — WP-1.1/WP-1.15 (consumed here).

## Target paths
* `bridge/` — `submit_task_resolution` handler: payload assembly, upload, outcome
  reporting
* `bridge/tests/` — submission and idempotency tests
* WP changelog entry

## Acceptance criteria
- [ ] The payload carries all Section 10.5 inputs plus the captured evidence
  (branch, sha, patch, file list — FR-MCP-07).
- [ ] The upload sends an idempotency key; a double submit with the same key yields
  one transition and one identical response (ADR-012, Section 18 concurrency row).
- [ ] The agent is told the actual outcome state — `to_be_audited` (T7) or
  `in_human_review` with `review_reason` (T8) — or a structured error with hint and
  next action.
- [ ] `LEASE_EXPIRED` and `TASK_STATE_CONFLICT` responses instruct stop-and-orient
  behavior, using only catalog codes (Section 9.2, Section 11.1 step 7).
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`uv run pytest bridge/tests/ -k submit_resolution -q` — assert T7 and T8 outcomes,
same-key idempotent replay with a single transition, and stale-lease rejection with
hint; then the full bridge suite stays green (concurrency cases against real Postgres
per Section 18).

## Attachments
* [Section 8.2 — Transition table (T7, T8)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Tool catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan notes WP-2.6's patch endpoint may be built jointly with WP-3.4 — if
  WP-3.2's endpoint is not yet available, land against the contract with an
  integration test gated on it; do not invent a temporary submission shape.
* Idempotency key scope (per session? per attempt?) must match the backend's
  implementation — coordinate with WP-3.2; a mismatch silently double-submits.
* Encoding a success-only retry (ignoring the outcome state) would hide escalations
  from the agent — always surface `in_human_review` and its reason.
