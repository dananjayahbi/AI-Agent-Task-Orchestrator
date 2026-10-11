# Architecture Decision Records

This directory holds the accepted architecture decision records for the AI Agent Task
Orchestrator. The parent plan
[`../../ai_agent_task_orchestrator_architecture_plan.md`](../../ai_agent_task_orchestrator_architecture_plan.md)
— the repository-root file — remains the single source of
truth (Section 0); these records mirror Section 23 so downstream micro-documents can
cite a stable ADR file. Any wording difference that changes meaning must be reconciled
with the plan, never left to diverge.

## Record template (context / decision / consequences)

Every record uses this shape:

| Section | Content |
|---|---|
| Front matter table | `Status` (accepted / superseded / deprecated), `Decision date`, `Parent plan` (Section 23 row), `Session notes` link |
| Context | The situation that forced the decision, grounded in plan sections |
| Decision | The Section 23 decision sentence, verbatim in substance |
| Rationale | The Section 23 rationale, verbatim in substance |
| Alternatives considered | The Section 23 alternatives, verbatim in substance (no invented alternatives) |
| Consequences | Practical implications derived from the decision and cited plan sections |
| Amendments | Explicit amendment notes only — silent rewrites are forbidden (MT-0.4-01 / Appendix C item 1) |

## Index

Status legend: `accepted` = recorded as an accepted decision (WP-0.4); `pending` =
skeleton entry not yet written; `superseded` / `deprecated` = replaced by a later ADR.

| ID | Title | File | Status | Decision date |
|---|---|---|---|---|
| ADR-001 | Single monorepo for all packages | [ADR-001-single-monorepo.md](ADR-001-single-monorepo.md) | accepted | 2026-10-11 |
| ADR-002 | SSE as the primary realtime channel | [ADR-002-sse-primary-realtime-channel.md](ADR-002-sse-primary-realtime-channel.md) | accepted | 2026-10-11 |
| ADR-003 | Celery (worker and beat) on Redis for background jobs | [ADR-003-celery-on-redis-background-jobs.md](ADR-003-celery-on-redis-background-jobs.md) | accepted | 2026-10-11 |
| ADR-004 | Agent tokens scoped to exactly one project at the backend | [ADR-004-project-scoped-agent-tokens.md](ADR-004-project-scoped-agent-tokens.md) | accepted | 2026-10-11 |
| ADR-005 | DRF with generated OpenAPI as the contract | [ADR-005-drf-openapi-contract.md](ADR-005-drf-openapi-contract.md) | accepted | 2026-10-11 |
| ADR-006 | Layered mobile auth: edge policy, device-bound token, biometric unlock | [ADR-006-layered-mobile-auth.md](ADR-006-layered-mobile-auth.md) | accepted | 2026-10-11 |
| ADR-007 | Backend never accesses repositories; evidence uploaded by host-side components | [ADR-007-backend-never-accesses-repositories.md](ADR-007-backend-never-accesses-repositories.md) | accepted | 2026-10-11 |
| ADR-008 | Merge performed by a host-side Merge Executor; `completed` only after successful merge | [ADR-008-host-side-merge-executor.md](ADR-008-host-side-merge-executor.md) | accepted | 2026-10-11 |
| ADR-009 | Deterministic Policy Engine decides escalation from stored evidence | [ADR-009-deterministic-policy-engine.md](ADR-009-deterministic-policy-engine.md) | accepted | 2026-10-11 |
| ADR-010 | Canonical snake_case state values separate from display labels | [ADR-010-canonical-snake-case-states.md](ADR-010-canonical-snake-case-states.md) | accepted | 2026-10-11 |
| ADR-011 | Tool-only contract; prompts and injected rules are enhancements | [ADR-011-tool-only-contract.md](ADR-011-tool-only-contract.md) | accepted | 2026-10-11 |
| ADR-012 | Idempotency keys plus lease fencing on all agent mutations | [ADR-012-idempotency-and-lease-fencing.md](ADR-012-idempotency-and-lease-fencing.md) | accepted | 2026-10-11 |
| ADR-013 | Optional per-task Git worktrees; default one concurrent task per project | [ADR-013-optional-per-task-worktrees.md](ADR-013-optional-per-task-worktrees.md) | accepted | 2026-10-11 |

No `pending` entries remain: all thirteen records (Section 23, ADR-001..ADR-013) were
written and accepted by MT-0.4-02 on 2026-10-11, using the decision date from the
WP-0.4 review session recorded in
[`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md)
(MT-0.4-01). That session flagged **no amendments** — none of the recorded outcomes
contradicts Section 23.

## Conventions

* One decision, one file; file names are `ADR-{three-digit id}-{kebab-title}.md`.
* IDs are never reused (parent plan Section 0.2). New decisions get new IDs; future
  ADRs beyond ADR-013 are out of scope for WP-0.4.
* Status changes (e.g. superseded) require an explicit amendment note in the record
  and a reconciliation against the parent plan.
