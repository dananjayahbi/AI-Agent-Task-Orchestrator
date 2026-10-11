# ADR-010 — Canonical snake_case state values separate from display labels

| Field | Value |
|---|---|
| Status | accepted |
| Decision date | 2026-10-11 |
| Parent plan | Section 23 — ADR-010 |
| Session notes | [`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md) (WP-0.4 / MT-0.4-01) |

## Context

Gap G-01 found inconsistent state names in the source specification (`In progress` vs
`In Progress`, `Review` vs `In human Review`). The domain model, state machine,
events, tool responses and all three clients must agree on exact values
(Sections 4, 7, 8).

## Decision

Canonical snake_case state values separate from display labels.

## Rationale

Removes spelling drift (G-01).

## Alternatives considered

* Using display strings everywhere.

## Consequences

* The canonical machine values are `draft`, `pending`, `in_progress`,
  `to_be_audited`, `in_human_review`, `completed`; display labels are presentation
  only (Section 4, G-01; Section 7 `state` field).
* API payloads, transition history, filters, events and tool responses compare
  machine values only; M1 micro-tasks cite ADR-010 for the frozen catalog (with
  Sections 8.2/8.4).
* Display labels can change freely without breaking contracts or persisted history.

## Amendments

None — MT-0.4-01 (2026-10-11) flagged no conflict with Section 23.
