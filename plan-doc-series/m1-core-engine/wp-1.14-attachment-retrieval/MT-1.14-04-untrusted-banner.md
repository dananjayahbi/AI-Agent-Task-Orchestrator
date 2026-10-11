# MT-1.14-04 — Prefix All Text Outputs with the Untrusted-Content Banner

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.14-04 |
| Title | Prefix all text outputs with the untrusted-content banner |
| Parent WP | WP-1.14 — Attachment retrieval API (Milestone M1) |
| Requirements | FR-ATT-04; G-07, NFR-10 |
| Priority | M |
| Dependencies | MT-1.14-02 (content endpoint), MT-1.14-03 (paginated responses), MT-0.5-02/MT-0.5-03 (header/error conventions) |
| Parent sections | 9.5 (P10), 19.1 (WP-1.14 slices), 20.4, 20.5 |

## Context
Section 9.5 makes the banner a privacy requirement, not decoration: "When task text
that includes original text — OCR transcripts, descriptions, extracted markdown — is
returned to an agent, it is prefixed with an untrusted-content banner (P10)." FR-ATT-04
closes the same loop: "all such text is prefixed with the untrusted-content banner
before delivery." Rationale (Section 9.5 stage 3 / G-07): an attacker-controlled file
must not become trusted instructions inside a model's context — the banner tells the
model the content is data, not commands. WP-1.14's fourth slice is "untrusted-content
banner". Since the content endpoint is the only backend path that returns
attachment-derived text (and the `text_ocr` description fields and any task-side
summaries flow through related serializers), the banner must be applied uniformly, at
one choke point, so no new delivery path can skip it.

## Inputs / Prerequisites
* MT-1.14-02 / MT-1.14-03 — the content endpoint producing text responses to decorate.
* MT-1.12-08 / MT-1.13-03 — the original-text sources (OCR transcript, layout
  description, extracted markdown, provider description).
* Parent plan Section 9.5 — banner requirement and its placement ("prefixed").
* FR-ATT-04 — "before delivery" of all such text.
* MT-0.5-02 / MT-0.5-03 — envelope and header conventions (the banner is content,
  not a header; keep separation).
* Note: Section 9.5's attachment **errors** paragraph and the banner are distinct
  mechanisms — the banner prefixes successful text payloads only.

## Scope (in)
* A single shared prefixer that prepends the untrusted-content banner to every text
  payload derived from attachment content: OCR transcripts, layout/description text,
  extracted markdown pages, and provider-generated descriptions when surfaced as raw
  text.
* Apply it at the content endpoint boundary (the choke point for `text_ocr`,
  `markdown`, and text-safe `auto`) so every format path inherits it — including
  paginated pages (each page is delivered text, so each page carries the banner;
  note this in the changelog so clients strip/expose it knowingly).
* Exactly one banner per delivered text value — not once per response with multiple
  fields, and never double-prefixed when a cached description (MT-1.13-04) is already
  decorated at its source: pick one layer, test for duplicates, and document the
  chosen layer in the changelog.
* Banner text itself is fixed configuration read through the MT-0.5-01 env
  conventions (no hardcoded environment-specific paths — Section 20.4 item 3); no
  secrets involved.
* Tests: every text-returning format/endpoint case asserts the banner prefix and its
  absence on non-text responses (`image_base64` bytes are never prefixed); descriptor
  short descriptions in task payloads (MT-1.14-01) follow the same decision — either
  decorated or left as short metadata, decided once and asserted either way.
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Bridge-side banner application for model-content blocks (WP-2.5 prefixes before
  delivering to a model — Section 9.5 P10; this task delivers the REST payload
  already annotated).
* Enclosing content in delimiters in addition to the banner — P10 specifies a banner
  prefix only; do not invent a second wrapper.
* Sanitizing/escaping content (prompt-injection detection) — out of plan scope; the
  banner is the plan's mitigation.
* Error payloads — errors use the Section 9.2 envelope, not the banner.
* The `format`, pagination and error behaviors — MT-1.14-02 / 03 / 05.

## Target paths
* `backend/apps/attachments/` (shared banner helper applied in the content view)
* `backend/` configuration for the banner text (MT-0.5-01 conventions)
* `backend/tests/attachments/` (banner presence/absence/per-page assertions)
* WP changelog entry

## Acceptance criteria
- [ ] Every attachment-derived text response is prefixed with the untrusted-content
  banner before delivery — Section 9.5 P10; FR-ATT-04; WP-1.14 fourth slice.
- [ ] The banner appears exactly once per delivered text value across all paginated
  pages and repeated retrievals (no double-prefixing of cached descriptions).
- [ ] `image_base64` responses are untouched (binary, not text).
- [ ] The banner text is configuration, not hardcoded environment-specific content
  (Section 20.4 item 3); no secrets (item 3).
- [ ] Cross-cutting rule covered: one helper used by all text paths, with tests that
  would fail if a new format path forgot it (Section 19.6 engineering rule).
- [ ] Tests, lint and type check green in CI (item 2); changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_untrusted_banner.py -v` — banner on
`text_ocr` / `markdown` / text-safe `auto` responses, one banner per page of a
multi-page document, cached-description re-retrieval, absence on `image_base64`;
full suite green.

## Attachments
* [Section 9.5 — Untrusted-content banner (P10)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-ATT-04 — Four-format retrieval with banner](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [G-07 — Prompt-injection posture](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Double-prefixing is the realistic bug: description cached after banner application
  at generation time versus banner applied at delivery time. Apply the banner at
  delivery (content endpoint) only, store un-decorated text, and assert
  non-duplication in tests — record this storage decision in the changelog because
  MT-1.13-04 (caching) and WP-2.5 (model delivery) both read the same stored value.
* Whether the descriptor `short description` in task payloads (MT-1.14-01) counts as
  "returned text" under FR-ATT-04 is not spelled out cell-by-cell — decide once
  (banner vs. short-metadata exemption), state the reading in the changelog, and
  raise a new OQ (`OQ-15+`) if web/mobile consumers object to banners in list views.
* P10's "delivered to a model" wording means WP-2.5 must not strip the REST banner
  and re-add its own inconsistently — coordinate the single banner contract in the
  WP changelog note so the bridge and backend agree on who applies it on each path.
