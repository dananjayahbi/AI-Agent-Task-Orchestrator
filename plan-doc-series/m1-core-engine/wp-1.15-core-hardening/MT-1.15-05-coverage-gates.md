# MT-1.15-05 — Establish Coverage Gates for the Hardening Suite

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.15-05 |
| Title | Establish coverage gates for the hardening suite |
| Parent WP | WP-1.15 — Core engine hardening (Milestone M1) |
| Requirements | NFR-01, NFR-12 (suite completeness); NFR-04 (aligned failures) |
| Priority | M |
| Dependencies | MT-1.15-01 … MT-1.15-04 (the four suites), MT-1.1-01/MT-1.2-06/MT-1.6-06 (modules under measurement), CI pipeline from WP-0.x |
| Parent sections | 18 (coverage targets), 19.1 (WP-1.15 acceptance), 19.6 (no duplication), 20.4 (items 1–2, 7), 20.5 |

## Context
WP-1.15's acceptance ends: "…and the Section 18 coverage target for the state machine
and leases." Section 18 sets the numbers: 85% overall line coverage on the **state
machine, lease logic, and Policy Engine**, and 100% branch coverage on the token
validation paths of the Policy Engine. WP-1.15's fifth slice is "coverage gates." The
gate is what turns those prose targets into a CI-enforced invariant — the same
spirit as the plan's other "one source" gates (MT-1.1-04's OpenAPI drift gate).
Caveat the plan itself carries: the Policy Engine is a Milestone M3 deliverable
(WP-3.4), so a M1 gate can only measure the modules that exist — the state machine
(MT-1.1-01) and lease/sweeper logic (WP-1.6/WP-1.7) — while the Policy Engine line
awaits M3. This micro-task defines what is measured now, enforces it in CI, and
records the deferred M3 portion explicitly.

## Inputs / Prerequisites
* MT-1.15-01 … MT-1.15-04 — the four suites whose combined run the gate wraps.
* MT-1.1-01 (state machine), MT-1.2-06 or the module holding lease logic
  (per Appendix A layout — measure actual modules present, no invented paths).
* Parent plan Section 18 — the 85%/100%-branch targets and coverage tooling context.
* Parent plan Section 19.1 — WP-1.15 acceptance wording ("Section 18 coverage target
  for the state machine and leases").
* Existing CI pipeline (WP-0.x groundwork) — the gate is a CI step, not a new system.

## Scope (in)
* Coverage measurement configured for the backend test runs with the modules under
  gate called out explicitly: the state machine and the lease/sweeper logic (Section
  18 targets; WP-1.15 acceptance names state machine and leases).
* Enforce ≥ 85% line coverage on those gated modules in CI — a run below threshold
  fails the job (Section 20.4 item 2, inverted: the gate makes "CI green" contingent
  on the coverage number).
* Per-file scope rather than whole-repo percentage: gate the named modules so
  unrelated low-coverage utilities cannot mask a regression in the state machine, and
  so unmeasured modules (e.g. Policy Engine, which arrives in WP-3.4) do not make
  the gate unpassable at M1.
* The four suites from MT-1.15-01 … 04 are the coverage-producing run — no parallel
  "coverage-only" test set (Section 19.6: one suite, one gate).
* Wire the gate into CI and document how to reproduce locally (Test command below);
  add the WP changelog note (Section 20.4 item 7).
* Record the deferred portion in the changelog: Policy Engine 85% line + 100% branch
  on token validation paths becomes enforceable at WP-3.4 (Section 18), not earlier.

## Out of scope
* Writing new tests to *reach* 85% — MT-1.15-01 … 04 supply the evidence; this task
  builds the measuring stick. If the measurement reveals a gap below threshold, the
  fix is a follow-up test addition attributed to the suite that owns the gap (record
  in the changelog; do not silently lower the threshold).
* Whole-repo coverage percentage targets — the plan sets them only for the named
  modules (Section 18); do not invent a repo-wide number.
* Policy Engine branch coverage enforcement — deferred to WP-3.4 per Section 18 (M3).
* Performance/NFR-01 load thresholds — Section 18 keeps optimization out of M1.

## Target paths
* Backend coverage configuration (pytest-cov or the tool the repo already uses —
  configure, do not introduce a second tool)
* CI workflow step enforcing the threshold on the gated modules
* `docs/testing.md` or the existing testing doc note on local reproduction (update
  in place if present)
* WP-1.15 changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] CI fails when line coverage of the state machine or lease/sweeper modules drops
  below 85% — Section 18 target; WP-1.15 acceptance second half (NFR-01).
- [ ] The gate measures the modules that exist at M1 and the changelog records the
  Policy Engine portion (85% line, 100% branch on token validation) as enforced at
  WP-3.4 — Section 18, no silent scope reduction.
- [ ] The gate wraps the same four suites (one run, one gate) — Section 19.6.
- [ ] Threshold reproducible locally with the documented command (Section 20.4
  item 1: acceptance proven by test command).
- [ ] CI green on the clean run with gate enabled (Section 20.4 item 2); no secrets
  or environment-specific paths (item 3).
- [ ] Changelog note added (item 7).

## Test command
`pytest backend/tests/concurrency backend/tests/idsempotency backend/tests/auth
--cov=<state-machine-module> --cov=<lease-module> --cov-fail-under=85 -q` — the CI
gate reproduces exactly; plus the per-suite commands from MT-1.15-01 … 04 during
development.

## Attachments
* [Section 18 — Testing strategy and coverage targets](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.15 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 20.4 — Global definition of done](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Path naming for "the state machine" and "lease logic" follows Appendix A's actual
  module layout — resolve the concrete paths from the tree before hardcoding the
  `--cov` arguments; if a module boundary is unclear (leases split across app and
  sweeper), define it once in the coverage config and note the choice in the
  changelog so later WPs do not re-scope it.
* Enforcing Policy Engine coverage at M1 is impossible (WP-3.4 dependency) — the
  deferred note must be explicit or the gate will be misread as claiming M1
  completeness (Section 18).
* Raising coverage thresholds can tempt broad, low-value tests; the plan's target is
  behavioral (state machine and leases), so any test added purely to move the number
  should exercise real transitions — record that guidance in the changelog note.
