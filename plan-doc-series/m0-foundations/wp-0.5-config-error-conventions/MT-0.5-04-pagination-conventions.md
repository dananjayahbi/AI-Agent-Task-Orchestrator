# MT-0.5-04 — Define Cursor-Based Pagination Conventions for All List Endpoints

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.5-04 |
| Title | Define cursor-based pagination conventions for all list endpoints |
| Parent WP | WP-0.5 — Configuration, secrets and error conventions (Milestone M0) |
| Requirements | NFR-11 (typed contract), NFR-09 (scale: 10,000 tasks) |
| Priority | M |
| Dependencies | MT-0.5-02 (conventions document structure) |
| Parent sections | 9.2, 7.3, 19.1 (WP-0.5), 20.4, 21 (RISK-13) |

## Context
Section 9.2 fixes pagination as cursor-based for the v1 REST surface, and the API hosts
list endpoints that must scale to 10,000 tasks and 50 GB of attachments (NFR-09) with
pagination named as a mitigation for RISK-13. WP-0.5's pagination slice writes the one
convention every list endpoint — projects, tasks, work, checkpoints, resolutions,
audit reports, attachments, events history — implements, so the OpenAPI contract
(NFR-11) and the four clients agree from the first endpoint onward.

## Inputs / Prerequisites
* Parent plan Section 9.2 — "Pagination is cursor-based"; the full list-endpoint
  inventory (projects, tasks, work, checkpoints, resolutions, audit reports,
  attachments, events, merge pending, tokens, devices).
* Parent plan Section 9.6 — event history endpoint with filters (resume via event id
  is SSE-specific, but history listing paginates).
* Parent plan Section 9.5 — attachment `content` endpoint already specifies `page`/
  `page_number`/`total_pages` behavior for document chunks — an explicit, pre-existing
  exception to cursor pagination that the convention must acknowledge.
* Parent plan Section 7.3 — identifier generation rules (IDs are stable, sortable
  anchors for cursor construction).
* MT-0.5-02 — the conventions document this section is added to.

## Scope (in)
* Publish the pagination section of the WP-0.5 conventions document defining:
  * The canonical cursor query parameter name and the canonical response envelope for
    list endpoints (results plus an opaque next-cursor value; absence of next cursor
    means the end of the list).
  * Cursor opacity rule: cursors are opaque to clients (server may encode ordering
    state); clients never construct or parse them.
  * Stable ordering rule: each list endpoint declares one deterministic sort (e.g. by
    stable ID or creation time plus ID tiebreak) so cursors never skip or duplicate
    rows.
  * Default and maximum page-size parameters with documented defaults, configurable
    where 9.10 groups allow.
* Explicitly document the Section 9.5 exception: attachment `content` retrieval is
  page-numbered (`page`, `page_number`, `total_pages`) because chunks are re-creatable
  and agents budget context — list endpoints still use cursors.
* State the OpenAPI obligation: parameters and response shape are part of the typed
  contract generated in WP-1.1 and guarded by schema diff in CI (NFR-11).
* Reference the document from backend, bridge, web and mobile package docs
  (WP-0.5 acceptance).
* Add a WP changelog note.

## Out of scope
* Implementing pagination in any endpoint — WP-1.3/1.4 onwards (first list endpoints).
* Changing the attachment `content` page scheme — it is specified in Section 9.5.
* Offset pagination anywhere — explicitly not part of the plan; do not offer it.
* Client-side paging UI/UX (infinite scroll, page controls) — WP-4.x / WP-5.x.
* Page-size numbers not stated in the plan — choose documented defaults and mark them
  as such, not as plan facts.

## Target paths
* `docs/plan/conventions/pagination.md` (pagination conventions section of the WP-0.5
  conventions document)
* `backend/`, `bridge/`, `web/`, `mobile/` package docs or configs (reference added)
* WP changelog entry

## Acceptance criteria
- [ ] One canonical query parameter and one response envelope are defined for cursor
  pagination across all list endpoints named in Section 9.2.
- [ ] Cursor opacity, stable ordering, and end-of-list semantics are specified.
- [ ] Default/maximum page sizes are documented with explicit defaults.
- [ ] The Section 9.5 attachment `content` page-numbering exception is documented so
  implementers do not "unify" it incorrectly.
- [ ] The OpenAPI obligation (typed contract, schema diff) is stated per NFR-11.
- [ ] The document is referenced from backend, bridge, web and mobile package docs
  (WP-0.5 acceptance).
- [ ] No endpoint behavior beyond Section 9.2/9.5 is invented.
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Cross-check the conventions document against the Section 9.2 endpoint table: every
list (GET collection) endpoint must be covered by the cursor rule, and the Section 9.5
attachment `content` exception must be findable in the document; grep the four package
docs for the conventions reference.

## Attachments
* [Section 9.2 — REST API surface (pagination)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.5 — Attachment processing (page scheme)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* RISK-13 (large lists degrade performance): a convention without a maximum page size
  invites unbounded responses — fix the cap here, even if the numeric default is a
  documented choice rather than a plan fact.
* Cursor semantics interact with SSE event history (9.6): keep the history endpoint on
  the cursor convention while resume-by-event-id stays a stream concern — conflating
  them would break the "no gaps, no duplicates" guarantee.
