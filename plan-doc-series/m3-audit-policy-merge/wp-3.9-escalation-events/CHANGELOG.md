# WP-3.9 — Escalation notifications hook (`review.requested`)

## Unreleased

### Done — MT-3.9-01 + MT-3.9-02 (payload contract + entry emission)

- **MT-3.9-01 payload contract.** The `review.requested` event uses
  the Section 9.6 envelope verbatim (`type` = `review.requested` — a
  catalog member, unchanged; `project_id`, `task_id`, `occurred_at`,
  `actor`). Its `data` carries exactly: the canonical
  `review_reason` (Section 8.4's 12-value enum — membership asserted
  per emission, none invented), `task_version` (the Section 9.8
  dedupe key `(event type, task id, state version)`), and — only
  where the Policy Engine decided — `policy_rule_results`: **WP-3.4's
  persisted shape verbatim** (the Audit Report's per-rule
  `{rule, passed, review_reason}` rows, all nine, structural
  equality asserted against the persisted column — one vocabulary,
  no parallel "escalation details" shape). The `data` key set is
  closed and asserted (no free-text evidence/secrets — Section 9.8
  minimization; Section 12.4 posture).
- **MT-3.9-02 emission — one hook on the transition itself.** The
  dispatcher emits exactly one `review.requested` event whenever a
  row's `to_state` is `in_human_review` — inside the same
  transaction as the Transition/task rows (Section 8.2 rule 2),
  published strictly post-commit (Section 9.6, WP-1.9's writer).
  Entry rows covered today: **T8** (`self_flagged` /
  `scope_violation`), **T9** (`retry_exhausted`), **T14** (the
  enumerated policy reason + the persisted rule details), and
  T10-escalation's §8.5 branch by the same rule; **T18** inherits
  the hook when WP-3.7 wires its row (MT-3.9-03's gap — see below).
  Non-entry transitions emit none; a task re-entering later emits a
  fresh event (one per entry, never one per task); the Section 9.8
  push seam stays a single downstream consumer (one trigger, one
  event — no double-writer).
- **Rule-details sourcing (recorded design).** A third hook seam in
  `apps/tasks/state_machine/hooks.py` — the default/override split
  of the WP-1.9 event hook — lets the audit app install the *reader*
  of the persisted `policy_rule_results`
  (`apps/audit/policy/wiring.review_rule_details_hook`, installed
  with the engine in `AuditConfig.ready()`). It answers for **T14
  only** (MT-3.9-02: T8/T9/T18 carry no policy rule results —
  absence is the empty mapping, never a fabricated rule set), reads
  the current-attempt report (a stale attempt's evaluation never
  rides a later escalation), and cannot lag the event: T14's side
  effect persisted the evaluation earlier in the same transaction
  (MT-3.4-06). An entry row that never set an enum reason is a
  programming error (`ValueError`, full rollback) — never a silent
  payload.
- Tests: `tests/test_review_requested_payload.py` (envelope,
  enum membership, WP-3.4 shape equality, closed key set, the hook
  seam) and `tests/test_review_requested_emission.py` (one-per-entry
  for T8/T9/T14, none for non-entry rows, re-entry freshness,
  same-transaction write, post-commit-only publication) green; the
  WP-1.5 matrix/system suites updated for the second entry event
  (their "exactly one event" assertions now assert the MT-3.9-02
  shape); full backend suite green.

### Deferred — MT-3.9-03 (reason-coverage tests)

- **Deferred with this WP's convergence note:** MT-3.9-03 drives the
  `merge_conflict` reason through **T18**, which does not exist until
  WP-3.7 wires the merge queue (the registry holds T2–T16 + T19
  today). Per the MT's own dependencies it waits; the emission hook
  is already generic over `to_state`, so T18 will flow through it
  the moment its row lands. The remaining reason values
  (`test_failure`, `migration_detected`, `sensitive_config_changed`,
  `diff_over_threshold`, `low_confidence`, `auditor_flagged`,
  `policy_forced_review`) are produced by the policy suites' own
  escalations; MT-3.9-03's exhaustive per-reason table joins them
  then.
