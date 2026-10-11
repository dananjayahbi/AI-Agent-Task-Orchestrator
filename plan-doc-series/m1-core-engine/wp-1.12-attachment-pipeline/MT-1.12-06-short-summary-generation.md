# MT-1.12-06 — Implement Short Summary Generation per Document

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.12-06 |
| Title | Implement short summary generation per document |
| Parent WP | WP-1.12 — Attachment pipeline: parse, OCR, chunk, tokens (Milestone M1) |
| Requirements | FR-ATT-02, FR-ATT-03 |
| Priority | M |
| Dependencies | MT-1.12-05 (chunks available as summary input) |
| Parent sections | 9.5, 19.1 (WP-1.12), 9.10, P10, 20.4, 20.5 |

## Context
Section 9.5 documents stage: after splitting and token estimation, "generate a short
summary." FR-ATT-03: the descriptor carries a short description. The summary is
derived data — re-creatable (Section 9.5) — and its input is untrusted attachment
content (P10): the summary path must treat extracted text as data, never as
instructions.

## Inputs / Prerequisites
* MT-1.12-05 — chunked, token-estimated text (summary input with a bounded context).
* Parent plan Section 9.5 — "short summary" per document (images included via their
  OCR transcript — see scope).
* Section 9.10 — generation settings (model/provider hooks) are environment-driven
  with documented defaults; OQ-07 governs vision-provider selection (WP-1.13) — this
  task's text summary must not depend on it.
* WP-0.5 conventions for any errors surfaced.

## Scope (in)
* Summary generation over the extracted text (bounded by chunks — first/most
  representative chunks under a documented token budget) producing a short summary
  stored as derived data and exposed through the descriptor's short-description
  field (FR-ATT-03).
* Images: a short summary derived from the OCR transcript (layout captions arrive
  with WP-1.13; do not wait for it).
* Provider configuration per Section 9.10 with a documented default; a deterministic
  fallback (e.g. extractive head-of-document summary) when no generative provider is
  configured, so the pipeline completes offline (OQ-07 default is "disabled").
* Untrusted-content handling: summary input is treated as data; the stored summary
  contains no instruction-following behavior — asserted by a prompt-injection-style
  fixture test.
* Tests: summary length within documented bounds, populated on descriptors,
  fallback path with provider disabled, injection fixture handled as data.

## Out of scope
* Vision/layout captions and their caching — WP-1.13 (OQ-07).
* Chunking/token estimation — MT-1.12-05.
* Status/retry — MT-1.12-07.
* Serving summaries in payloads — descriptor shape fixed in MT-1.11-04; web/mobile
  display is WP-4.x/WP-5.x.
* The P10 untrusted-content banner on retrieved text — WP-1.14.

## Target paths
* `backend/apps/attachments/summarize.py`
* `backend/tests/attachments/test_summary.py`
* Environment template entries: summary provider settings (documented defaults)
* WP changelog entry

## Acceptance criteria
- [ ] Every processed document attachment gets a short summary persisted as derived
  data and exposed on the descriptor (Section 9.5; FR-ATT-03).
- [ ] With no generative provider configured (OQ-07-style default), the pipeline
  still completes using the documented fallback — no hard dependency on a remote
  model (Section 9.10 documented defaults; Section 20.4 item 3).
- [ ] An injection fixture ("ignore previous instructions…") yields a summary that
  quotes/neutralizes the text and never follows it (P10).
- [ ] Summary inputs are bounded by the documented token budget; output length
  within documented bounds.
- [ ] Lint, type check and tests green (item 2); changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_summary.py -v` — summary produced for each
document kind, fallback with provider disabled, bounds, injection-fixture handling.

## Attachments
* [Section 9.5 — Attachment processing (short summary)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.10 — Configuration](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-ATT-03 — Short description in descriptors](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* If a generative provider is configured, its calls cost money and can fail — failures
  must degrade to the fallback summary, not fail the pipeline (analogous to the
  Section 9.5 description-provider degradation; log cost/errors like WP-1.13 will).
* "Short" is not quantified in the plan — document the chosen bound in the changelog
  note rather than inventing a requirement.
