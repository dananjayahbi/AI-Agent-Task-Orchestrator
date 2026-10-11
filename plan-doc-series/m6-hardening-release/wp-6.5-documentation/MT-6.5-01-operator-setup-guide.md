# MT-6.5-01 — Write the Operator Setup Guide

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.5-01 |
| Title | Write the operator setup guide |
| Parent WP | WP-6.5 — Documentation and runbooks (Milestone M6) |
| Requirements | all (per Section 19 WP-6.5; primarily NFR-06, NFR-11) |
| Priority | M |
| Dependencies | WP-0.2 (env template and Compose bring-up), WP-5.10 (distribution docs per MT-5.10-04 pointer), WP-6.2 (backup docs to link), M1–M5 features to document (Section 19 WP-6.5 dependency) |
| Parent sections | 9.10 (configuration), 16.1 (Compose), 16.2 (config/secrets), 16.4 (VPS checklist), 16.5 (upgrades/rollback), 19 (WP-6.5 goal, deliverables, acceptance), 20.4, 20.5; Appendix A |

## Context
Section 19 (WP-6.5): goal "Operator and user documentation", deliverables "setup
guide, agent client guides, runbooks (Section 17), upgrade and rollback guide",
acceptance "someone following only the docs can stand up the stack, onboard a repo
and connect an agent." This first slice writes the operator setup guide — the spine
of that acceptance — covering bring-up from a fresh clone through configuration,
secrets, health checks, upgrades and rollback. Later slices (agent guides, runbooks,
troubleshooting) attach to it; WP-5.10's distribution doc (MT-5.10-04) explicitly
left a pointer target for this guide to link.

## Inputs / Prerequisites
* Parent plan Section 16.1 — the Compose service table (images, ports, volumes,
  health checks, profiles `dev`/`prod`) the bring-up narrative must follow.
* Parent plan Section 16.2 — one documented environment template, real values
  outside Git, prod startup validation for weak/missing secrets.
* Parent plan Section 9.10 — the configuration groups with documented defaults and
  fail-fast startup validation to describe.
* Parent plan Section 16.5 — upgrade procedure (pull images, run migrate, restart;
  backward-compatible `/v1`; API version header warnings) and rollback (previous
  image tags retained; reversible migrations) — the guide's upgrade/rollback chapter
  is the WP-6.5 "upgrade and rollback guide" deliverable.
* WP-0.2's README (bring-up/tear-down) and the environment template — source
  material to consolidate, not duplicate blindly.
* MT-6.2-03/04 — backup schedule and restore procedure links for the
  operations section.
* MT-5.10-04 — mobile distribution path, which left an explicit pointer for this
  guide.

## Scope (in)
* Write the operator setup guide under `docs/` (location recorded in risk notes —
  Appendix A reserves `docs/plan/`, `docs/adr/`, `docs/runbooks/`,
  `docs/agent-guides/`): prerequisites, fresh-clone bring-up (one documented command
  path per WP-0.2 acceptance), environment template walkthrough (Section 9.10
  groups, Section 16.2 secrets rules), service-by-service health verification
  (Section 16.1 health checks, `/health/live`, `/health/ready`), profiles
  (`dev`/`prod`), and tear-down with data-preservation notes.
* Include the upgrade and rollback chapter per Section 16.5 (this is WP-6.5's
  named deliverable): image pull + migrate + restart flow, API version-header
  compatibility note, rollback to previous image tags, and the reversibility caveat
  for migrations.
* Include the VPS pointer: Section 16.4's checklist summarized with a pointer to the
  parent plan (NFR-06/GOAL-5 readers), and links to WP-6.2's backup/restore docs
  and MT-5.10-04's distribution path.
* Keep every command and path generic — no host-specific paths, no real secrets
  (Section 20.4 item 3); commands are documented as the single documented path
  rather than scattered alternatives.
* Cross-link from `README.md`/`CONTRIBUTING.md` (the MT-0.1-06 doc tree) and add a
  changelog note (Section 20.4 item 7).

## Out of scope
* Per-client agent connection steps — MT-6.5-02 (the guide links to them; the
  acceptance's "connect an agent" leg is theirs).
* The seven Section 17 runbooks — MT-6.5-03 (guide links, does not absorb).
* Troubleshooting decision trees — MT-6.5-04.
* Writing or changing the environment template itself — WP-0.2 deliverable; the
  guide documents it as-is and flags gaps rather than editing config.
* Rewriting parent plan sections — Section 0 single source of truth; gaps become
  plan-update suggestions in the changelog.

## Target paths
* `docs/` — operator setup guide (with upgrade and rollback chapter)
* `README.md` / `CONTRIBUTING.md` — link to the guide
* WP changelog entry (including any plan-update suggestions)

## Acceptance criteria
- [ ] A single operator guide exists covering prerequisites through bring-up,
  configuration/secrets (Sections 9.10/16.2), health verification (Section 16.1),
  profiles and tear-down — WP-6.5 deliverable "setup guide".
- [ ] The guide contains the upgrade and rollback chapter from Section 16.5 —
  WP-6.5 deliverable "upgrade and rollback guide".
- [ ] Following only the guide, the bring-up steps were actually executed against a
  clean environment and matched reality at every step (Section 19 WP-6.5 acceptance
  first leg: "stand up the stack"; Section 20.4 item 1).
- [ ] Links land for MT-5.10-04's distribution path, WP-6.2 backup/restore docs, and
  the MT-6.5-02/03/04 siblings (Section 20.5 traceability).
- [ ] No secrets, real tokens or environment-specific host paths appear (Section
  20.4 item 3).
- [ ] Guide reachable from README/CONTRIBUTING; changelog note added (item 7).

## Test command
Perform a dry run of the guide's bring-up commands against a clean checkout/Compose
project and confirm every documented step produces its stated result (services
healthy, `/health/ready` responding); grep the guide for secret-shaped strings and
absolute host paths (expected: zero matches), and confirm the upgrade/rollback
chapter cites Section 16.5's steps.

## Attachments
* [Section 16 — Infrastructure and Deployment](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.5 goal, deliverables, acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.10 — Configuration (environment-driven)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Appendix A reserves no general `docs/` guide location — choose one (e.g. alongside
  the plan under `docs/plan/` or a top-level `docs/setup.md`), record the choice in
  the changelog, and link it from the doc-tree READMEs; do not invent a new
  undocumented docs area silently (same discipline MT-6.1-01 applied).
* The guide must be executed, not just written — an untested setup guide fails
  WP-6.5's acceptance on first contact; the dry-run requirement above is the
  guardrail.
* Duplicate sources drift: the guide consolidates pointers (WP-0.2 README, env
  template comments, parent plan sections) rather than copying values that can go
  stale; where it must restate a default, cite the parent section (Section 20.5).
* If a step cannot be documented without a real secret or account (Cloudflare
  account, FCM credentials), document the shape and the dashboard reference only
  (Section 16.2; MT-0.5-01 env discipline).
