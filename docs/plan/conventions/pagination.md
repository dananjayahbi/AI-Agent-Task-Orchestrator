# Pagination conventions — cursor-based lists

| Field | Value |
|---|---|
| Status | Published |
| Published | 2026-10-11 |
| Owner | WP-0.5 — Configuration, secrets and error conventions (MT-0.5-04) |
| Source of truth | Parent plan Sections 9.2 (cursor-based pagination), 9.5 (page-numbered attachment content), 7.3 (identifier rules), 9.6 (event history) — the plan is authoritative; this document is the published reference |
| Requirements | NFR-11 (typed contract), NFR-09 (10,000 tasks, 50 GB attachments); mitigates RISK-13 |
| Sibling conventions | [`configuration.md`](./configuration.md), [`error-envelope.md`](./error-envelope.md), [`headers.md`](./headers.md) |

## Purpose

Section 9.2 fixes "Pagination is cursor-based" for the v1 REST surface. The API
hosts list endpoints that must scale to 10,000 tasks and 50 GB of attachments
(NFR-09), with pagination named as a mitigation for RISK-13 (large lists degrade
performance). This document writes the one convention every list endpoint implements
— projects, tasks, work, checkpoints, resolutions, audit reports, attachments,
events history, merge pending, tokens — so the OpenAPI contract (NFR-11) and the
four clients agree from the first endpoint onward.

## Which endpoints this covers

Every list (`GET` on a collection) endpoint of the Section 9.2 table:

| Area | List endpoints under this convention |
|---|---|
| Tokens | `GET /tokens` |
| Projects | `GET /projects` |
| Tasks | `GET /projects/{pid}/tasks` |
| Agent work | `GET /projects/{pid}/work` |
| Progress | `GET /tasks/{id}/checkpoints` |
| Submission | `GET /tasks/{id}/resolutions` |
| Audit | `GET /tasks/{id}/audit-reports` |
| Merge queue | `GET /merge/pending` |
| Attachments | `GET /tasks/{id}/attachments` |
| Events | `GET /events` (history with filters) |

Single-resource `GET`s (project detail, manifest, policy, task detail, patch,
attachment detail, dashboard summary, health) are not lists and carry no
pagination. Section 9.2 defines no `GET /devices` collection — none is claimed
here; any list endpoint added later joins this convention automatically.

## The canonical cursor contract

* **Canonical query parameter:** `cursor` — one name for every list endpoint.
  The first page is requested without `cursor`; each subsequent request passes back
  the `next_cursor` value from the previous response.
* **Canonical response envelope:** every list response is an object with exactly
  two members — `results` (the page's items, in the endpoint's declared order) and
  `next_cursor` (the opaque cursor for the following page). The wire contract:

```json
{
  "results": [],
  "next_cursor": "opaque-cursor-example"
}
```

* **End-of-list semantics:** `next_cursor` absent or `null` means the end of the
  list — there is no next page. Clients stop on that signal alone and never infer
  completion from page length.
* **Page size:** the canonical parameter `page_size` selects the number of items
  per response. **Documented defaults (WP-0.5 choices, not plan facts — the plan
  states no numbers):** default `25`, maximum `100`. A response never exceeds the
  maximum; how a request above it is treated (clamped or rejected with
  `VALIDATION_ERROR`) is fixed per endpoint in the OpenAPI contract (WP-1.1), not
  here. The values are subject to the units/metadata rules of
  [`configuration.md`](./configuration.md) if exposed as settings — only through an
  existing Section 9.10 group; new configuration semantics become an open question
  first (Section 20.1, rule 5). The maximum exists because RISK-13 demands a cap.

## Rules

1. **Cursor opacity.** A cursor is opaque to clients: the server may encode
   ordering state inside it; clients never construct, parse, modify or interpret a
   cursor — only pass it back verbatim. A cursor is valid only for the same
   endpoint with the same filter and sort parameters it was issued under.
2. **Stable ordering.** Each list endpoint declares exactly one deterministic sort
   in its OpenAPI contract, so paging never skips or duplicates rows. The default
   shape is server-clock `created_at` (UTC, ISO-8601 — Section 0.4, Principle P7)
   with the row's stable identifier (Section 7.3) as tiebreak. An identifier
   tiebreak must order by the id's generation rule — Section 7.3 ids grow beyond
   three digits naturally (`T1000`), so raw lexicographic string comparison of ids
   is not a stable order. Client-supplied timestamps never order a listing.
3. **One mechanism per surface.** Cursor pagination is the only collection-listing
   mechanism on the v1 surface. Offset pagination is not part of the plan and is
   never offered here.

## Documented exception — attachment `content` (Section 9.5)

`GET /attachments/{id}/content?format=&page=` is **page-numbered, by explicit plan
specification**: the request carries `page`, and the response carries
`page_number`, `total_pages` and a token count for the returned page/chunk so an
agent can budget context (Section 9.5 retrieval behavior).

* This is a pre-existing, deliberate exception to cursor pagination — implementers
  must **not** "unify" it into the cursor convention; Section 9.5 is authoritative.
* The exception is specific to that one retrieval endpoint. It creates no
  precedent: no other endpoint may use page numbers, and it is not offset
  pagination on collections.

## SSE history vs stream resume (Section 9.6)

`GET /events` (history, filters) is a list endpoint and follows the cursor
convention above. Reconnect resume of `GET /events/stream` by last event id is a
separate, stream-recovery mechanism (Section 9.6: "no gaps, no duplicates") — event
ids never act as list cursors, and cursors never resume a stream. See also the
three-mechanism disambiguation in [`headers.md`](./headers.md).

## OpenAPI obligation (NFR-11, ADR-005)

The `cursor` and `page_size` parameters, the two-member response envelope, and each
endpoint's declared sort are part of the typed contract generated in WP-1.1 and
guarded by schema diff in CI (Section 18 quality gates; Section 20.4, item 4). The
contract is the single source for web and mobile clients (NFR-11).

## Out of scope (for this document)

* Implementing pagination in any endpoint — WP-1.3 / WP-1.4 onwards (first list
  endpoints).
* Changing the attachment `content` page scheme — fixed by Section 9.5.
* Offset pagination anywhere — explicitly not part of the plan.
* Client-side paging UI/UX (infinite scroll, page controls) — WP-4.x / WP-5.x.
* Page-size numbers beyond the documented defaults above — the plan states none;
  these are marked as documented defaults, never as plan facts.

## References

* Parent plan Section 9.2 — "Pagination is cursor-based"; the list-endpoint
  inventory above.
* Parent plan Section 9.5 — attachment `content` page scheme (`page`,
  `page_number`, `total_pages`).
* Parent plan Section 7.3 — identifier generation rules (stable sort anchors);
  Section 9.6 — event history filters.
* Referenced from the package documentation of `backend/`, `bridge/`, `web/` and
  `mobile/` (WP-0.5 acceptance).
