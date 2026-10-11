# Plan documents

This directory holds planning documentation that lives with the repository.

| Document | Description |
|---|---|
| [Architecture & Implementation Plan](../../ai_agent_task_orchestrator_architecture_plan.md) | The single source of truth: requirements, design, milestones, ADR summary. Intentionally stays at the repository root. |
| [Micro-document series overview](../../plan-doc-series/overview.md) | Master index of the micro-document series — one micro-document per task-sized slice of the plan. |
| [Micro-document roadmap](../../plan-doc-series/roadmap.md) | Wave-ordered execution plan for the series (a wave may only depend on earlier waves). |
| [M0 decision review notes](m0-decision-review-notes.md) | Outcomes of the WP-0.4 decision review session (MT-0.4-01). |
| [Configuration conventions](conventions/configuration.md) | Environment variable naming, grouping and secret handling — WP-0.5 (MT-0.5-01), from parent plan Sections 9.10/16.2. |
| [Error conventions](conventions/error-envelope.md) | Canonical error envelope and the 19-code catalog — WP-0.5 (MT-0.5-02), from parent plan Section 9.2. |
| [Header conventions](conventions/headers.md) | Correlation id and idempotency key headers — WP-0.5 (MT-0.5-03), from parent plan Sections 9.2/9.6/17. |
| [Pagination conventions](conventions/pagination.md) | Cursor-based pagination for all list endpoints, plus the Section 9.5 attachment `content` exception — WP-0.5 (MT-0.5-04). |

Notes:

- Micro-documents live in one folder per work package under
  `plan-doc-series/{milestone-folder}/wp-{number}-{title}/`.
- Each work package folder keeps a changelog for short completion notes (parent plan
  Section 20.4, item 7); see
  [WP-0.1's changelog](../../plan-doc-series/m0-foundations/wp-0.1-monorepo-scaffolding/CHANGELOG.md)
  as the first example.
- The shared configuration and error conventions (WP-0.5) live under
  [`conventions/`](conventions/) — one document per concern: configuration,
  error envelope, headers, pagination. They are referenced from the package
  documentation of `backend/`, `bridge/`, `web/` and `mobile/`.
