# MT-5.10-04 — Define and Document the Distribution Path

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.10-04 |
| Title | Define and document the distribution path |
| Parent WP | WP-5.10 — Mobile release builds and distribution (Milestone M5) |
| Requirements | FR-MOB-06 |
| Priority | M |
| Dependencies | MT-5.10-02 (Android artifact produced), MT-5.10-03 (TestFlight or recorded blocker) |
| Parent sections | 19 (WP-5.10 fourth slice; deliverable "internal distribution"), 16.5 (upgrades), 19 (deliverables), 20.4, 20.5; 22 (OQ-08); 21 (RISK-10) |

## Context
Section 19 (WP-5.10) lists "distribution" as a slice and "internal distribution"
among deliverables; OQ-08 (decided) fixes the path for v1: Android internal build
first, iOS via TestFlight when the developer account is available — no public stores.
This task turns the produced artifacts (and the MT-5.10-01/03 spike facts) into a
written, repeatable path: who gets which build, how they install it, how updates
roll out, and what happens on the iOS branch if it stayed blocked (RISK-10). The
document is what MT-5.10-05's checklist and later the operator guide (MT-6.5-01)
point testers at.

## Inputs / Prerequisites
* MT-5.10-02 — the Android internal artifact and its preflight result.
* MT-5.10-03 — TestFlight steps or the precise iOS blocker record.
* MT-5.10-01 — signing documentation and credential-handling rules.
* Parent plan OQ-08 (decided) — the path this document must reflect.
* Parent plan Section 16.5 — upgrade discipline (pull new build, restart, backward-
  compatible changes) — the mobile analogue: how a newer build replaces an installed
  one without data loss (secure storage survives update; re-login not required unless
  tokens rotate).

## Scope (in)
* A distribution document covering, per platform:
  * **Android:** how the internal release artifact is shared and installed
    (internal/sideload path, unknown-sources note from MT-5.10-02), who the testers
    are, and how a new build is delivered (install-over-the-existing with the same
    signing key — tied to MT-5.10-01's keystore discipline).
  * **iOS:** the TestFlight path (invitees/groups, build upload steps pointer to
    MT-5.10-03's doc) or, if blocked, the explicit current state per OQ-08 and the
    web fallback (responsive web review channel — MT-4.11-01 — as the interim
    review path, per RISK-10's "web fallback for reviews").
  * **Update rollout:** which build testers should run during WP-5.10 verification
    and after v1 (version identity from MT-5.10-02), and the rule that checklist
    results attach to a specific version.
  * **Secrets/credentials:** no signing or store credentials in the document —
    pointers only (Section 20.4 item 3).
* Cross-links: signing doc (MT-5.10-01), build steps (MT-5.10-02/03), the
  real-device checklist (MT-5.10-05), and a pointer target for the operator guide
  (MT-6.5-01).
* Changelog note (Section 20.4 item 7).

## Out of scope
* Producing builds — MT-5.10-02/03. Signing setup — MT-5.10-01.
* Executing the real-device checklist — MT-5.10-05.
* Public store submission flows (Play/App Store) — OQ-08 excludes them for v1.
* Backend/tunnel distribution concerns — Section 15/16 territory (link only).

## Target paths
* `mobile/docs/` — distribution-path document (per-platform install, update and
  rollout rules; blockers recorded)
* `mobile/docs/` — cross-links to signing, build and checklist documents
* WP changelog entry (path chosen, iOS branch status)

## Acceptance criteria
- [ ] The document states the Android internal distribution path end to end:
  artifact → sharing → install → update-over-previous (Section 19 WP-5.10
  "internal distribution"; OQ-08).
- [ ] The iOS path is TestFlight steps or the recorded blocker with the web-fallback
  note — matching OQ-08's conditional wording and RISK-10's fallback mitigation.
- [ ] Update/rollout rules reference version identity from MT-5.10-02 and the
  same-signing-key upgrade constraint (Section 16.5 spirit; MT-5.10-01).
- [ ] No credentials or secrets appear in the document (Section 20.4 item 3).
- [ ] The checklist (MT-5.10-05) and operator guide (MT-6.5-01) both have a
  link target here (traceability, Section 20.5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Documentation review pass: read `mobile/docs/` distribution document against OQ-08's
decided wording and MT-5.10-02/03's recorded facts — confirm every referenced
artifact/version exists or is explicitly marked blocked, grep it for
secret-looking values (expected: none), and confirm the checklist and operator-guide
links resolve.

## Attachments
* [Section 22 — OQ-08 (mobile distribution path)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.10 slices and deliverables](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 21 — RISK-10 (friction + web fallback)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The document must reflect what MT-5.10-02/03 actually achieved — an idealized
  path that never ran is exactly the failure mode this series guards against
  (Section 20.4 item 1); if iOS is blocked, the document says so.
* "Internal distribution" for Android has multiple mechanisms (file share, MDM,
  internal track) — OQ-08 does not pick one; choose the simplest that fits a single
  Owner and record the choice as this task's decision, not as a plan fact.
* Over-specifying future release automation invites scope creep — document the
  manual v1 path only; automation is post-v1 (Section 20.3 splitting).
