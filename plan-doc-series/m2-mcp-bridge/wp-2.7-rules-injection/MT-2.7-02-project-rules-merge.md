# MT-2.7-02 — Implement project-specific rules merging from system_prompt_rules

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.7-02 |
| Title | Implement project-specific rules merging from system_prompt_rules |
| Parent WP | WP-2.7 — Rules injection (Milestone M2) |
| Requirements | FR-MCP-05 |
| Priority | M |
| Dependencies | MT-2.7-01 (templates and render function), MT-2.4-06 (project context cache carrying rules) |
| Parent sections | 10.3 (step 5), 10.6, 19 (WP-2.7), 20.4, 20.5 |

## Context
Section 10.6 states plainly: "Project-specific rules from `system_prompt_rules` are
appended." Gap G-08 confirms a project-level rules field feeds all three delivery
channels. The backend stores `system_prompt_rules` on the project (WP-1.3); the
bridge receives it in the cached project context (Section 10.3 step 5) and must append
it — after the standard rules — consistently everywhere the rules block is rendered:
initialize instructions, `claim_task` responses, and `get_project_context`.

## Inputs / Prerequisites
* Parent plan Section 10.6 — appending rule for `system_prompt_rules`.
* Parent plan Section 10.3 step 5 — cached project context includes rules.
* Parent plan gap G-08 — one project-level rules field feeding all channels.
* MT-2.7-01 — the shared render function this merge extends.
* WP-1.3 — backend project registry supplying `system_prompt_rules` (via the API
  client from WP-2.3).

## Scope (in)
* Merge logic in the shared render path: standard (or auditor) template first, then
  the project's `system_prompt_rules` appended as a clearly delineated section —
  exactly the Section 10.6 ordering.
* Robust handling of absent/empty `system_prompt_rules`: render standard rules alone
  with no empty section header, no crash.
* Normalization limits: preserve the owner's wording (it is their policy text); apply
  only minimal safe handling (strip control characters, cap length at a documented
  default per Section 9.10) — never interpret or rewrite the content.
* Consistency guarantee: the same merged output is produced for the claim response,
  initialize instructions, and `get_project_context` (one code path, asserted by
  tests).
* Unit tests: merged output ordering, empty/missing field, rules present in cached
  context refresh after an Owner edit (fetch-on-refresh behavior of the cache),
  and a no-duplication test (project rules never rendered twice).

## Out of scope
* Editing project rules — web project settings (WP-4.2, FR-WEB-09).
* Backend storage/validation of `system_prompt_rules` — WP-1.3.
* Delivering the merged text over the three channels — MT-2.7-03.
* Auditor-vs-coder template selection — MT-2.7-01.
* Invalidation of an already-open session's cached rules — see risk notes; do not
  invent a push mechanism.

## Target paths
* `bridge/src/` (rules render/merge module)
* `bridge/tests/` (merge tests)
* WP changelog entry

## Acceptance criteria
- [ ] Merged rules always show standard/auditor rules first and the project's
  `system_prompt_rules` appended, per Section 10.6 — asserted by ordering test.
- [ ] Missing or empty `system_prompt_rules` renders standard rules cleanly with no
  empty section artifacts.
- [ ] The owner's wording is preserved verbatim apart from documented safety
  normalization; no rules are paraphrased by the bridge (Section 20.5).
- [ ] Claim response, initialize instructions and `get_project_context` produce
  identical merged output from the single render path (G-08 consistency).
- [ ] Tests pass in CI; no secrets introduced (Section 20.4 items 2, 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the merge tests, e.g. `uv run pytest bridge/tests/ -k rules_merge`; assert
ordering, empty-field behavior, single-render consistency across the three channel
callers, and verbatim project-rules preservation.

## Attachments
* [Section 10.6 — Rules block](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Gap G-08 — Rules delivery channels](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Project rules are owner-authored free text injected into agent context — keep the
  documented length cap and control-character stripping, and never execute or
  interpolate it as anything but text.
* Sessions opened before an Owner edits rules keep the old text until refresh; the
  plan specifies no live invalidation — document this and raise an OQ-xx if
  prompt propagation becomes a requirement.
