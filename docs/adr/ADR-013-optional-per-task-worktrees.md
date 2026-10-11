# ADR-013 — Optional per-task Git worktrees; default one concurrent task per project

| Field | Value |
|---|---|
| Status | accepted |
| Decision date | 2026-10-11 |
| Parent plan | Section 23 — ADR-013 (embodies decided OQ-03) |
| Session notes | [`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md) (WP-0.4 / MT-0.4-01) |

## Context

Several agents may target one repository: a shared working tree can be corrupted
(RISK-03) and parallel tasks on overlapping files cause merge conflicts (RISK-04).
OQ-03 asked how to handle this; the review session decided the recommended default on
2026-10-11.

## Decision

Optional per-task Git worktrees; default one concurrent task per project.

## Rationale

Avoids same-repo collisions without forcing complexity.

## Alternatives considered

* Always worktrees.
* Unrestricted concurrency.

## Consequences

* The default `max_concurrent_tasks` of 1 per project protects the shared working
  tree out of the box (RISK-03 mitigation).
* Per-task worktrees are an available, later improvement — opt-in complexity rather
  than a prerequisite (OQ-03 recommended default, decided 2026-10-11).
* Always-worktrees and unrestricted concurrency are excluded as defaults.

## Amendments

None — MT-0.4-01 (2026-10-11) flagged no conflict with Section 23.
