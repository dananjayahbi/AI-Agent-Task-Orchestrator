# MT-0.3-04 — Add Dependency and Secret Scanning Gates

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.3-04 |
| Title | Add dependency and secret scanning gates |
| Parent WP | WP-0.3 — CI pipeline (Milestone M0) |
| Requirements | NFR-07, NFR-11 |
| Priority | M |
| Dependencies | MT-0.3-01, MT-0.1-05 (scanner patterns) |
| Parent sections | 12.1, 12.4, 18, 19.1 (WP-0.3), 20.4, 21 (RISK-08, RISK-14) |

## Context
Section 18 lists dependency scanning and secrets scanning among the blocking CI quality
gates, supporting the NFR-07 security baseline (OWASP ASVS Level 1). RISK-08 and
RISK-14 make secret detection a standing control against token/config leaks, with the
pre-commit hooks (MT-0.1-05) as the local first line and CI as the authoritative gate.
This task makes both scans mandatory and merge-blocking.

## Inputs / Prerequisites
* MT-0.1-05 — secret-scan patterns/config to reuse in CI (same scanner preferred).
* MT-0.3-01 — the CI workflow to extend.
* Parent plan Section 18 — "Security: … dependency scanning; secrets scanning".
* Parent plan Section 12.1/12.4 — threat model and data protection context.
* Scanners available to CI: one for Python dependencies (`uv`/pip-audit equivalent),
  one for npm dependencies (npm audit or equivalent), one for secrets (the same
  conservative-pattern scanner used in hooks).

## Scope (in)
* Add a dependency-scan job covering both Python packages (backend, bridge) and the web
  package's npm dependencies; fail on vulnerabilities at or above an agreed severity
  threshold (document the threshold in the workflow notes).
* Add a secrets-scan job running over the full repository history/worktree with the
  conservative patterns and config-file globs from RISK-08.
* Make both jobs required checks so findings block merge (WP-0.3 acceptance).
* Document the update/exception process for a flagged dependency (waivers recorded in
  the workflow notes, never by disabling the gate).
* Add a WP changelog note.

## Out of scope
* Mobile (pub) dependency scanning — add with the real Flutter app (WP-5.5) if the
  chosen scanner supports it; note it as a follow-up rather than silently skipping.
* Optional external/managed secret scanner integration — RISK-08, scheduled M3.
* Full ASVS security review and authorization matrix tests — WP-6.1 / WP-1.15.
* Runtime container CVE scanning — M6 hardening.

## Target paths
* `.github/workflows/` — dependency-scan and secret-scan jobs
* Scanner configuration reused from the root (`gitleaks`-style config if present)
* `CONTRIBUTING.md` or workflow notes — severity threshold and waiver process
* WP changelog entry

## Acceptance criteria
- [ ] A dependency-scan job runs for backend, bridge and web and fails on findings
  above the documented threshold.
- [ ] A secret-scan job runs over the whole repository and fails on any finding.
- [ ] Both are required checks: a PR introducing a leaked credential or a vulnerable
  dependency is blocked from merging (WP-0.3 acceptance).
- [ ] The CI secret scan uses the same pattern source as the pre-commit hook.
- [ ] No real credentials anywhere in workflow files (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the scan jobs on the clean branch and confirm both pass (e.g. `gh run view --log`
shows the dependency and secret scan steps succeeding); on a throwaway branch commit a
file containing a fake credential to confirm the secret-scan gate fails and blocks
merge, then delete the branch without merging.

## Attachments
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.1 — Threat model summary](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* RISK-08: pattern-based scanning misses leaks — pair the gate with human review of
  config changes; keep patterns conservative to avoid noisy false positives that
  pressure people to waive the gate.
* Dependency scanners on a fresh skeleton will find few issues; thresholds must be set
  so the gate stays meaningful as real dependencies arrive in WP-1.1 onward.
