# AI Agent Task Orchestrator

A single, always-on control plane that lets one developer run many AI coding agents across many
repositories at once: one source of truth for task state, logs, and quality gates; strict
isolation between projects; safe parallelism between agents; remote observability and one-tap
approvals from a phone.

The single source of truth for architecture, requirements, and delivery is the parent plan:

- [Architecture & Implementation Plan](ai_agent_task_orchestrator_architecture_plan.md)
- [Micro-document series overview](plan-doc-series/overview.md)

## Repository layout

The layout follows Appendix A of the parent plan (ADR-001: single monorepo):

| Path | Package |
|---|---|
| `docs/` | Plan, ADRs, runbooks, agent guides — starts at [`docs/plan/`](docs/plan/) |
| `backend/` | Django control plane (Python, uv-managed) |
| `bridge/` | MCP bridge + Merge Executor (Python, uv-managed) |
| `web/` | Next.js (App Router) operations board |
| `mobile/` | Flutter mobile client |
| `schemas/` | Shared contracts (manifest schema, OpenAPI snapshot, tool schemas) |
| `infra/` | Compose, Cloudflare tunnel, and backup configuration |
| `e2e/` | Cross-stack scenario scripts |
| `plan-doc-series/` | Micro-document series (one folder per work package) |

## Documentation

The documentation tree (parent plan Appendix A):

- [Operator setup guide](docs/setup.md) — fresh-clone bring-up, configuration and
  secrets, health verification, upgrade and rollback (WP-6.5, MT-6.5-01)
- [Plan documents](docs/plan/) — index of the parent plan and micro-document series
- [Architecture decision records](docs/adr/) — ADR-001 through ADR-013
- [Runbooks](docs/runbooks/) — one stub per Section 17 runbook (content: WP-6.5)
- [Agent client guides](docs/agent-guides/) — per-client setup page stubs (content: WP-2.11)

## Per-package commands

Every package runs its lint, format check, and type check with exactly one documented command
each. The commands live in [CONTRIBUTING.md](CONTRIBUTING.md) under **Tooling commands**:

- `backend/` → see [CONTRIBUTING.md — Backend (Python)](#backend-python)
- `bridge/` → see [CONTRIBUTING.md — Bridge (Python)](#bridge-python)
- `web/` → see [CONTRIBUTING.md — Web (Next.js)](#web-nextjs)
- `mobile/` → see [CONTRIBUTING.md — Mobile (Flutter)](#mobile-flutter)
- Git hooks → see [CONTRIBUTING.md — Git hooks](#git-hooks)

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) first: it documents package boundaries (which package
owns which responsibility), the tooling commands, and the hook installation.
