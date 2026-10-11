# MT-2.1-01 — Create the Bridge Package Layout

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.1-01 |
| Title | Create the bridge package layout |
| Parent WP | WP-2.1 — Bridge package skeleton (Milestone M2) |
| Requirements | FR-MCP-01 (single MCP server entry) |
| Priority | M |
| Dependencies | MT-0.1-01 (repo groundwork), MT-0.1-02 (Python tooling — ruff/pytest config) |
| Parent sections | 10.1 (responsibilities), 10.2 (run modes), 23 (ADR-004, ADR-008), 19.1 (WP-2.1 first slice), Appendix A (repo layout), 20.3, 20.4, 20.5 |

## Context
WP-2.1's first slice is "package layout." The plan fixes both the language and the
location: the bridge is Python (ADR-004: "agent bridge is Python"), and Appendix A
gives its home as `bridge/` — a separate top-level package alongside `backend/`,
`web/` and `agent-guides/`, with its own `pyproject.toml` so tooling stays per-package
(Section 19.7: test only what a change affects). Section 10.1 defines what the package
will eventually contain — transport, manifest resolution, capability resolution,
credential loading, resume-context cache, tool implementations — so the layout must
reserve those seams now, even though WP-2.1 delivers only a skeleton (empty tool set
per WP-2.1 acceptance). ADR-008 (independent-versioned deployables) means the bridge
must not import from `backend/` — a hard architectural boundary this layout enforces.

## Inputs / Prerequisites
* MT-0.1-01 — repository structure and conventions from Foundations.
* MT-0.1-02 — Python tooling (uv, ruff, pytest) already configured for `backend/`;
  the bridge mirrors that configuration pattern with its own config files.
* Parent plan Section 10.1 — the component responsibilities the layout must
  accommodate (implement in later MTs; this task only carves the structure).
* Parent plan Appendix A — `bridge/` and its placeholder files in the repo tree.
* Parent plan Section 10.2 — run modes (stdio / streamable HTTP / executor-embedded)
  that will need distinct entry points under the package.

## Scope (in)
* Create the `bridge/` top-level package directory with a `pyproject.toml` declaring
  the package (name, Python version per plan, uv-compatible), its own ruff/pytest
  configuration mirroring the MT-0.1-02 conventions, and an `src`-style or flat layout
  consistent with what Appendix A shows.
* Seed the module seams Section 10.1 names, as empty/placeholder modules with
  docstrings only (no logic): transport/entry points, config (env + user-level file),
  manifest resolution, capability resolution, credentials, resume-context cache, and
  tools registry — later MTs (MT-2.1-02 … 04, WP-2.2, WP-2.4) fill them in.
* An empty tools registry so the package satisfies WP-2.1's acceptance ("empty tool
  set" under the MCP inspector) once the entry point exists (MT-2.1-04).
* Cross-package boundary guard: no imports from `backend/` or `web/` anywhere in
  `bridge/` — assert it with a simple test or lint rule so ADR-008's independence
  cannot regress silently.
* Verify tooling runs from the package root (`uv`-driven ruff and pytest, matching
  MT-0.1-02's command style); changelog note (Section 20.4 item 7).

## Out of scope
* Config loading behavior — MT-2.1-02; structured logging — MT-2.1-03; entry points —
  MT-2.1-04.
* Manifest discovery/validation, token loading, session handling — WP-2.2.
* Actual tool implementations (`list_projects`, `create_task`, …) — WP-2.4 onward.
* Packaging/distribution to PyPI or a container — Section 10.11 packaging is a later
  WP (the plan's packaging decision points there; do not publish anything here).
* Any code in `backend/`, `web/` or `agent-guides/` — only create `bridge/` files.

## Target paths
* `bridge/pyproject.toml`, ruff/pytest config files (per Appendix A layout)
* `bridge/` module tree — placeholder modules for the Section 10.1 responsibilities
* `bridge/tests/` — the boundary test (no backend/web imports) and a smoke import
* WP changelog entry

## Acceptance criteria
- [ ] `bridge/` exists as an independently configurable Python package (own
  `pyproject.toml`, tooling runs from its root) — Appendix A; ADR-004 (Python bridge);
  ADR-008 (independent deployables).
- [ ] Module seams match Section 10.1's responsibility list, each with a docstring
  pointing at its plan section; no business logic in the skeleton (Section 19.1 first
  slice: layout only).
- [ ] Boundary test proves no `bridge/` module imports `backend/` or `web/`
  (ADR-008).
- [ ] Empty tools registry present, ready for MT-2.1-04's inspector check
  (WP-2.1 acceptance).
- [ ] `uv run --directory bridge ruff check .` and `uv run --directory bridge pytest -q`
  pass (Section 20.4 items 1–2: test command proof, CI green).
- [ ] No secrets or environment-specific paths committed (item 3); changelog note
  added (item 7).

## Test command
`uv run --directory bridge ruff check .` and `uv run --directory bridge pytest -q` —
smoke import of the package, boundary (no-backend-import) test, empty registry
present; the WP-2.1 inspector acceptance runs in MT-2.1-04.

## Attachments
* [Section 10.1 — Bridge responsibilities](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Appendix A — Repository layout](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-004 / ADR-008 — Stack and deployable independence](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Over-scaffolding is the temptation: placeholders must stay logic-free or later MTs
  inherit premature interfaces the plan has not fixed (Section 10.4 capability
  negotiation and Section 10.3 manifest shape are specified later — do not
  pre-implement them).
* `uv` workspace versus standalone package: the plan says `bridge/` has its own
  `pyproject.toml` (Appendix A) and does not mandate a workspace — choose
  standalone unless a workspace already exists at the repo root, and record the
  choice in the changelog.
* Appendix A's `bridge/` tree may show placeholder filenames that differ slightly
  from the Section 10.1 responsibility split — follow Appendix A for paths, Section
  10.1 for responsibilities, and note any mismatch as a plan inconsistency (new OQ
  `OQ-15+`) rather than renaming repo files the plan lists.
