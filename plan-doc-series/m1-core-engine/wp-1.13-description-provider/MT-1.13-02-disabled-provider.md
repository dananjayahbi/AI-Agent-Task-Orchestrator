# MT-1.13-02 — Implement the Disabled Provider (No External Calls)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.13-02 |
| Title | Implement the disabled provider (no external calls) |
| Parent WP | WP-1.13 — Visual description provider (Milestone M1) |
| Requirements | FR-ATT-02, FR-ATT-05; G-14 |
| Priority | M |
| Dependencies | MT-1.13-01 (interface and selection in place), MT-1.12-02 (image stage hook) |
| Parent sections | 4 (G-14), 9.5, 19.1 (WP-1.13 acceptance), 20.4, 20.5; OQ-07 |

## Context
WP-1.13's acceptance has two halves; this task proves the first: "with provider
disabled, tasks still process using OCR only." OQ-07's recommended default is "Disabled
by default", and G-14 requires the provider to *be able* to be disabled — so the
disabled path is not a fallback, it is the out-of-the-box configuration of the whole
system. Section 9.5 lists "disabled" as one of the three named implementations. This
micro-task makes that implementation real: it answers the interface from MT-1.13-01
with no description and performs zero external calls, so a deployment without vision
credentials or budget processes attachments exactly as WP-1.12 already allows
(MT-1.12-02 explicitly deferred captions to this WP).

## Inputs / Prerequisites
* MT-1.13-01 — the interface, failure contract and configuration selection with
  disabled as default.
* MT-1.12-02 — the image stage that must complete without a caption when disabled.
* Parent plan Section 9.5 — pipeline stages; OCR runs regardless of the provider, and
  only the "layout caption" step depends on the provider.
* OQ-07 — recorded default: disabled (WP-0.4 decision; re-read before building).

## Scope (in)
* Implement the `disabled` provider: satisfies the interface, returns an explicit
  "no description" result, and makes **no network or subprocess calls of any kind**
  (Section 9.5, G-14).
* Register it as the configuration default so a fresh environment with no provider
  settings resolves to it (Section 9.10 documented default).
* End-to-end assertion through the pipeline: with default settings, an image fixture
  flows detect → normalize → OCR → caption step (no-op) → persist → `ready`, proving
  WP-1.13's first acceptance half ("tasks still process using OCR only").
* Confirm derived data written by the no-op path: no description field populated, no
  failure reason recorded, status transitions unchanged from MT-1.12-07 semantics.
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* The remote implementation and its configuration — MT-1.13-03.
* Caching — with nothing generated there is nothing to cache; MT-1.13-04 owns the
  cache contract (it must treat "disabled" as "no description", never as a cached
  empty string — note this for that task).
* Degradation behavior: disabled is a *choice*, not a failure; failure degradation is
  MT-1.13-05.
* Toggling the provider per project or per attachment — the plan configures the
  provider in the backend (G-14, Section 9.10), not per project; do not invent a
  policy field (Section 7.2 Project Policy has none).

## Target paths
* `backend/apps/attachments/` (disabled implementation registered with the selector)
* `backend/tests/attachments/` (no-external-call test, pipeline end-to-end with
  defaults)
* Environment template entry: confirm documented default (Section 9.10)
* WP changelog entry

## Acceptance criteria
- [ ] With no provider settings configured, the image pipeline completes to `ready`
  using OCR only — WP-1.13 acceptance, first half (FR-ATT-02).
- [ ] The disabled provider performs zero external calls: test asserts no HTTP client,
  subprocess or file-network access is invoked during a processing run (G-14 "can be
  disabled"; OQ-07 default).
- [ ] No description is persisted and no failure is recorded for the no-op caption step
  (Section 9.5 stage 4 only persists what was produced).
- [ ] The disabled implementation is selected by default in a fresh environment
  (Section 9.10 documented default; Section 20.4 item 3 — no secrets required).
- [ ] Tests, lint and type check green in CI (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
`pytest backend/tests/attachments -k disabled_provider or image_pipeline -v` — runs the
no-external-call assertion (network/subprocess blocked in the test) and the
default-settings pipeline flow to `ready`; CI must be green on the branch (Section
20.4 item 2).

## Attachments
* [Section 9.5 — Attachment processing (pipeline stages)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.13 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [OQ-07 — Provider default (disabled)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "No external calls" must be enforced by the test (blocked network / no client
  constructed), not by reading the code — a disabled provider that still pings a
  health endpoint violates OQ-07's budget intent.
* Do not encode "disabled" as an empty description string that downstream code (task
  payload short description, `text_ocr` output in WP-1.14) could mistake for a real
  caption; keep the explicit "no description" result through the interface contract
  fixed in MT-1.13-01.
* If MT-1.12-02's hook turns out never to call the provider when settings are absent,
  the "pipeline runs the caption step" assertion will silently pass — assert the hook
  is actually reached (call-spy), otherwise this test proves nothing.
