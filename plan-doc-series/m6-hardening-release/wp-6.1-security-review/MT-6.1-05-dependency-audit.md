# MT-6.1-05 — Run the Dependency Audit and Remediate Findings

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.1-05 |
| Title | Run the dependency audit and remediate findings |
| Parent WP | WP-6.1 — Security review (Milestone M6) |
| Requirements | NFR-07 |
| Priority | M |
| Dependencies | MT-0.3-04 (CI dependency and secret scan gates), MT-6.1-01 (findings log); M1–M5 dependency sets frozen (Section 19 WP-6.1 dependency) |
| Parent sections | 12.1 (malicious uploads: sandboxed parsing context), 18 (Quality gates: dependency and secret scans), 19 (WP-6.1 goal and acceptance), 20.4 (item 2), 20.5 |

## Context
Section 18's quality-gate list includes dependency scanning for every CI run, and
Section 19 (WP-6.1) requires the full review to end with "no open high or critical
findings". This closing slice runs the dependency audit across all four packages —
backend (Python), bridge (Python/uv), web (npm) and mobile (pub) — plus infra
images, remediates what can be remediated, and records what cannot, so the WP's
findings log closes at zero open critical/high. NFR-07 (ASVS Level 1) includes the
"use no software with known vulnerabilities" discipline the plan's gates encode.

## Inputs / Prerequisites
* MT-0.3-04 — the CI security gates (dependency and secret scans) already wired in
  WP-0.3; this task runs them at full review depth and acts on results.
* Dependency manifests for backend, bridge, web, mobile (Appendix A layout) and the
  pinned container images in `infra/compose/` (Section 16.1).
* MT-6.1-01 — findings log, severity scale (critical/high per advisory severity
  mapped to the log's scale) and the mapping to close out.
* Section 20.4 item 2 — lint/type/tests green after any remediation bump.

## Scope (in)
* Run the dependency audit for each package with the project's scanner (the same
  family CI uses) and capture results: direct and transitive advisories with
  severity per package.
* Remediate by upgrading within the ranges the plan allows:
  * Patch/minor upgrades that keep contracts stable — apply and run the affected
    package's lint, type check and tests (Section 20.4 item 2).
  * Major upgrades required for a high/critical fix — weigh against scope creep
    (Section 20.3: keep it separate from features); if taken, they get their own
    changelog entry and full package test run.
  * No fix available (or fix would break the OpenAPI/client contract, NFR-11) —
    record an accepted-risk entry in the findings log with severity, justification
    and a follow-up owner; accepted risks for critical/high require the explicit
    justification text in the log.
* Confirm the CI gates would now pass clean (or only carry the logged accepted
  risks), and record infra image updates if base images were bumped (Section 16.1
  pinned images).
* Append results to the threat-to-test mapping (dependency-scanning row from
  Section 18) and close this slice's findings.
* Changelog note (Section 20.4 item 7).

## Out of scope
* The secret-scan half of the gates — MT-6.1-04 owns secrets (this task only uses
  the same CI machinery for dependencies).
* Adding new scanning products beyond what WP-0.3 wired — tool upgrades are a
  follow-up if the existing gate is inadequate (note it, don't scope-creep).
* Runtime/OS patching of the VPS host — MT-6.6-01's provisioning scope (record a
  pointer if the audit reveals a host-level item).
* The other review slices — MT-6.1-01/02/03/04 (shared log only).

## Target paths
* Dependency manifests (`backend/`, `bridge/`, `web/`, `mobile/`) — version bumps
  where remediation requires them
* `infra/compose/` — base image pins if images were updated (Section 16.1)
* `docs/plan/security-findings-log.md` (advisories, remediations, accepted risks)
* `docs/plan/security-threat-test-mapping.md` (dependency row updated)
* WP changelog entry (upgrades applied, accepted risks)

## Acceptance criteria
- [ ] All four packages plus infra images audited; results recorded with severities
  (Section 18 quality gates; Section 19 WP-6.1 goal).
- [ ] Every critical/high advisory is either fixed (upgrade applied, tests green)
  or present in the findings log as an accepted risk with justification and owner —
  zero open unaddressed critical/high (Section 19 WP-6.1 acceptance).
- [ ] Contract stability preserved after upgrades: schema diff check and generated
  clients still pass (Section 20.4 item 4; NFR-11).
- [ ] CI dependency gate passes with only the logged accepted risks remaining
  (Section 20.4 item 2).
- [ ] Changelog note added with applied upgrades and accepted risks (Section 20.4
  item 7).

## Test command
Run the CI dependency scan across backend, bridge, web and mobile (the WP-0.3
security-gate job) and confirm zero unaddressed critical/high advisories; then run
each upgraded package's lint/type/test selector to green and the schema-diff check
(Section 20.4 items 2 and 4).

## Attachments
* [Section 18 — Testing and Quality Strategy (quality gates)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.1 goal and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.1 — Compose services (pinned images)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Remediation near release can destabilize more than it fixes — prefer patch-level
  bumps; anything major gets the Section 20.3 discipline (separate task, full tests)
  rather than a rushed in-place rewrite.
* Accepted-risk entries are the honest escape valve but can rot — each needs an
  owner and a revisit note, or the findings log becomes a graveyard instead of a
  review record (WP acceptance depends on the log's credibility).
* Advisory severity scales differ per ecosystem — normalize to the findings log's
  scale (defined in MT-6.1-01) before deciding what counts as high/critical.
