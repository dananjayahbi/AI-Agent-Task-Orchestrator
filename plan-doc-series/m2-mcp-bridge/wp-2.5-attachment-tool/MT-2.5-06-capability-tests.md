# MT-2.5-06 — Write capability tests for both vision and text-only paths

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.5-06 |
| Title | Write capability tests for both vision and text-only paths |
| Parent WP | WP-2.5 — Tool: `read_task_attachment` with capability negotiation (Milestone M2) |
| Requirements | FR-ATT-04, FR-ATT-05, FR-ATT-06 |
| Priority | M |
| Dependencies | MT-2.5-01..05 (the full WP-2.5 implementation), WP-1.11/WP-1.12 (sample upload fixtures), WP-0.3 (CI) |
| Parent sections | 9.5, 10.4, 19 (WP-2.5), 18, 20.4, 20.5 |

## Context
WP-2.5's acceptance is a behavior triple: vision session receives an image block;
text-only session receives OCR plus description; every text output carries the
untrusted banner. Section 18's end-to-end row explicitly includes a "text-only model
with screenshot" scenario, and the unit row names capability resolution. This final
slice of WP-2.5 writes the cross-cutting test suite that proves the three paths work
together (resolver → table → packaging → banner/pagination), complementing the
per-slice unit tests written along the way.

## Inputs / Prerequisites
* MT-2.5-01..05 — resolver, table, image packaging, text packaging, pagination.
* Parent plan Section 9.5 and 10.4 — the behaviors under test (verbatim).
* Parent plan Section 18 — unit row (capability resolution) and end-to-end row
  ("text-only model with screenshot").
* WP-1.11/WP-1.12 — sample attachments (image with OCR-able text, document, non-image)
  for fixtures.
* WP-0.3 — CI pipeline that runs the suite.

## Scope (in)
* A cross-path test suite driving `read_task_attachment` end to end against the
  integration environment:
  * vision session + image + `auto` → MCP image content block;
  * text-only session + image + `auto` → OCR plus description;
  * every text output shape (`auto` text, `text_ocr`, `markdown`) prefixed with the
    untrusted banner;
* A matrix over `format_preference` (`auto`, `image_base64`, `text_ocr`, `markdown`)
  crossed with session capability (vision, text-only, `unknown`), asserting the
  resolver step that decided each outcome.
* Table-file interaction cases: known client, unknown client, missing file — each
  landing on the expected packaging path.
* Pagination assertions on document reads (page fields + token count) with image/OCR
  paths unaffected.
* The Section 18 end-to-end "text-only model with screenshot" scenario hooked into
  the suite (or asserted here if the scenario runner owns it).
* CI wiring so the suite runs with the bridge test jobs (Section 20.4 item 2).

## Out of scope
* Re-writing the per-slice unit tests — they stay with MT-2.5-01..05.
* Real-client conformance runs (Claude Code CLI, Aider, etc.) — WP-2.11.
* Backend pipeline correctness (OCR quality, normalization) — WP-1.12/WP-1.13; this
  suite consumes their fixtures.
* Performance/load testing — Section 18 performance layer.

## Target paths
* `bridge/tests/` — capability cross-path suite
* CI pipeline config (suite invocation)
* WP changelog entry

## Acceptance criteria
- [ ] Vision session + image via `auto` yields an MCP image content block
  (WP-2.5 acceptance, FR-ATT-05).
- [ ] Text-only session + image via `auto` yields OCR plus description (WP-2.5
  acceptance, FR-ATT-05).
- [ ] Every text output in the matrix carries the untrusted banner (WP-2.5
  acceptance, FR-ATT-06, Section 9.5).
- [ ] The format × capability matrix passes, with each outcome traceable to the
  resolver step that produced it (Section 10.4).
- [ ] Pagination fields present on document reads; image/OCR paths unaffected
  (FR-ATT-04).
- [ ] Only catalog error codes appear in failure cases (Section 20.4 item 5); suite
  green in CI (item 2); changelog note added (item 7).

## Test command
`uv run pytest bridge/tests/ -k attachment_capability -q` — run the cross-path matrix
and banner assertions against the integration environment; then the full bridge suite
stays green.

## Attachments
* [Section 9.5 — Attachment processing (retrieval behavior)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Do not "prove" the vision path with a stubbed image block — the WP acceptance is
  behavioral; use real fixtures from WP-1.11/WP-1.12 so pipeline-produced artifacts
  are what get packaged.
* Banner assertions must check every text branch, not one sample — a missed branch is
  exactly the failure mode the acceptance calls out.
* If the description provider is disabled in CI (OQ-07 default), the text-only path
  asserts OCR plus the degraded no-description outcome; document which variant each
  test covers rather than enabling a paid provider in CI.
