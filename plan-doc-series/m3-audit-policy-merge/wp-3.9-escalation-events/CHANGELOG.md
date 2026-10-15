# WP-3.9 — Escalation notifications hook (`review.requested`)

## Unreleased

### Done — MT-3.9-03 (reason-coverage tests)

- **MT-3.9-03 reason coverage complete — every Section 8.4 reason
  exercised by the transition that owns it.** The table-driven suite
  `tests/test_escalation_reasons.py` (`pytest backend/tests -k
  escalation_reasons -q`, 16 tests green) drives one row per canonical
  reason through the real machinery, never a synthetic hook call:
  **T8** (`self_flagged` in-scope self-flag, `scope_violation`
  out-of-scope submit) and **T9** (`retry_exhausted` at the ceiling)
  through the endpoints/dispatch; **T14** with each of R1–R9 failing
  alone through the real verdict endpoint with the engine installed;
  **T18** (`merge_conflict`) through WP-3.7's now-wired merge row —
  the gap this MT was deferred on is closed (the executor's
  `merge_failed` dispatch lands in `in_human_review` and flows through
  the generic entry hook exactly as MT-3.9-02 predicted).
- **Per-row contract:** exactly one `review.requested`; the Section 9.6
  envelope verbatim (catalog `type`, `project_id`, `task_id`,
  `occurred_at`, the driving `actor`); the canonical reason on the task
  and in the event data; the Section 9.8 dedupe-key `task_version`
  matching the post-transition row. T14 rows key the rule details on
  the **failed rule id** (exactly `[R*n*]` failed, that outcome's
  `review_reason` the escalation reason) — never message text, per the
  MT's risk note; T8/T9/T18 rows assert `data` is exactly
  `{review_reason, task_version}` — no fabricated rule set.
- **Coverage guard:** the suite asserts its rows cover exactly
  `ReviewReason.values` *and* an independently-written copy of the
  canonical twelve (plan-first, Section 20.5) — a future enum addition
  fails the suite until this table grows a row, so the anti-rot device
  lives in the tests, not in review checklists.
- **Negative controls:** T4 (claim), T7 (clean submit → `to_be_audited`)
  and T17 (merge completion) emit no `review.requested` while their own
  catalog events (`task.claimed`, `task.transitioned`,
  `merge.succeeded`) all fire — non-entry transitions stay quiet.
- CI: the suite runs in the existing backend unit job (Section 20.4
  item 2 — `pytest` picks up `tests/`); no pipeline change needed.
  Only Section 9.6 catalog types and Section 8.4 reasons appear
  (items 5–6).

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