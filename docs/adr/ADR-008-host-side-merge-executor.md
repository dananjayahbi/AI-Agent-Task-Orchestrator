# ADR-008 — Merge performed by a host-side Merge Executor; `completed` only after successful merge

| Field | Value |
|---|---|
| Status | accepted |
| Decision date | 2026-10-11 |
| Parent plan | Section 23 — ADR-008 (merge-strategy context for decided OQ-06) |
| Session notes | [`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md) (WP-0.4 / MT-0.4-01) |

## Context

"Completed = merged" is a core invariant of the task lifecycle (Section 8), but the
backend never accesses repositories (ADR-007), so the merge itself must run on the
host. The `merge` app exposes a merge queue API consumed by the host-side Merge
Executor (Sections 6.3, 9.1).

## Decision

Merge performed by a host-side Merge Executor; `completed` only after successful
merge.

## Rationale

Keeps "Completed = merged" invariant honest.

## Alternatives considered

* Backend merges.
* Agent merges.
* Mark complete on approval.

## Consequences

* A passing audit moves the task to merge-pending but it stays `to_be_audited` until
  the executor reports a successful merge (Section 8.2, T13); merge outcomes emit
  `merge.started|succeeded|failed` events (Section 9.6).
* The Executor runs in a dedicated worktree on the host and reports results to the
  backend (Section 6.3).
* **OQ-06 context (decided 2026-10-11):** projects without a local merge step set
  `merge_strategy` to `manual`, where approval marks `completed` without executor
  involvement — the recorded exception path for ADR-008's invariant, not a rewrite of
  it.
* Backend merging, agent merging, and mark-complete-on-approval are excluded as the
  default flow.

## Amendments

None — MT-0.4-01 (2026-10-11) flagged no conflict with Section 23; the OQ-06 note
above is context recorded with the decision, not a change to its substance.
