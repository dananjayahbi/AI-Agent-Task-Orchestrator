# MT-2.6-01 — Implement log_task_checkpoint returning next-due hint and new expiry

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.6-01 |
| Title | Implement log_task_checkpoint returning next-due hint and new expiry |
| Parent WP | WP-2.6 — Tools: checkpoint and submission with Git evidence (Milestone M2) |
| Requirements | FR-LEA-03 |
| Priority | M |
| Dependencies | WP-1.8 (checkpoint endpoint), WP-1.6 (lease semantics), WP-2.4 (tool plumbing conventions) |
| Parent sections | 10.5, 8.6, 9.2, 19 (WP-2.6), 20.4, 20.5 |

## Context
Section 10.5: `log_task_checkpoint` takes `task_id`, `message`, `percentage`, returns
the new expiry, and a `LEASE_EXPIRED` error instructs the agent to stop and re-claim.
Section 8.6: each valid checkpoint sets `lease_expires_at` = min(now + duration,
`lease_acquired_at` + `lease_max_total_minutes`); after the hard cap the owner must
submit or release; late checkpoints from a old owner return `LEASE_EXPIRED` and must
not resurrect the lease. FR-LEA-03 fixes the extension rule, and RISK-02's mitigation
puts a `next_checkpoint_due` hint in every tool response so agents never forget to
checkpoint. This is WP-2.6's first slice: the checkpoint tool the rest of the
submission flow builds on.

## Inputs / Prerequisites
* Parent plan Section 10.5 — `log_task_checkpoint` inputs and error behavior.
* Parent plan Section 8.6 — lease extension formula, hard cap, late-checkpoint rule,
  fencing generation.
* Parent plan Section 9.2 — `POST /tasks/{id}/checkpoints` endpoint and
  `LEASE_EXPIRED` catalog code.
* WP-1.8 — backend checkpoint model, ownership validation and endpoint.
* WP-1.6 — lease claim/expiry semantics the endpoint enforces.
* Rules block item 5 (Section 10.6) — checkpoint cadence expectations set on agents.

## Scope (in)
* The `log_task_checkpoint` tool handler calling `POST /tasks/{id}/checkpoints` with
  `task_id`, `message`, `percentage`, carrying the session's idempotency key
  (Section 10.10, ADR-012).
* Response assembly: new `lease_expires_at` (Section 8.6 formula) plus the
  `next_checkpoint_due` hint (RISK-02), so the agent knows exactly when to send the
  next one.
* `LEASE_EXPIRED` mapping with a stable code, hint and next action telling the agent
  to stop and re-claim (Section 10.5); late checkpoints must never resurrect a lease
  (Section 8.6) — asserted against the real backend.
* Hard-cap behavior surfaced: when the extension hits
  `lease_acquired_at + lease_max_total_minutes`, the response guides the agent to
  submit or release rather than implying more lease is coming.
* Structured tool output per Section 10.5 rules (compact, no project id).
* Unit/integration tests: normal extension, cap-clamped extension, expired-lease
  rejection with hint, idempotent replay of the same checkpoint.

## Out of scope
* Backend checkpoint model, ownership validation, endpoint — WP-1.8.
* The lease sweeper that applies T5 — WP-1.7.
* Submission flow — MT-2.6-04.
* Optional output-tail attachment per checkpoint — deferred, MT-2.6-06 (G-11).
* Rules text telling agents when to checkpoint — WP-2.7.

## Target paths
* `bridge/` — `log_task_checkpoint` tool handler and response assembly
* `bridge/tests/` — checkpoint tool tests
* WP changelog entry

## Acceptance criteria
- [ ] The tool accepts `task_id`, `message`, `percentage` and returns the new expiry
  (Section 10.5).
- [ ] The response includes the `next_checkpoint_due` hint (RISK-02 mitigation)
  alongside the new expiry.
- [ ] The extension follows the Section 8.6 formula and clamps at the hard cap
  (FR-LEA-03), with guidance to submit or release at the cap.
- [ ] A checkpoint from an expired/old lease returns `LEASE_EXPIRED` with hint and
  next action (stop and re-claim) and does not resurrect the lease (Section 8.6).
- [ ] Only catalog error codes are used (Section 20.4 item 5); lint/type/tests green
  (item 2); changelog note added (item 7).

## Test command
`uv run pytest bridge/tests/ -k log_task_checkpoint -q` — assert new expiry and
next-due hint on success, cap clamping, `LEASE_EXPIRED` with hint on a stale
checkpoint (zero state change), and idempotent replay; then the full bridge suite
stays green.

## Attachments
* [Section 8.6 — Lease semantics in detail](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Tool catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Hint drift: `next_checkpoint_due` must be derived from the same lease numbers the
  response returns, or agents will checkpoint against a stale deadline — compute both
  from one source.
* Do not weaken the late-checkpoint rule to be "helpful": a resurrected lease after
  T5 breaks fencing (Section 8.6, ADR-012).
* Fencing generation must be carried by the call like every mutating call; dropping
  it here would let a slow former owner extend a reclaimed lease.
