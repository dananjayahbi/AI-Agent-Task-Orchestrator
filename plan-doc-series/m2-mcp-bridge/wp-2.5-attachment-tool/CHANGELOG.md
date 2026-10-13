# WP-2.5 — Attachment tool (`read_task_attachment`)

Capability-negotiated attachment delivery in the MCP bridge: the
Section 10.4 resolver, the editable client capability table, MCP image
blocks for vision sessions, banner-correct text/OCR packaging, one-based
pagination, and the cross-path capability matrix (MT-2.5-01 … MT-2.5-06).

## Delivered

### MT-2.5-01 — capability resolver

`src/orchestrator_bridge/capabilities.py`: `resolve_capability()` applies
Section 10.4's four steps in order (explicit `format_preference` → session
capability → client table → text-safe `unknown` default), short-circuiting
on the first decisive step. The resolver is a pure function of explicit
inputs (table and session value are parameters), reports which step decided
the delivered format (`ResolutionStep`), and attaches the step-4
explicit-request note whenever the capability is `unknown`. Capability is
always resolved (even under an explicit format) because Section 9.5's
image gate needs it. `client_identity()` reads the MCP handshake
(`Context.session.client_params.client_info`) defensively — every optional
layer is None-safe and never raises from a tool call.

New setting: `ORCHESTRATOR_BRIDGE_SESSION_CAPABILITY` (`vision` |
`text_only`; unset = `unknown` = text-safe) → `Settings.session_capability`
→ `ToolRuntime.session_capability`, passed by both entrypoints (stdio and
HTTP connection). Follow-up: the row belongs in
`docs/plan/conventions/configuration.md` (hot shared contract, not owned by
this WP — see Follow-ups).

### MT-2.5-02 — client capability table

`bridge/capability_table/clients.json` (editable, Appendix A path) seeded
from Section 10.9 with **every client at `unknown`** — "Expected yes",
"To verify", "Likely text-only" and the stated "Text-only" rows are
predictions, not verified claims (ADR-006). Loader
(`src/orchestrator_bridge/capability_table.py`): case-insensitive name
match, optional dotted-version windows, first match wins; missing /
malformed / non-object files degrade to the empty table (every lookup →
unknown) with a warning, never a crash; per-entry malformation skips one
entry; unrecognized capability values record `unknown`. Path resolution:
explicit argument → `ORCHESTRATOR_BRIDGE_CAPABILITY_TABLE` override → the
shipped repo file; cached per resolved path (startup semantics: edits take
effect on process restart — documented in the table's README). Editing
procedure for WP-2.11 conformance runs: `bridge/capability_table/README.md`.

### MT-2.5-03 — image content blocks

`tools/attachment.py` + `tools/attachment_packaging.py`: vision sessions
under `auto` (or explicit `image_base64`) receive an MCP `ImageContent`
block plus a compact `TextContent` provenance block (capability/step);
the bridge asks the backend for `image_base64` explicitly (backend `auto`
is text-safe per WP-1.14). Text-only sessions' explicit `image_base64` is
rejected before the wire with `ATTACHMENT_UNSUPPORTED_FORMAT`, hinting
`auto`/`text_ocr` — unless `force=true` (recorded decision below). The
not-ready descriptor short-circuits with `ATTACHMENT_NOT_READY` + status
details; a content-endpoint 409/415 envelope passes through verbatim
through the translator. A payload without image data is a
`SERVER_ERROR` malformed-response failure, never a crash.

### MT-2.5-04 — text/OCR packaging

`text_result()` surfaces `content`, `description` (text_ocr), and the page
triple with nulls dropped; empty OCR is a usable degraded state (keys drop
out; attachment id/format/resolution still delivered). Banner (P10):
`ensure_untrusted_banner()` is idempotent on the documented default
`[UNTRUSTED CONTENT] …` **and** on any banner starting with the
`[UNTRUSTED` marker — the backend annotates at REST delivery (WP-1.14), so
server-annotated text passes through unchanged (wp-1.13 double-banner
note), while a hypothetical unannotated path is still marked exactly once.
Image blocks bypass banners by design (Section 9.5 prefixes text outputs;
the provenance block is bridge metadata). The step-4 explicit-request note
travels in every text result's `resolution` block.

### MT-2.5-05 — pagination

`page_number` (integer ≥ 1, default 1) is forwarded as the one-based
`page` param on the paginated `markdown` path only — a documented no-op on
image/OCR (accepted, never sent). `page_number`/`total_pages`/`token_count`
surface on the result when the backend sends them (token count documented
as an estimate, never presented as exact). Out-of-range pages surface the
backend's `VALIDATION_ERROR` with pagination-specific recovery guidance
("retry with `page_number` in 1..total_pages") while details pass through
verbatim.

### MT-2.5-06 — capability matrix tests

`tests/test_attachment_capability_matrix.py` + the image/text/pagination
suites: format × capability × resolver-step combinations green against the
transport-seam fake, banner presence asserted on every delivered text
shape, pagination asserted, and the shipped table's entries proven to
resolve text-safe (no verified client claims vision).

## Recorded decisions

* **`force` input (new, recorded):** Section 9.5 says an image request
  from a text-only session is rejected "unless forced" but names no
  mechanism; the tool schema gains an optional `force` boolean (default
  false). Explicit `image_base64` alone is not the force — otherwise
  "rejected without force" would be unreachable. Flagged for plan review
  per §20.1 item 5.
* **Session-capability setting:** `ORCHESTRATOR_BRIDGE_SESSION_CAPABILITY`
  is a normal optional Settings key (env > user file > unset), validated
  `vision|text_only` at startup; unset is the honest text-safe default.
  The bridge never infers vision (ADR-006).
* **Banner split:** the backend owns the banner on REST-delivered text
  (WP-1.14); the bridge's `ensure_untrusted_banner` is the idempotent
  defense-in-depth guard, not a second annotator. Residual edge: a
  deployment rewording the banner *without* keeping the `[UNTRUSTED`
  marker would get the bridge's default prefix added after the server's
  (double marker) — documented in the packaging module.
* **Table in wheels:** the table file is repo-level
  (`bridge/capability_table/clients.json`); an installed wheel has no copy
  and degrades to the empty table (text-safe). Shipping a copy inside the
  wheel (hatch force-include) is a follow-up, not required by MT-2.5-02's
  acceptance.

## Files

`src/orchestrator_bridge/capabilities.py`,
`src/orchestrator_bridge/capability_table.py`,
`src/orchestrator_bridge/tools/attachment.py`,
`src/orchestrator_bridge/tools/attachment_packaging.py`,
`bridge/capability_table/clients.json`,
`bridge/capability_table/README.md`, `tools/schemas.py`,
`tools/registration.py`, `tools/runtime.py`, `config.py`,
`entrypoints/stdio.py`, `http_service/connection.py`, `bridge/.env.example`;
tests: `test_capability_resolver.py`, `test_capability_table.py`,
`test_attachment_image.py`, `test_attachment_text.py`,
`test_attachment_pagination.py`, `test_attachment_capability_matrix.py`,
plus pinned-test updates (`test_tool_schemas.py`, `test_layout.py`,
`conftest.py`).

## Follow-ups

* `docs/plan/conventions/configuration.md` needs the
  `ORCHESTRATOR_BRIDGE_SESSION_CAPABILITY` row (hot shared contract;
  single-owner — not edited here).
* Live-gated end-to-end attachment runs against a real backend
  (`ORCHESTRATOR_BRIDGE_LIVE_TESTS=1`) once the WP-1.12 pipeline has a
  seeded image fixture.
* WP-2.11 conformance runs populate the table's observed clientInfo
  names/versions and flip verified capabilities.

### Convergence gate (2026-10-14)

- Closed the `configuration.md` follow-up: the `ORCHESTRATOR_BRIDGE_SESSION_CAPABILITY` row was added at convergence, and `bridge/.env.example` was re-verified as documenting the key.
