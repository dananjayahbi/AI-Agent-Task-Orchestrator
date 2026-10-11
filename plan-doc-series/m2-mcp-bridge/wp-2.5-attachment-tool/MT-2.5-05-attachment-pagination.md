# MT-2.5-05 — Implement attachment pagination parameters

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.5-05 |
| Title | Implement attachment pagination parameters |
| Parent WP | WP-2.5 — Tool: `read_task_attachment` with capability negotiation (Milestone M2) |
| Requirements | FR-ATT-04 |
| Priority | M |
| Dependencies | MT-2.5-03, MT-2.5-04 (packaging branches that emit pages), WP-1.14 (content endpoint paging), WP-0.5 (pagination conventions) |
| Parent sections | 9.5, 10.5, 19 (WP-2.5), 20.4, 20.5 |

## Context
Section 9.5: "Large documents return one page or chunk per call with `page_number`,
`total_pages`, and a token count so the agent can budget context." The tool catalog
(Section 10.5) lists `page_number` among `read_task_attachment`'s key inputs, and
`auto` routes documents to "markdown, paginated". FR-ATT-04 requires on-demand
retrieval in all four formats with pagination. This task adds the paging parameters
and response fields so agents never swallow an entire document into context at once.

## Inputs / Prerequisites
* Parent plan Section 9.5 — paging contract (`page_number`, `total_pages`, token
  count) and the `markdown`/`auto` document rows.
* Parent plan Section 10.5 — `page_number` input on `read_task_attachment`.
* WP-0.5 pagination conventions document (MT-0.5-04) — shared paging rules the tool
  follows rather than inventing its own.
* WP-1.14 — backend `GET /attachments/{id}/content?format=&page=` the tool wraps.
* `VALIDATION_ERROR` from the Section 9.2 catalog for out-of-range pages.

## Scope (in)
* `page_number` input handling on `read_task_attachment` (default first page),
  forwarded to the backend content endpoint per WP-0.5 pagination conventions.
* Response fields `page_number`, `total_pages` and the token count for the returned
  page, on every paginated document read (`auto` document row, `markdown`).
* Out-of-range or non-integer `page_number` → `VALIDATION_ERROR` with hint and next
  action (Section 10.5 tool rules).
* Consistency between tool-level and endpoint-level paging: same page size and
  numbering semantics as WP-1.14's endpoint (one source of truth — WP-0.5
  conventions).
* Unit tests: default first page; middle page; last page (`page_number` ==
  `total_pages`); out-of-range rejected; token count present; image/text paths
  unaffected by paging.

## Out of scope
* Packaging branches themselves — MT-2.5-03/04.
* Backend page computation and chunking — WP-1.14, WP-1.12.
* Cursor-based pagination for list endpoints (tasks, checkpoints) — WP-0.5/endpoint
  owners; this task is document pages only.
* Retry/resume behavior across pages — caller-driven by design.

## Target paths
* `bridge/` — attachment tool input schema and response assembly (paging fields)
* `bridge/tests/` — pagination tests
* WP changelog entry

## Acceptance criteria
- [ ] `page_number` is an accepted input on `read_task_attachment` (Section 10.5) and
  defaults to the first page.
- [ ] Every paginated document read returns `page_number`, `total_pages` and a token
  count for the returned page (Section 9.5, FR-ATT-04).
- [ ] Out-of-range pages return `VALIDATION_ERROR` with a hint and next action, using
  only catalog codes (Section 20.4 item 5).
- [ ] Tool and backend endpoint agree on page numbering and size (WP-0.5 pagination
  conventions; no divergent second definition).
- [ ] Image and OCR text paths behave unchanged with paging arguments supplied
  (no-op, not an error).
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`uv run pytest bridge/tests/ -k attachment_pagination -q` — assert default/middle/
last page responses carry `page_number`, `total_pages` and token count, out-of-range
yields `VALIDATION_ERROR`, and image/OCR paths ignore paging; then the full bridge
suite stays green.

## Attachments
* [Section 9.5 — Attachment processing (retrieval behavior)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Tool catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Page-size mismatch between the bridge and the backend would corrupt `total_pages`
  — both sides must follow the WP-0.5 pagination conventions; test against the real
  endpoint (WP-1.14), not a mock that re-derives sizes.
* Token counts are estimates (Section 9.5 says "estimate tokens" for documents); do
  not present them as exact budgets in tool copy.
* If WP-1.14 lands after this task, land against the contract with an integration
  test gated on WP-1.14 rather than inventing a temporary paging scheme.
