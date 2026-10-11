# M0 Decision Review Session Notes — WP-0.4 (MT-0.4-01)

| Field | Value |
|---|---|
| Session date | 2026-10-11 |
| Format | Unattended, asynchronous review of parent plan Section 22 and Appendix C |
| Scope | Open questions OQ-01..OQ-14 (Section 22); Appendix C checklist items 1–7 |
| Source of truth | `../../ai_agent_task_orchestrator_architecture_plan.md` (Sections 0, 19.1 WP-0.4, 20.4, 22, 23, Appendix C) |
| Downstream consumers | MT-0.4-02 (ADR records), MT-0.4-03 (Section 22 table update) |
| Overrides applied | None — every outcome below confirms the plan's recommended default |

## 1. Session basis (read first)

Per MT-0.4-01's inputs, these are owner decisions; **this session was run unattended, so
it can only confirm the plan's recommended defaults — it cannot deliberate or override
them.** That limitation is stated explicitly here so nothing below is mistaken for a
live owner decision:

* **Confirmed decisions (OQ-01, OQ-02, OQ-03, OQ-04, OQ-06):** the recommended default
  is adopted as the working decision, unblocking M1/M2 per WP-0.4 acceptance. Basis:
  "default confirmed in unattended session, 2026-10-11" — owner ratification requested.
* **Conscious deferrals (all remaining nine OQs):** recorded as deferred with an
  assigned decision milestone equal to the item's "needed by" column. These questions
  are **not settled**; the recommended defaults stay proposals until their milestone.
* **Owner-preference items are deliberately left open:** OQ-14 (dogfooding), OQ-08
  (mobile distribution) and OQ-11 (domain/Cloudflare ownership) are deferrals, not
  silent settlements.
* **ADR conflicts flagged:** none. No outcome below contradicts Section 23, so
  MT-0.4-02 receives zero amendments (Section 5).

## 2. Outcomes for OQ-01..OQ-14

| ID | Outcome | Decision / assigned milestone | Rationale (plan-faithful) | Date |
|---|---|---|---|---|
| OQ-01 | **Decided** (default confirmed) | SSE only for v1; revisit if bidirectional streaming is needed — ADR-002 | SSE gives one-way feeds that are resumable by event id with no gaps or duplicates (Section 9.6) and is proxy/tunnel-friendly; WebSocket via Channels adds machinery no v1 requirement needs. | 2026-10-11 |
| OQ-02 | **Decided** (default confirmed) | DRF with schema generation — ADR-005 | DRF's mature ecosystem for permissions, throttling and schema generation serves the Section 12.2 authorization matrix and the generated OpenAPI contract. | 2026-10-11 |
| OQ-03 | **Decided** (default confirmed) | Default one concurrent task per project; optional per-task worktrees as a later improvement — ADR-013 | Directly mitigates RISK-03 (shared working-tree corruption) and RISK-04 (overlapping-file conflicts) without forcing worktree complexity on every project. | 2026-10-11 |
| OQ-04 | **Decided** (default confirmed) | Liveness pings off by default (explicit checkpoints only, as the spec states); available per project with a hard cap | Keeps lease extension tied to explicit checkpoints under the Section 8.6 hard cap, so a hung agent cannot renew a lease indefinitely; per-project opt-in serves environments that need it. Consistent with ADR-012 (fencing still applies). | 2026-10-11 |
| OQ-05 | **Deferred** | Deferred to M2 | Client verification effort belongs with bridge conformance and per-client guides (RISK-01, WP-2.11); the recommended order (Claude Code → VS Code Copilot → OpenCode, Aider, DeepSeek harness) remains a proposal for the owner to confirm at M2. | 2026-10-11 (deferral recorded) |
| OQ-06 | **Decided** (default confirmed) | Yes — projects without a local merge step are supported via `merge_strategy` set to `manual`: approval marks `completed` without executor involvement — ADR-008 (merge-strategy context) | Keeps the "Completed = merged" invariant (ADR-008) explicit: the manual merge is a recorded owner attestation outside the executor path, configured per project rather than a silent gap. | 2026-10-11 |
| OQ-07 | **Deferred** | Deferred to M1 | Visual descriptions are disabled by default; the provider and monthly budget require an owner spend decision only when a project enables the feature. | 2026-10-11 (deferral recorded) |
| OQ-08 | **Deferred** | Deferred to M5 | Distribution needs accounts, signing and store tooling (RISK-10); the Android-internal-first default stands as a proposal until mobile work starts. Owner decision — not settled now. | 2026-10-11 (deferral recorded) |
| OQ-09 | **Deferred** | Deferred to M1 | Authentication strength lands with WP-1.2 accounts work; "strong password plus optional TOTP, passkeys later" remains the proposal for the owner to confirm or override at M1. | 2026-10-11 (deferral recorded) |
| OQ-10 | **Deferred** | Deferred to M6 | Retention values are enforced by the M6 cleanup jobs; the plan's defaults (events 1 year; checkpoints and patches 180 days after completion; attachments until archive plus 30 days) remain proposals until then. | 2026-10-11 (deferral recorded) |
| OQ-11 | **Deferred** | Deferred to M5 | Requires the owner's domain and Cloudflare account; `orchestrator.<domain>` remains the proposed hostname. Owner decision — not settled now. | 2026-10-11 (deferral recorded) |
| OQ-12 | **Deferred** | Deferred to M5 | v1 mobile scope is review and monitoring only (Could); scope is confirmed with the owner when mobile work starts (RISK-11 context). | 2026-10-11 (deferral recorded) |
| OQ-13 | **Deferred** | Deferred to M5 | Digests off by default with per-event toggles only remains a proposal until the notifications work package ships. | 2026-10-11 (deferral recorded) |
| OQ-14 | **Deferred** | Deferred to M3 | Dogfooding is an owner-preference decision: adopt only after the minimum M3 set exists. **Explicitly open — not settled by this session**; scheduled for M3 per the plan's "needed by" column. | 2026-10-11 (deferral recorded) |

Summary: **5 decided** (OQ-01, OQ-02, OQ-03, OQ-04, OQ-06 — WP-0.4 acceptance
criteria), **9 consciously deferred** with assigned decision milestones identical to
their "needed by" values (OQ-05→M2, OQ-07→M1, OQ-08→M5, OQ-09→M1, OQ-10→M6,
OQ-11→M5, OQ-12→M5, OQ-13→M5, OQ-14→M3). No recommended default was overridden.

## 3. Decisions mapped to ADRs (input for MT-0.4-02)

| OQ | Embodied by | Note |
|---|---|---|
| OQ-01 | ADR-002 (SSE as the primary realtime channel) | Same substance as Section 23. |
| OQ-02 | ADR-005 (DRF with generated OpenAPI as the contract) | Same substance as Section 23. |
| OQ-03 | ADR-013 (optional per-task Git worktrees; default one concurrent task per project) | Same substance as Section 23. |
| OQ-04 | *(no Section 23 ADR)* | Consistent with ADR-012 (idempotency plus lease fencing); no ADR amendment needed. |
| OQ-06 | ADR-008 (host-side Merge Executor; `completed` only after successful merge) — merge-strategy context | `merge_strategy: manual` refines how ADR-008's invariant is satisfied without executor involvement; recorded as context, not as a rewrite of ADR-008. |

## 4. Appendix C checklist — recorded status (items 1–7)

| # | Checklist item | Status |
|---|---|---|
| C-1 | All Section 22 questions marked as decided or consciously deferred | **Satisfied.** All 14 outcomes recorded in Section 2 above; MT-0.4-03 writes them into the Section 22 table with decision and date columns, making the plan self-contained. |
| C-2 | State names, review reasons, and error codes frozen as canonical catalogs (Sections 8.4, 9.2) | **Satisfied — frozen as printed.** This session made no edit to Sections 8.4/9.2; the canonical enums stand as the plan's catalogs (ADR-010 for states). Publishing the conventions document belongs to WP-0.5. |
| C-3 | Policy defaults and glob presets agreed per framework used in the owner's real projects | **Deferred to WP-3.1 (M3).** Plan-level policy defaults exist (Section 9, R1–R9), but framework glob presets need the owner's real projects; owner input required when WP-3.1 runs. |
| C-4 | Priority clients for compatibility testing confirmed | **Deferred to M2 (OQ-05).** Recommended verification order recorded in Section 22; owner confirms at M2. |
| C-5 | Hostnames, domain, and Cloudflare account ready (needed before M5) | **Deferred to M5 (OQ-11).** Owner supplies the domain; hostname proposal `orchestrator.<domain>` recorded. Early preparation noted as cheap but still owner-owned. |
| C-6 | Execution order in Section 20.6 accepted | **Accepted.** Confirmed consistent with the micro-document series roadmap (`plan-doc-series/roadmap.md`, Wave 1 = M0 in full first); unattended default-confirmation — owner ratification requested. |
| C-7 | Decision on dogfooding the orchestrator for its own development (OQ-14) | **Open — assigned milestone M3 (OQ-14).** Deliberately not settled by this session; re-decide after the minimum M3 set exists. |

## 5. Amendments flagged for MT-0.4-02

**None.** Every recorded outcome confirms (rather than contradicts) Section 23's ADR
substance, so no ADR amendment is required. If the owner later overrides any confirmed
default during ratification, that override must be processed as an explicit amendment
in the affected ADR — not as a silent rewrite.

## 6. Changelog reference

This session's outcome is recorded in the WP changelog at
`../../plan-doc-series/m0-foundations/wp-0.4-decision-records/CHANGELOG.md`
entry "MT-0.4-01" (parent plan Section 20.4, item 7).
