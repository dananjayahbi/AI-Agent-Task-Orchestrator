# MT-0.1-06 — Create the Documentation Skeleton

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.1-06 |
| Title | Create the documentation skeleton (docs/plan, docs/adr, docs/runbooks, docs/agent-guides) |
| Parent WP | WP-0.1 — Monorepo scaffolding and tooling (Milestone M0) |
| Requirements | NFR-11 |
| Priority | S |
| Dependencies | MT-0.1-01 |
| Parent sections | 10.9, 17, 19.1 (WP-0.1), 20.4, Appendix A |

## Context
Appendix A reserves four documentation areas under `docs/`, and WP-0.1 lists
contribution notes among its deliverables. This task creates the skeleton — index files
and stubs — so later milestones have an obvious, stable home for ADRs (WP-0.4), runbooks
(Section 17), and per-client agent setup pages (Section 10.9, WP-2.11), instead of
inventing document locations ad hoc.

## Inputs / Prerequisites
* MT-0.1-01 — the `docs/` directory tree exists.
* Parent plan Section 17 — runbook list: stuck lease, failed merge, tunnel down, restore
  from backup, rotate tokens, add a project, onboard a new agent client.
* Parent plan Section 10.9 / 19 (WP-2.11) — client compatibility matrix and per-client
  guides; Section 22 OQ-05 for the first verified clients.
* Parent plan Section 23 — ADR-001..ADR-013 to be filed in `docs/adr/` by MT-0.4-02.

## Scope (in)
* Create an index/README in `docs/plan/` pointing at the parent architecture plan and
  this micro-document series.
* Create `docs/adr/` with an ADR index template listing ADR-001..ADR-013 as pending
  (files themselves are written by MT-0.4-02).
* Create `docs/runbooks/` with one stub per Section 17 runbook, each naming its owner
  milestone for content.
* Create `docs/agent-guides/` with a stub index for per-client setup pages (clients to
  be confirmed per OQ-05 in WP-0.4).
* Link the documentation tree from `CONTRIBUTING.md`/`README.md` and add a WP
  changelog note.

## Out of scope
* Writing the actual ADR records — MT-0.4-02.
* Runbook content (procedures, commands) — WP-6.4/WP-6.5.
* Agent client guides content — WP-2.11.
* The conventions document of WP-0.5 — created later under `docs/plan/`.
* Migrating the parent plan file itself — it stays at the repository root.

## Target paths
* `docs/plan/README.md` (index to plan and micro-document series)
* `docs/adr/README.md` (ADR index, ADR-001..013 listed as pending)
* `docs/runbooks/README.md` plus one stub file per Section 17 runbook
* `docs/agent-guides/README.md` (per-client guide index)
* `CONTRIBUTING.md` / `README.md` (documentation links)
* WP changelog entry

## Acceptance criteria
- [ ] All four `docs/` subdirectories exist with a README/index each.
- [ ] `docs/adr/README.md` lists ADR-001 through ADR-013 with status "pending".
- [ ] `docs/runbooks/` contains one stub for each of the seven Section 17 runbooks.
- [ ] `docs/agent-guides/` index exists and names where per-client pages will live.
- [ ] Documentation tree is reachable from the root README/CONTRIBUTING.
- [ ] No environment-specific paths in any created file (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
List the documentation tree (e.g. `Get-ChildItem -Recurse docs/`) and verify each of
the four subdirectories has a README, the ADR index names all 13 ADR IDs, and
`docs/runbooks/` contains seven runbook stubs matching the Section 17 list.

## Attachments
* [Appendix A — Proposed Repository Layout](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 17 — Observability and Operations](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.9 — Client compatibility matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* ADR status "pending" must be flipped to "accepted" by MT-0.4-02; a stale index would
  misrepresent decision state (Appendix C checklist item 1).
* The first agent clients are only confirmed when OQ-05 is decided in WP-0.4 — keep the
  guides index generic until then.
