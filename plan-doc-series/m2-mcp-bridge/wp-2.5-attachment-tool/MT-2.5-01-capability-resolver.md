# MT-2.5-01 — Implement the capability resolver (explicit param, config, client table, default)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.5-01 |
| Title | Implement the capability resolver (explicit param, config, client table, default) |
| Parent WP | WP-2.5 — Tool: `read_task_attachment` with capability negotiation (Milestone M2) |
| Requirements | FR-ATT-04, FR-ATT-05 |
| Priority | M |
| Dependencies | WP-2.4 (core tools and tool plumbing), WP-1.14 (attachment content endpoint), MT-2.5-02 (capability table read by lookup step) |
| Parent sections | 10.4, 9.5, 10.9, 19 (WP-2.5), 20.4, 20.5 |

## Context
Section 10.4 fixes one resolution order for every attachment read: (1) explicit
`format_preference` in the call (except `auto`), (2) session capability set at startup
via configuration or environment, (3) lookup of the MCP client name/version against a
maintained capability table (editable file), (4) default `unknown`, treated as
text-safe — OCR plus description first, with a note on how to request the image
explicitly. Section 9.5's `format_preference` table defines what each resolved format
does downstream. This micro-task implements the resolver itself — the single decision
point that `read_task_attachment` consults before packaging content — so packaging
tasks (MT-2.5-03, MT-2.5-04) only consume a resolved capability, never re-derive it.

## Inputs / Prerequisites
* Parent plan Section 10.4 — the four-step resolution order (verbatim).
* Parent plan Section 9.5 — retrieval behavior table for `auto`, `image_base64`,
  `text_ocr`, `markdown`.
* Parent plan Section 10.9 — client compatibility matrix as the starting content for
  the capability table (WP-2.11 verifies it later).
* WP-2.4 — the `read_task_attachment` tool shell and schema plumbing conventions.
* WP-1.14 — backend content endpoint whose `format` the resolver feeds.
* Parent plan Section 18 (Unit row) — capability resolution is named as a table-driven
  unit-test subject.

## Scope (in)
* A single resolver module invoked per attachment read that applies the four steps in
  exactly the Section 10.4 order, short-circuiting on the first decisive step.
* Explicit non-`auto` `format_preference` always wins over configuration, table and
  default.
* Session capability configuration (startup/env) as step 2, with a documented default
  when unset.
* A lookup hook for step 3 keyed by MCP client name and version, reading the editable
  table file created in MT-2.5-02; a client miss falls through to step 4.
* Step 4 behavior: resolve to `unknown` (text-safe), which downstream packaging turns
  into OCR plus description plus the note on requesting the image explicitly.
* Surfacing which resolution step decided, in the tool's structured output, so tests
  and debugging can assert the path taken.
* Table-driven unit tests for all four steps, including client-name misses
  (Section 18 unit row).

## Out of scope
* The capability table file's contents and seeding — MT-2.5-02.
* Image content-block packaging — MT-2.5-03.
* Text/OCR packaging and the untrusted banner — MT-2.5-04.
* Pagination parameters — MT-2.5-05.
* Verifying real clients against the table — WP-2.11 (conformance script).
* Backend `content` endpoint behavior — WP-1.14.

## Target paths
* `bridge/` — capability resolver module
* `bridge/tests/` — resolver unit tests
* WP changelog entry

## Acceptance criteria
- [ ] The resolver implements the four Section 10.4 steps in order, with an explicit
  non-`auto` `format_preference` short-circuiting config, table and default.
- [ ] An unknown or missing client resolves to `unknown` (text-safe), and the result
  notes how to request the image explicitly (Section 10.4 step 4).
- [ ] The resolving step is reported in the structured output and asserted by tests.
- [ ] Table-driven unit tests cover all four steps and the client-miss fall-through
  (Section 18 unit row).
- [ ] No packaging path re-implements resolution logic (one resolver, consumed by
  MT-2.5-03/04).
- [ ] Lint, type check and tests green in CI (Section 20.4 item 2); changelog note
  added (item 7).

## Test command
`uv run pytest bridge/tests/ -k capability -q` — assert each resolution step wins in
its turn, the client-miss falls to `unknown`, and the reported step matches the
expected table row; then the full bridge suite stays green.

## Attachments
* [Section 10.4 — Capability negotiation](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.5 — Attachment processing (retrieval behavior)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Order drift: implementing table lookup before session config (or letting `auto`
  sneak past step 1) silently changes behavior — pin the order with tests, the plan
  stays authoritative (Section 0).
* Session-capability configuration touches startup config, so a missing key must fall
  back safely to step 3/4 rather than fail the bridge (no hidden decisions — Section
  20.1).
* The table's contents may claim capabilities no client actually has; MT-2.5-02 keeps
  unverified entries at `unknown` until WP-2.11 confirms them.
