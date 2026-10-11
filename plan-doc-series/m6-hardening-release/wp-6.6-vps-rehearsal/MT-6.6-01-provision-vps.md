# MT-6.6-01 — Provision the VPS Host with Container Runtime

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.6-01 |
| Title | Provision the VPS host with container runtime |
| Parent WP | WP-6.6 — VPS migration rehearsal and v1 release (Milestone M6) |
| Requirements | NFR-06, GOAL-5 |
| Priority | M |
| Dependencies | WP-6.1 to WP-6.5 complete (Section 19 WP-6.6 dependency), WP-0.2 (env template), MT-6.5-01 (operator guide as the script being followed) |
| Parent sections | 1.2 (GOAL-5), 1.4 (success criterion 5), 5.2 (NFR-06), 16.1 (Compose services), 16.2 (config/secrets on a VPS), 16.4 (VPS migration checklist, step 1), 19 (WP-6.6), 20.4, 20.5; 21; Appendix A |

## Context
Section 16.4 is the checklist for GOAL-5: step 1 is "Provision host, install container
runtime, copy environment file with changed hostnames and storage settings."
Section 19 (WP-6.6): goal "Prove GOAL-5 and tag v1", deliverables "rehearsal log,
fixes, release notes, tag", acceptance "success criterion 5 in Section 1.4 met" —
"The full stack is moved from the laptop to a VPS by changing environment
configuration only (no code or compose edits)." This first slice is the
provisioning step of the rehearsal and, critically, the start of the rehearsal log
that accumulates evidence for the whole WP. The constraint that makes or breaks the
WP is already stated: config-only — so every deviation discovered while provisioning
is a finding to fix, not a workaround to accept.

## Inputs / Prerequisites
* Parent plan Section 16.4 — checklist step 1 verbatim; the procedure this rehearsal
  executes end to end across MT-6.6-01 … 04.
* Parent plan Section 16.1 — the exact services, volumes and health checks that must
  come up on the VPS (same Compose topology — NFR-06 "identical Compose stack").
* Parent plan Section 16.2 — secrets on a VPS use the host's secret mechanism or
  Compose secrets, same variable names everywhere (NFR-06).
* Parent plan Section 1.4 criterion 5 — the config-only acceptance bar; any code or
  Compose edit required is a blocking finding.
* MT-6.5-01 — the operator guide; the rehearsal deliberately runs *from the docs*,
  which also tests WP-6.5's acceptance.
* MT-6.2-01/02/03 — backups in the second location that MT-6.6-02 will restore.
* MT-6.1-05 note: runtime/OS patching of the VPS host is in this task's provisioning
  scope (recorded there as this task's responsibility).

## Scope (in)
* Provision the host: a Linux VPS with a container runtime capable of running the
  Section 16.1 Compose stack (Docker/Compose equivalent), OS/runtime patching
  applied and recorded (per MT-6.1-05's handoff).
* Copy the environment file to the VPS with only environment-level changes:
  changed hostnames and storage settings per Section 16.4 step 1; secrets placed via
  the host secret mechanism or Compose secrets (Section 16.2) — never committed,
  never pasted into logs.
* Enforce the no-public-ports posture from the start: only `web` and `backend`
  publish to the LAN interface by default; remote access will arrive via the tunnel
  in MT-6.6-03 (Sections 16.1, FR-NET-01).
* Start the stack and reach green health checks for the Section 16.1 services
  (readiness probes pass) — the stack must be provably identical to local
  (NFR-06): same services, same wiring, environment-only differences.
* Open the rehearsal log (`docs/plan/`): host facts (provider/region/runtime
  versions — no secrets), steps executed, deviations found, time stamps; this is the
  WP-6.6 "rehearsal log" deliverable's first entries and where "fixes" are tracked.
* Changelog note (Section 20.4 item 7).

## Out of scope
* Restoring database or media backups — MT-6.6-02 (checklist step 2).
* Tunnel, manifests, agent tokens — MT-6.6-03 (steps 4–5).
* Smoke test suite — MT-6.6-04 (step 6).
* Release notes and the v1 tag — MT-6.6-05.
* Any code, Compose or template edit "needed to make it work" — if provisioning
  requires one, stop and log it as a blocking finding for the plan owner (Section
  1.4 criterion 5); this task fixes nothing outside environment configuration.
* Choosing the VPS provider or paying accounts — owner-provided host (Section 20.1
  principle 5: the choice is the owner's; record it, don't make it).

## Target paths
* `docs/plan/` — rehearsal log (created here; appended by MT-6.6-02 … 05)
* Host environment (outside Git) — environment file copy with changed hostnames and
  storage settings (Section 16.4 step 1)
* WP changelog entry

## Acceptance criteria
- [ ] A Linux VPS with container runtime runs the Section 16.1 stack with all
  service health checks green (Section 16.4 step 1; NFR-06 identical stack).
- [ ] The only changes made were environment-level: hostnames and storage settings
  per Section 16.4 step 1, secrets via Section 16.2 mechanisms — zero code or
  Compose edits (Section 1.4 criterion 5; Section 20.4 item 3).
- [ ] No inbound public ports are open beyond the LAN-by-default posture; tunnel
  not yet required (FR-NET-01; Section 16.1).
- [ ] OS/runtime patching performed and recorded (MT-6.1-05 handoff).
- [ ] The rehearsal log exists with provisioning steps, host facts (no secrets),
  and any deviations logged as findings (Section 19 WP-6.6 deliverable "rehearsal
  log"; Section 20.4 item 1).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
On the VPS, run the documented health checks for every Section 16.1 service (Compose
health status green; `/health/live` and `/health/ready` responding) and confirm via
`git status`/diff on the repo checkout that no tracked file differs from the laptop
build (config-only proof); review the rehearsal log for completeness and zero
secrets.

## Attachments
* [Section 16.4 — VPS migration checklist (GOAL-5)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 1.4 — Success criteria (criterion 5)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [NFR-06 — Portability](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The config-only bar is decided by small omissions — a hardcoded hostname, a
  Windows path, a laptop-only volume name surfacing only at runtime. Hunt them by
  actually starting every service; each one found is a WP-6.6 "fix" deliverable
  (RISK-15's host-path family), and hiding one to keep the rehearsal green defeats
  GOAL-5.
* Provisioning steps vary by provider and are not in the plan — keep provider
  specifics in the rehearsal log as facts, not in repo docs (no environment-specific
  paths committed, Section 20.4 item 3).
* A fresh internet-exposed host is a security-sensitive moment: patch before
  starting the stack, publish only LAN-default ports, and never write secrets into
  the rehearsal log or shell history (Section 12.4; Section 20.4 item 3).
* If the VPS cannot be provisioned in-session (account/billing), that is a blocking
  dependency, not a partial pass — record it in the log and stop the WP rather than
  simulating the rehearsal.
