# MT-2.4-06 — Implement get_project_context for cheap orientation

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.4-06 |
| Title | Implement get_project_context for cheap orientation |
| Parent WP | WP-2.4 — Tools: availability, details, claim, release, context (Milestone M2) |
| Requirements | FR-MCP-03 |
| Priority | M |
| Dependencies | MT-2.4-01 (schemas), MT-2.3-01..04 (API client), WP-2.2 (cached project context) |
| Parent sections | 10.3 (step 5 cache), 10.5, 19 (WP-2.4), 20.4, 20.5 |

## Context
Section 10.5 adds `get_project_context` as a new tool with no inputs whose purpose is
"bound project name, rules, policy summary — cheap orientation call." Section 10.3
step 5 already has the bridge cache project context (name, policy summary, rules) at
session open, so this tool should answer from the cache without a backend round trip
whenever possible — that is what makes it cheap. It is the first tool an agent calls
after connect to orient itself in the bound project (complementing the rules delivered
on initialize by WP-2.7).

## Inputs / Prerequisites
* Parent plan Section 10.5 — `get_project_context` row: no inputs; project name,
  rules, policy summary.
* Parent plan Section 10.3 step 5 — session binding caches project context (name,
  policy summary, rules); no tool accepts a project id.
* Parent plan Section 9.4 — policy concepts the summary reflects (thresholds,
  `max_concurrent_tasks`, `audit_required`, `auto_complete_enabled` as configured —
  only fields the backend returns).
* MT-2.4-01 — schema (empty input object).
* WP-2.2 — cache populated at session open; MT-2.3-01..04 — client for refresh.

## Scope (in)
* Handler for `get_project_context` reading the session's cached context and
  returning: project name and id, the effective rules (same content family as the
  Section 10.6 block, including project-specific `system_prompt_rules` once WP-2.7
  merges them), and a compact policy summary as structured fields the backend
  provided — no re-derivation of policy logic in the bridge.
* Cache-refresh behavior on staleness: if the cache is missing (for example a resumed
  session), fetch once via the client using the bound session's project, then serve
  from cache; a backend failure surfaces as a structured retryable error with hint
  and next action, not a crash.
* Compactness: the response contains no task lists, no user data, no secrets
  (Section 10.5 "cheap"; Section 12.4 data protection).
* Unit tests: cache-hit path (no network), cache-miss refresh path, backend-down
  path with structured error, and empty-input validation.

## Out of scope
* Caching implementation itself — WP-2.2 (MT-2.2-04).
* Rules merging and delivery channels — WP-2.7.
* Policy editing — web policy editor (WP-4.2, FR-WEB-09).
* Backend context/policy serialization — WP-1.x.
* The MCP prompt that also orients agents — WP-2.8.

## Target paths
* `bridge/src/` (context tool handler)
* `bridge/tests/` (handler tests)
* WP changelog entry

## Acceptance criteria
- [ ] `get_project_context` takes no inputs and returns project name, rules and
  policy summary per Section 10.5 — asserted by schema and fixture tests.
- [ ] The cache-hit path performs no backend request (cheap-orientation intent),
  proven by the unit test's mock transport.
- [ ] No `project_id` parameter; the answer is always the bound session's project
  (Section 10.3).
- [ ] Backend-down path yields a structured error with a Section 9.2 code, hint and
  next action (Section 10.5 error rule, Section 10.10).
- [ ] Tests pass in CI; only catalog codes used (Section 20.4 items 2, 5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the context tool tests, e.g. `uv run pytest bridge/tests/ -k get_project_context`;
assert cache-hit makes zero transport calls, refresh path works, and backend failure
produces a structured retryable error.

## Attachments
* [Section 10.5 — Tool catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.3 — Manifest discovery and binding](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Stale cached policy after an Owner edits policy mid-session: the plan does not
  specify invalidation for this cache — note the limitation and raise an OQ-xx if
  agents must see policy edits promptly.
* Duplicating rules content here and in WP-2.7's claim/initialize channels invites
  drift; share one source for the rules text.
