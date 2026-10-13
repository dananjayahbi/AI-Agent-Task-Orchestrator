# WP-3.3 — Auditor claim and verdict API

## Unreleased

### Done — MT-3.3-01 … 05 (all five, in order)

- **MT-3.3-01 auditor role gating (T11).** `claim_task` takes a declared
  `role` (`coder` default, `auditor` opt-in) validated inside the claim
  lock against the Section 12.2 claim cells: `pending`→coder,
  `to_be_audited`→auditor; the other role's claimable state answers
  403 `ROLE_NOT_PERMITTED` (new `leases.exceptions.RoleNotAllowed`),
  every other state still falls to the registry's 409
  `TASK_STATE_CONFLICT` (scope check first, catalog codes only).
  `WorkView`'s serializer gains the same `role` param — `auditor`
  lists `to_be_audited`, `coder` (default) lists unblocked `pending`,
  never mixed. Successful auditor claims run T11
  (`audit.claimed` / reason `audit_claimed`, both §9.6/§8.4 members):
  flag-only (no state change), audit lease with the Section 8.6
  duration/cap/fencing, `claimed_role=auditor`, attempt number intact.
- **MT-3.3-02 auditor independence.** Server-side and attempt-scoped:
  `apps/audit/independence.py` compares the claiming session against
  the current attempt's `TaskResolution.submitted_by_session` (T7's
  clear keeps it) and against the coder's §7.2 `AgentSession.agent_label`
  (lookup skipped when no row is on record); a missing current-attempt
  resolution fails **closed**. Same session or label → 409
  `AUDITOR_SAME_AS_CODER` (claim-conflict family) with no lease and no
  state change; a historical attempt's coder never blocks a later
  auditor. The verdict service re-runs the same function (MT-3.3-05's
  recheck). Wave 7 exit criterion covered.
- **MT-3.3-03 audit lease expiry (T11/T12).** T11's lease obeys the
  shared policy duration/hard cap (`extend_lease` reused, no parallel
  logic); the sweeper's selection widens to `TO_BE_AUDITED` rows with
  an auditor lease past expiry and dispatches T12
  (`task.lease_expired` / reason `lease_expired`), which clears the
  lease, bumps `audit_retry_count` (new §7.2-adjacent Task column with
  a non-negative DB check, migration `tasks.0008`), and never leaves
  `to_be_audited` nor touches the resolution. Coder branches (T5/T7)
  byte-identical; `SweepReport.audit_released` counts the new branch.
- **MT-3.3-04 Audit Report model + listing.** `apps.audit.models.AuditReport`
  persists exactly §7.2's field set (`task`/`resolution` FKs spelled
  `task_id`/`resolution_id`, auditor identity, evidence, confidence
  1-5 with validator + DB check, notes, proposed verdict enum,
  `policy_decision`/`policy_rule_results` nullable for the MT-3.4-06
  engine, `created_at`; index `(task, created_at)`). Reports accumulate
  one per verdict across T12 retries. `GET /tasks/{id}/audit-reports`
  (Owner or auditor-scoped agent; `CanReadAuditReports`) serves
  pagination.md's cursor envelope, newest first
  (`(created_at, id)` composite cursor).
- **MT-3.3-05 audit verdict endpoint (T13/T14, invariant 4).**
  `POST /tasks/{id}/audit-verdict` accepts the §10.5 shape
  (`task_id`, `session_id`, `lease_generation`, verdict
  `pass`/`flag_risk`/`fail`, confidence 1-5, notes, evidence with the
  required `commands` structure), refuses non-owners and stale leases
  through the existing fencing gates, re-checks independence, stores
  the Audit Report, then consults the fail-closed decision seam
  (`resolve_audit_decision`, the T10 `resolve_policy_decision` pattern):
  with no engine installed a `pass` verdict escalates as
  `policy_forced_review`, `flag_risk`/`fail` as `auditor_flagged` —
  the endpoint never approves (invariant 8.3.4). An approving hook is
  the only path to T13 (`audit.passed` / `audit_passed`, merge-pending,
  lease cleared); escalations run T14 → `IN_HUMAN_REVIEW`
  (`audit.escalated` / `audit_escalated`, review reason from the
  decision, lease cleared). Idempotency-Key replay returns the stored
  201; unkeyed retries die at the state gate. Owner submission is
  refused (§12.2 Owner=No wins over §9.2's caller column; deferred to
  WP-4.8's review panel).

### Decisions

- T11/T13 are registry **flag-only** rows (`to_state=None`): §8.2's
  "(audit lease)"/"merge-pending" cells are not task states.
- `AUDITOR_SAME_AS_CODER` is a 409 (claim-conflict family), matching
  the authorization-matrix probe's `ok` codes.
- T13/T14 clear the audit lease on success (prevents post-verdict T12
  noise); T12 itself re-checks the expired auditor lease inside the
  dispatch guard.
- Reason codes added to `TransitionReason` only where §9.6/§8.4
  already list them (`audit_claimed`, `audit_passed`,
  `audit_escalated`); T12 reuses `lease_expired`. No invented codes.
- All four registry rows register lazily via `ensure_audit_wired()`
  (claim auditor path, verdict service, sweeper audit branch) — the
  MT-1.5-04 wiring seam; `wp33_helpers.restore_audit_registry` is
  autouse in every WP-3.3 suite and also resets the decision hook.
- Fail-closed default reasons: `policy_forced_review` (verdict pass)
  vs `auditor_flagged` (flag_risk/fail, §8.4 R8's definition).

### Deviations / recorded readings (open questions for the parent plan)

- `audit_retry_count` is a §7.2 gap fill required by MT-3.3-03's
  "audit_retry_count + 1" (added with a non-negative DB constraint).
- §7.2 has no `acceptance_criteria_results` column for the report;
  the endpoint nests it inside the evidence JSON when supplied.
- Reports GET admits Owner + auditor-scoped agents (coder/device 403).

### Cross-WP touchpoints (coordinated, minimal)

- `leases/` (claim/serializers/views/exceptions/sweeper/tasks),
  `tasks/models` + `transitions.py` + `serializers/tasks.py`,
  `config/urls.py` (audit app route include) — all additive.
- Drift guards updated by the sole editor of each: authorization
  matrix (to_be_audited claim now role=auditor, verdict probe on the
  real route with a seeded attempt-1 resolution, deferred audit
  entries retired), rate-limiting rows (`audit-verdict`,
  `audit-reports` present), task-model field/constraint sets.
- Bridge: no catalog entries yet (WP-3.5 adds them) — follow-up for
  that WP: forward `role` in the claim body when `role=auditor` work
  lands in the bridge tool.

### Final battery (this WP)

- `ruff check` / `ruff format --check` on owned files: clean.
- `mypy`: clean for owned files (two attachments-owned errors were
  outstanding elsewhere at battery time).
- `manage.py check`: 0 issues. `makemigrations --check`: no changes.
- Targeted pytest: WP-3.3's five suites + WP-3.2's three → 95 passed.
- Full suite: 1323 passed, 20 skipped; 3 pre-existing errors in
  `test_rate_limits_tunnel.py` (an `<!-- pragma: allowlist secret -->`
  HTML comment inside the `rate-limits.md` JSON fence breaks
  `json.loads`; committed at a667e92, untouched by this WP).
- OpenAPI: one regeneration, byte-stable across two runs (SHA256
  `EFBE6D89…F4197B5`); backend contract tests 6/6 and bridge contract
  13/13 green against the final document.
- **Convergence gate:** the 3 `test_rate_limits_tunnel.py` errors were
  fixed (reworded the `rate-limits.md` §6 JSON line that detect-secrets
  flagged — no pragma inside the fence). The nullable-enum
  `oneOf: [PolicyDecisionEnum, NullEnum]` shape this WP's
  `AuditReport.policy_decision` produced broke the pinned Dart client
  generator (missing enum import), so a SPECTACULAR postprocessing hook
  (`apps/core/schema_hooks.py`) flattens it to `nullable + allOf`; schema
  re-regenerated byte-stable ×2 (new SHA256 `5C57C958…0AEA6`), web +
  mobile clients regenerated, both contract suites re-verified 13/13 +
  6/6, backend mypy clean.
