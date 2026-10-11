# MT-1.13-01 — Define the DescriptionProvider Interface (Disabled / Remote-Vision Implementations)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.13-01 |
| Title | Define the DescriptionProvider interface (disabled / remote-vision implementations) |
| Parent WP | WP-1.13 — Visual description provider (Milestone M1) |
| Requirements | FR-ATT-02, FR-ATT-05; G-14 |
| Priority | M |
| Dependencies | MT-1.12-01 … MT-1.12-08 (WP-1.12 complete; image stage awaits the caption hook) |
| Parent sections | 4 (G-14), 9.5, 9.10, 19.1 (WP-1.13), 20.4, 20.5; OQ-07 |

## Context
Section 9.5 fixes the description provider as "a pluggable interface with implementations
'disabled', 'Anthropic-compatible vision model', and 'local model'", where descriptions
are generated once and cached, cost and failures are logged, and failures degrade to
OCR-only. G-14 resolved the spec gap the same way: a pluggable `DescriptionProvider`
configured in the backend, can be disabled, result cached permanently per attachment
(WP-1.13). MT-1.12-02 deliberately stopped before the caption step — "the layout caption
is produced when WP-1.13 lands" — so this micro-task defines the seam that the image
pipeline stage (Section 9.5 stage 2) will call and that MT-1.13-02/03 implement. OQ-07
governs provider choice and budget: recommended default disabled.

## Inputs / Prerequisites
* MT-1.12-01 … MT-1.12-08 — the pipeline is complete; the image stage has OCR output
  and normalized images ready to caption (Section 9.5 stage 2).
* Parent plan Section 9.5 — the three named implementations, "generated once and
  cached", "cost and failures are logged", "failures degrade to OCR-only".
* Parent plan Section 9.10 — "description provider settings" is a configuration group;
  every setting needs a documented default and startup validation.
* OQ-07 — which provider and monthly budget: disabled by default (recorded in WP-0.4;
  re-read the recorded decision).
* MT-0.5-01 — environment naming conventions for the provider settings.

## Scope (in)
* Define the `DescriptionProvider` interface: input contract (normalized image and/or
  OCR transcript plus attachment identity), output contract (description text or an
  explicit "no description" result), and a typed failure signal the pipeline can catch
  to degrade (Section 9.5).
* Define the configuration-driven selection point: which implementation is active,
  resolved from the Section 9.10 description provider settings, with **disabled as the
  documented default** (OQ-07).
* Leave in place the pipeline call-site stub from MT-1.12-02 so the image stage routes
  through the interface rather than any concrete class (no direct imports of
  implementations outside the provider module).
* Document the obligations the interface must honor so later micro-tasks cannot miss
  them: descriptions generated once per attachment (MT-1.13-04), cost and failure
  logging (MT-1.13-03), degradation to OCR-only (MT-1.13-05).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Behavior of the disabled implementation — MT-1.13-02.
* The remote vision-model implementation, its credentials and cost logging — MT-1.13-03.
* Caching semantics — MT-1.13-04.
* Failure degradation behavior and tests — MT-1.13-05.
* The "local model" implementation named in Section 9.5: WP-1.13 deliverables list only
  "disabled and remote-vision implementations", so local model stays out until a new
  OQ or plan amendment asks for it (Section 20.1 principle 5).
* Wiring captions into task payloads and retrieval outputs — WP-1.14 consumes them.

## Target paths
* `backend/apps/attachments/` (provider interface module and selection/factory helper)
* `backend/tests/attachments/` (interface contract and selection tests)
* Environment template entry: description provider settings group (Section 9.10)
* WP changelog entry

## Acceptance criteria
- [ ] A single `DescriptionProvider` interface exists with documented input, output and
  failure contracts covering Section 9.5's caption step (FR-ATT-02, G-14).
- [ ] Implementation selection is configuration-driven with **disabled** as the
  documented default, matching OQ-07's recommended default (Section 9.10).
- [ ] The image pipeline stage calls only through the interface — a test or import check
  proves the pipeline module has no concrete-implementation import (Section 20.5).
- [ ] Settings appear in the environment template with documented defaults (Section
  9.10; Section 20.4 item 3 — no secrets committed).
- [ ] Tests, lint and type check green in CI (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
`pytest backend/tests/attachments -k description_provider -v` — asserts the interface
contract, that the default selection resolves to the disabled implementation with no
provider settings present, and that overriding the setting selects by name; then run
`uv run --directory backend ruff check .` and the documented mypy invocation (MT-0.1-02).

## Attachments
* [Section 9.5 — Attachment processing (description provider)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [G-14 — Visual description provider gap resolution](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [OQ-07 — Which provider and budget](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Section 9.5 names a "local model" implementation but WP-1.13's deliverables do not —
  do not build it speculatively; raise a new OQ (next free `OQ-15+` id) if requested.
* The exact settings keys for the provider are not fixed by the plan beyond "description
  provider settings" (Section 9.10) — choose names via MT-0.5-01 conventions and record
  them in the changelog so MT-1.13-03 configures the same keys.
* Interface shape (sync vs. task-based) is a pipeline-integration decision: match how
  MT-1.12-02 structures worker stages, and note the choice — do not fork a second
  async path.
