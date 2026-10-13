# WP-3.4 — Policy Engine (deterministic R1–R9)

## Unreleased

### Done — MT-3.4-01 … 07 (all seven, in order)

- **MT-3.4-01 evaluator framework.** `apps/audit/policy/` — a pure,
  deterministic evaluator (ADR-009): `context.PolicyContext` carries
  exactly the Section 9.4 inputs (Task scope, Project Policy fields,
  Resolution's authoritative changed-files/stats + stored-patch added
  lines, Audit Report evidence/confidence/verdict) as frozen data;
  `engine.RuleRegistry` reserves slots **R1…R9** in Section 9.4 table
  order and validates each rule's escalation reason against the
  Section 8.4 catalog at registration; `engine.evaluate` runs **every**
  registered rule (no short-circuit — MT-3.4-06 persists each
  outcome), returns `approve` only when all pass (else `escalate`, the
  plan's exact verbs), stamps `ENGINE_VERSION = "1.0.0"` on every
  result, and derives the deterministic primary reason = first failing
  rule in R1→R9 order (MT-3.4-07's `review_reason` mapping). The
  table-driven harness (`tests/wp34_helpers.PolicyCase` +
  `run_policy_table`) is exercised by every rule suite — Wave 7's
  exit criterion ("each rule pass/fail **and combinations**").
- **MT-3.4-02 R1 + R2.** R1 fails on any evidence command with a
  non-zero exit code, an unprovable exit code, or no evidence at all
  (§9.4 verbatim — `test_failure`); R2 recomputes scope from the
  authoritative changed-file list through the **shared** MT-3.2-04
  matcher (`evaluate_scope` — one matcher, never two) —
  `scope_violation`. Both pure over the context; no text parsing of
  auditor/coder prose anywhere.
- **MT-3.4-03 R3/R4/R5.** Glob rules against the §7.2 policy lists
  (`critical_path_changed`, `migration_detected`,
  `sensitive_config_changed`) via the shared `glob_matches`; R5 adds
  the added-line scan of the **stored patch** (Section 12.1
  secrets-in-diffs mitigation) with `SECRET_PATTERNS` — the backend
  mirror of the bridge helper's `secret_patterns.toml` (ids, severities
  and regexes asserted equal in `test_policy_rules_r3_r4_r5.py`: one
  conceptual list; additions are reviewed data edits on both sides).
- **MT-3.4-04 R6/R7.** R6 fails on insertions+deletions *greater
  than* `autonomous_diff_threshold_lines` (equal passes — §9.4's
  strict wording) from MT-3.2-03's authoritative stats;
  `diff_over_threshold`. R7 fails when the stored confidence is *below*
  `auditor_min_confidence` (equal passes) — `low_confidence`.
  Boundary and policy-variance (custom threshold/minimum) table cases.
- **MT-3.4-05 R8/R9.** R8 fails iff `proposed_verdict != "pass"` —
  `auditor_flagged`; R9 fails iff `auto_complete_enabled` is false —
  `policy_forced_review`, decided **only** by the persisted policy
  flag (model text cannot override — asserted).
- **MT-3.4-06 persistence.** `AuditReport` gains
  `policy_engine_version` (§9.4 "the version is stored on each Audit
  Report"; MT-3.3-04 predated it — migration `audit.0002`) plus two
  pairing CheckConstraints (no decision without results/version).
  `policy.persist.persist_evaluation` is the **only** writer: the T13
  and T14 side effects call it inside the dispatch transaction, so
  decision + all-nine rule results + version land atomically with the
  transition (or not at all — asserted by the rollback test). The
  engine-only guard: `AuditReportQuerySet` refuses
  `update()`/`bulk_update()` on the three columns and `save()` refuses
  changing them on existing rows outside the engine's one-shot write
  (`PolicyFieldsImmutable`); the strict §10.5 input serializer already
  refuses them at the API boundary. The listing/201 payloads return
  the persisted results **and** version intact (review panel §13.2).
- **MT-3.4-07 T13/T14/T10 integration.** `policy.adapter` assembles
  contexts from persisted rows (storage read for the patch body lives
  here, never in the rules); `policy.wiring.ensure_policy_engine_wired`
  installs the engine on **both** seams — the audit seam
  (`set_audit_decision_hook`) and MT-3.2-05's T10 seam
  (`set_policy_decision_hook`) — from `AuditConfig.ready()` (the
  events-app hook precedent; registry rows stay lazily wired). T13
  fires only on engine approval (merge-pending, `audit.passed`,
  audit lease concluded); T14 on any failure with the verbatim §8.4
  reason, `audit.escalated` + the §9.8 push; the verdict endpoint and
  T10 consult the same pure evaluator, so service choice and row
  re-check agree by construction (invariant 8.3.4 made structural).
  Parametrized endpoint tests drive **each of R1–R9 failing alone**
  to `in_human_review` with its exact reason, plus combined failures
  (primary = first failing rule in R1→R9 order) and the T13 approve.

### Decisions / recorded readings (Section 20.1 item 5)

- **Primary reason ordering** (MT-3.4-07 risk note): the Task's single
  `review_reason` is the **first failing rule in Section 9.4 table
  order R1→R9**; every failing reason is persisted in
  `policy_rule_results` for the review panel.
- **`policy_rule_results` shape**: a JSON **list of nine** rows
  `{"rule": "R1"…, "passed": bool, "review_reason": §8.4 member|null}`
  in R1→R9 order — the shape MT-3.3-04's test already documented;
  the engine version rides its own column so the JSON shape can evolve
  against a stamped history (MT-3.4-06 risk note).
- **Absence conventions** (MT-3.4-01/04/05 risk notes): missing
  evidence (``None``/empty/unprovable exit codes) fails R1 closed;
  `added_lines=None` (§9.7 oversize body, or a resolution without a
  stored artifact) fails R5(b) closed — never a vacuous pass;
  unprovable diff stats fail R6 closed (the real path always populates
  them — MT-3.2-03 parses before the body-drop);
  absent auditor inputs (`confidence`/`proposed_verdict` = `None` on
  the T10 path) make R7/R8 **not applicable** — they pass, by explicit
  convention, never by silently defaulting a value.
- **R1 "test command" reading**: every §10.5 `evidence.commands[]`
  entry counts (the shape has no per-command type discriminator).
- **Unparseable stored globs** (hand-edited rows predating WP-3.1
  validation) fail R3/R4/R5 closed (escalate); R2's shared matcher
  already fails such projects closed at the scope layer.
- **Fail-closed ambient stays**: fixtures that assert the pre-engine
  fail-closed defaults now pin both seams to `None` *before* the test
  as well as after (wp32/wp33 helpers) — `AuditConfig.ready()` runs
  once per process, so an ambient engine must never leak into those
  suites.

### Open questions raised (risk notes demanded an answer, not silence)

- **OQ-WP3.4-1 (T10 evidence gap).** §8.5 says the coder's submission
  "includes evidence", but §10.5's `submit_task_resolution` carries no
  evidence field and §7.2's Task Resolution has no column. Until a
  structured carrier lands, R1 fails closed on the T10 path
  (`test_failure`) and **T10's approve branch is structurally gated** —
  proven reachable in `test_policy_transitions.py` through an
  engine-derived approval over an evidence-bearing context, but not
  end-to-end through the adapter. No unplanned column invented
  (MT-3.4-06 risk note).
- **OQ-WP3.4-2 (T10 persistence target).** The coder path has no §7.2
  row to persist rule results onto (no Audit Report exists); the T10
  decision records only the enumerated `review_reason` on the
  transition. MT-3.4-06's risk note says raise the question rather
  than invent an entity — raised here.
- **OQ-WP3.4-3 (§7.2 field purity).** `policy_engine_version` extends
  the §7.2 column list by one field; §9.4 mandates version-per-report
  and MT-3.4-06 explicitly directs the addition — the field-set test
  documents the twelve-field set.

### Cross-WP touchpoints (coordinated, minimal)

- `tasks/state_machine/transitions_submission.py` **unchanged** — the
  T10 seam's WP-3.2 contract (signature + fail-closed default) is
  consumed as written; only its hook slot is now filled at startup.
- `tests/wp32_helpers.py` + `tests/wp33_helpers.py`: restore fixtures
  pin both decision seams fail-closed at test **start** (ambient-engine
  determinism; see Decisions).
- `tests/test_audit_report.py`: field-set grows the §9.4 version
  column; the engine-write test now asserts the
  `PolicyFieldsImmutable` guard + `persist_evaluation` path.
- `tests/test_authorization_matrix.py`: **unchanged** — the real-route
  verdict probe stays `in_human_review` under both ambient states
  (fail-closed seam default, or the engine's R5 fail-closed on the
  artifact-less seed row).
- OpenAPI: one regeneration, byte-stable ×2 (SHA256
  `4026FFCA…999229`); additive only (`policy_engine_version` on
  `AuditReport`). Bridge contract 13/13 green; the endpoint catalog's
  stale-flag rule has nothing to retire (no audit entries yet —
  WP-3.5 adds them). **Follow-up for WP-4.6 (web):** regenerate the
  typed client (`npm --prefix web run generate:api`) from the new
  snapshot.
- Push/event: no new catalog entries — T13/T14 keep §9.6's
  `audit.passed`/`audit.escalated` and the dispatcher's §9.8
  `in_human_review` push rule (Section 20.4 items 5–6).

### Final battery (this WP)

- `ruff check` / `ruff format --check` on owned files: clean.
- `mypy`: clean for owned files.
- `manage.py check`: 0 issues. `makemigrations --check`: no changes.
- Table-driven suites (`policy_evaluator`, `policy_rules_r1_r2`,
  `policy_rules_r3_r4_r5`, `policy_rules_r6_r7`, `policy_rules_r8_r9`)
  25 passed; `policy_persistence` 9 passed; `policy_transitions` 16
  passed.
- WP-3.3 suites (report/verdict/lease/role-gating/independence): 56
  passed. WP-3.2 suites (submission transitions/resolution/patch
  artifacts/patch parsing/scope): 65 passed. Authorization matrix +
  transition matrix + state-machine framework: 101 passed. Contract +
  route/rate-limit drift guards: 55 passed. Bridge contract: 13/13.

### Convergence gate (2026-10-14)

- Re-verified: OpenAPI regen byte-stable ×2 at SHA-256 `4026FFCA…` (sole authoritative regen), bridge contract 13/13, web + mobile clients regenerated against it (sole delta `policy_engine_version`); full backend suite **1388 passed, 26 skipped**.
