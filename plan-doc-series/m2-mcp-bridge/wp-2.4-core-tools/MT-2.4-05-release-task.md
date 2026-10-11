# MT-2.4-05 — Implement release_task (voluntary, no failure increment)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.4-05 |
| Title | Implement release_task (voluntary, no failure increment) |
| Parent WP | WP-2.4 — Tools: availability, details, claim, release, context (Milestone M2) |
| Requirements | FR-MCP-03, FR-LEA-01 |
| Priority | M |
| Dependencies | MT-2.4-01 (schemas), MT-2.4-04 (claim flow), MT-2.3-01..04 (API client) |
| Parent sections | 9.2 (`POST /tasks/{id}/release`), 10.5, 10.10, 19 (WP-2.4), 20.4, 20.5 |

## Context
Section 10.5 adds `release_task` as a new tool for voluntarily returning a task, with
the explicit behavior "No failure increment" — releasing is not a failed attempt, so
`attempt_number` bookkeeping and any failure counters must not be touched by it. The
tool pairs with the rules block (Section 10.6 rule 2: if a change outside scope is
truly required, release the task or flag it for human attention) and with Section
10.10, where process exit triggers a best-effort release or leaves the lease to
expire. It takes `task_id` and `reason`, calls `POST /tasks/{id}/release`, and is a
mutating call carrying an idempotency key.

## Inputs / Prerequisites
* Parent plan Section 9.2 — `POST /tasks/{id}/release`, caller: Agent.
* Parent plan Section 10.5 — `release_task` row: inputs (`task_id`, `reason`),
  behavior (no failure increment).
* Parent plan Section 10.10 — best-effort release on session end.
* MT-2.4-01 schemas; MT-2.4-04 claim handler (the state a release undoes);
  MT-2.3-01..04 client.
* Section 9.2 catalog — candidate codes: `TASK_NOT_FOUND`, `TASK_STATE_CONFLICT`,
  `LEASE_NOT_OWNED`, `LEASE_EXPIRED`, `VALIDATION_ERROR`.

## Scope (in)
* Handler for `release_task` forwarding `task_id` and `reason` to
  `POST /tasks/{id}/release` with idempotency key attached.
* Response shaping: the released task's new state and a next-action hint (typically
  re-entering availability), compact and structured per Section 10.5 rules.
* Error mapping with hint/next action: `LEASE_NOT_OWNED` (releasing a task the
  caller does not hold), `LEASE_EXPIRED` (lease already gone — nothing to do, re-list
  via `get_available_tasks`), `TASK_STATE_CONFLICT` (task no longer in a releasable
  state), `TASK_NOT_FOUND`, `VALIDATION_ERROR` for missing `reason` if the schema
  requires it.
* Unit tests: successful release, releasing a foreign lease, releasing an expired
  lease, idempotent retry of the same release, and a guard test asserting the
  request/response shape carries no attempt/failure-increment field the bridge could
  populate (the no-increment behavior is the backend's contract, asserted via the
  mocked response).

## Out of scope
* Backend lease bookkeeping and failure-attempt counters — WP-1.6.
* Automatic best-effort release at process exit — bridge lifecycle in WP-2.1
  (this tool is the building block it calls).
* Forced release by the Owner or lease-sweeper expiry — backend jobs
  (Section 9.9) and web UI.
* Checkpoint/submit flows — WP-2.6.

## Target paths
* `bridge/src/` (release handler module)
* `bridge/tests/` (handler tests)
* WP changelog entry

## Acceptance criteria
- [ ] `release_task` accepts exactly `task_id` and `reason` per Section 10.5; no
  `project_id` (Section 10.3).
- [ ] The tool doc/response states and tests prove no failure increment is requested
  or implied — release is voluntary and does not consume an attempt (Section 10.5).
- [ ] `LEASE_NOT_OWNED`, `LEASE_EXPIRED`, `TASK_STATE_CONFLICT`, `TASK_NOT_FOUND`
  surface with exact catalog codes, hint and next action.
- [ ] The mutating call carries an idempotency key and a retried release does not
  double-release (MT-2.3-03, NFR-12).
- [ ] Tests pass in CI; only Section 9.2 codes used (Section 20.4 items 2, 5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the release handler tests, e.g. `uv run pytest bridge/tests/ -k release_task`;
assert success shape, lease-state errors with hints, and idempotent retry behavior.

## Attachments
* [Section 10.5 — Tool catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.10 — Resilience](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "No failure increment" is backend-enforced; the bridge can only avoid requesting
  anything that would trigger it. If the release endpoint's contract is ambiguous,
  raise an OQ-xx before assuming a parameter shape.
* Agents may call release on an already-expired lease during shutdown races — the
  `LEASE_EXPIRED` path must be a clean, non-alarming next action, not a crash.
