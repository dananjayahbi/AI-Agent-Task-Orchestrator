# Security threat-to-test mapping — WP-6.1 deliverable (MT-6.1-01)

| Field | Value |
|---|---|
| Document | Threat-to-test mapping for parent plan Section 12.1 / 12.2 / 12.3 / 12.5 (Section 19 WP-6.1 deliverable; Section 18 Security row) |
| Created by | MT-6.1-01 (authorization review slice) |
| Appended by | MT-6.1-02 (upload abuse — done), MT-6.1-03 (token lifecycle — done), MT-6.1-04 (secrets & logs — done), MT-6.1-05 (dependency audit — done; all rows flipped) |
| Companion | [`security-findings-log.md`](./security-findings-log.md) (severity scale + findings; every gap named here that is not a passing test appears there) |
| Sources | `ai_agent_task_orchestrator_architecture_plan.md` Sections 12.1–12.5, 15.2/15.3 (by pointer), 18, 19; ADR-004, ADR-006 |

**Legend** — Verification cell: `file::test` = asserted in CI (backend unit layer unless noted);
`file` (no `::`) = the whole suite covers the row; `integration:` = CI integration job (real
Postgres, excluded from the unit baseline); `mobile:` = Flutter test; `review:` = documented
artifact inspected by this review, no executable assertion (honest coverage, never silently
claimed); `LIMITATION` = parent-plan accepted limitation (Section 12.3), detection not prevention.

---

## 1. Section 12.1 — twelve threats, one row each

| # | Threat (12.1) | Verification | Slice / status |
|---|---|---|---|
| 1 | Cross-project leakage (agent asks for another project's tasks) | `backend/tests/test_authorization_matrix.py::test_pid00001_agent_token_is_forbidden_on_pid00002_resources`, `::test_cross_project_guard_on_the_real_projects_registry`, `::test_body_supplied_project_id_cannot_widen_the_token_scope`; `backend/tests/test_permission_classes.py` (scope read from token+URL, never body); `backend/tests/events/test_event_authorization.py::test_cross_project_events_never_reach_a_filtered_connection`; bridge has no project parameter — `bridge/tests/test_project_mismatch.py` (manifest/project mismatch aborts scrubbed) | MT-6.1-01 — covered by tests (FR-SEC-01; ADR-004) |
| 2 | Duplicate/competing work (two agents claim one task) | `backend/tests/test_claim_transaction.py` (row-lock claim), `backend/tests/test_lease_fencing.py` (fencing generation), `backend/tests/test_concurrency_limit.py`, `backend/tests/test_voluntary_release.py`; `backend/tests/integration/test_claim_race_postgres.py` (parallel claim attempts + same-`Idempotency-Key` race — Section 18 concurrency layer) | MT-6.1-01 — covered by tests (FR-LEA-01) |
| 3 | Out-of-scope edits (agent edits unrelated files) | `backend/tests/test_scope_check.py` (submissions vs `target_scope`), `backend/tests/test_policy_rules_r1_r2.py` (R2 patch scope at audit), `backend/tests/test_patch_parsing.py`, `backend/tests/test_patch_artifacts.py` (stored patch, not agent's word); audit/escalation detection: `backend/tests/test_audit_report.py`, `backend/tests/test_escalation_reasons.py` | MT-6.1-01 — covered by tests + **LIMITATION** row 1 below (audit-time detection; Section 12.3) |
| 4 | Prompt injection via attachments/repo ("ignore previous instructions") | `backend/tests/attachments/test_untrusted_banner.py` (P10 untrusted banner), `backend/tests/attachments/test_document_extraction.py` + `test_image_pipeline.py` (extracted text is data — never executed; review); mandatory human review for scope violations: `backend/tests/test_review_endpoint.py`, `backend/tests/test_policy_transitions.py` | MT-6.1-01 — covered by tests + review (FR-RSK chain; RISK-07) |
| 5 | Agent misreporting (coder claims tests passed) | Auditor re-runs independently: `backend/tests/test_auditor_independence.py` (G-20), `backend/tests/test_audit_verdict.py` (verdict + evidence contract); Policy Engine uses evidence and the stored patch: `backend/tests/test_policy_evaluator.py`, `backend/tests/test_policy_rules_r1_r2.py` … `test_policy_rules_r8_r9.py`, `backend/tests/test_policy_transitions.py` | MT-6.1-01 — covered by tests |
| 6 | Self-approval (same agent audits own work) | `backend/tests/test_auditor_independence.py` (`AUDITOR_SAME_AS_CODER` on session **and** label; verdict POST refused, no report stored), `backend/tests/test_auditor_role_gating.py` | MT-6.1-01 — covered by tests |
| 7 | Token theft (leaked agent token) | Hash-at-rest: `backend/tests/test_api_token_model.py`, `backend/tests/test_device_token_binding.py::test_token_material_is_hashed_at_rest`, `backend/tests/test_owner_session_auth.py::test_auth_secrets_are_never_stored_in_plaintext`, `backend/tests/test_token_lifecycle.py::test_no_plaintext_token_value_survives_in_the_database` (all three kinds; derived 64-hex form only); revocation: `backend/tests/test_authorization_matrix.py::test_revoked_agent_token_fails_on_its_very_next_request` (+ device/owner twins), `backend/tests/test_device_revocation.py` (incl. SSE stream reconnect), `backend/tests/test_token_lifecycle.py::test_revoked_agent_token_is_rejected_on_its_next_request` / `::test_revoked_device_is_rejected_on_its_next_request`; expiry: `backend/tests/test_token_lifecycle.py::test_expired_agent_token_is_rejected_on_its_next_request` (+ device/owner twins; configured lifetimes pinned: 12 h / 720 h / 90 d); scoping + kind separation: row 1 tests, `backend/tests/test_token_lifecycle.py::test_agent_token_touches_only_its_own_project`, `::test_body_supplied_project_cannot_widen_the_token_scope`, `::test_kind_separation_*`, `::test_the_token_kind_catalog_stays_closed_at_three`, plus `backend/tests/test_device_token_binding.py::test_edge_identity_headers_alone_grant_nothing`; rate limiting: row 8; bridge storage redaction: `bridge/tests/test_config.py::test_agent_token_is_redacted_in_repr`, `bridge/tests/test_init_selftest.py` | MT-6.1-03 — covered by tests (`backend/tests/test_token_lifecycle.py`, 15); OQ-16 audit gap → findings log F-01 (pinned by `::test_token_audit_events_stay_pinned_to_the_oq16_catalog_gap`); biometric release is client-side by design (ADR-006) — `mobile/test/security/auth_gate_test.dart` + `lock_gate_test.dart` <!-- pragma: allowlist secret --> |
| 8 | Public exposure (backend reachable from internet) | Deny-by-default tunnel allowlist + catch-all 404 + ingress ordering + no committed hostname/secret: `backend/tests/test_route_allowlist_coverage.py` (MT-5.2-02); edge policy as code: `infra/cloudflare/access-policy.md` (MT-5.2-01); execution checklist: `infra/cloudflare/route-verification-checklist.md` (MT-5.2-04 — local half executed 96/96; **live half operator-pending**, Cloudflare account) | MT-6.1-01 — covered by tests + review; live edge application → findings log F-03 <!-- pragma: allowlist secret --> |
| 9 | Lost phone (mobile token abused) | `backend/tests/test_device_revocation.py` (revoked device rejected on next request **and** SSE stream reconnect; only the owning owner revokes; idempotent), `backend/tests/test_device_token_binding.py` (per-registration bound credential; token without a live device row authenticates nowhere); biometric gate (device-local layer, ADR-006): `mobile/test/security/auth_gate_test.dart`, `mobile/test/security/lock_gate_test.dart` | MT-6.1-01 — covered by tests (WP-5.3 acceptance re-verified) |
| 10 | Malicious uploads (weaponized PDF) | Type sniffing + size caps: `backend/tests/attachments/test_upload_validation.py` (content decides; declared-type mismatch rejected; over-limit refused), `backend/tests/attachments/test_upload_endpoint.py` (415 `ATTACHMENT_UNSUPPORTED_FORMAT`, canonical envelope, no storage on rejection); **abuse suite (this WP)**: `backend/tests/attachments/test_upload_abuse.py` — raw/encoded/absolute/symlink-style traversal names normalized and content-keyed (no write outside the root; empty normalization refused), oversized refused with no partial artifact and no worker hand-off, spoofed MIME (ELF-as-image, image-as-document, octet-stream smuggling) rejected 415 by sniffing, client header never trusted; worker-vs-web parsing separation asserted by configuration (enqueue seam → Celery `attachments.process_attachment`; no inline parsing); content-addressed storage guard: `backend/tests/attachments/test_storage.py` | MT-6.1-02 — covered by tests (WP-6.1 "traversal tests in CI"); cosmetic `..` label → findings log F-05; AV + OS sandbox → LIMITATION rows 2–3 |
| 11 | Secrets in diffs (API key committed by agent) | R5 pattern scan over the **stored patch's** added lines (absent patch fails closed): `backend/tests/test_policy_rules_r3_r4_r5.py`; escalation to human review: `backend/tests/test_policy_transitions.py` (`audit.escalated`), `backend/tests/test_escalation_reasons.py`; repository scan gate: `.github/workflows/security.yaml` (detect-secrets over every tracked file; same hook as pre-commit) — **MT-6.1-04 executed it clean** over the whole worktree plus this WP's new files; log-side scrubbing: `backend/tests/test_log_scrubbing.py` (9) + `bridge/tests/test_logging.py` redaction cases (4) — see rows in Section 3.5 below | MT-6.1-04 — covered by tests + executed gate (RISK-08/14 retired for this review) |
| 12 | Replay/duplication (retried POST) | `Idempotency-Key` replay asserted per mutating route: `backend/tests/test_task_api.py`, `test_claim_release_endpoints.py`, `test_resolution_submission.py`, `test_audit_verdict.py`, `test_review_endpoint.py`, `test_merge_queue.py`, `test_checkpoint_endpoint.py`, `test_device_registration_surface.py`, `test_agent_session_endpoints.py`; same-key concurrency: `backend/tests/integration/test_idempotency_postgres.py`, `integration/test_claim_race_postgres.py` | MT-6.1-01 — covered by tests (ADR-012; NFR-12) |

## 2. Section 12.3 — honest limitations (audit-time detection, not prevention)

| # | Limitation (12.3) | Status | Verification |
|---|---|---|---|
| L1 | The agent's own file tools can still touch the disk — scope is enforced at audit, not prevented at runtime | **LIMITATION — accepted by plan; audit-time detection** | Detection chain tested: row 3 tests (R2 patch scope, scope check) + mandatory human review (`test_review_endpoint.py`) + advisory rules (`test_policy_rules_*`) |
| L2 | OS-level sandboxing/containers for agent processes — Could, post-v1 | **LIMITATION — no v1 control; recorded (MT-6.1-02)** | Not tested (no control exists). Worker-vs-web process separation — the v1 control — asserted by configuration in `test_upload_abuse.py::test_web_request_defers_parsing_to_the_worker_task` / `::test_the_enqueue_seam_targets_the_celery_worker_job` |
| L3 | Optional antivirus on attachments — optional in 12.1, not a v1 requirement | **LIMITATION — absent; recorded (MT-6.1-02)** | Not tested (no control exists); sniffing + size + sandbox-by-worker are the shipped mitigations (row 10) |

## 3. Section 12.5 — audit-trail properties

| Property | Verification |
|---|---|
| State-changing actions write Event rows with actor and correlation id | `backend/tests/events/test_event_writes.py` (service paths: transitions, claims, task/project CRUD, policy edit scope) + `backend/tests/test_security_authorization_review.py::test_state_changing_api_call_records_actor_and_correlation_id` (API path: actor **and** the client-seen `X-Correlation-ID` stored verbatim) |
| Per-site emissions (checkpoint, lease warning, attachment, audit, review, merge, alerts) | `backend/tests/events/test_event_catalog.py` (catalog pinned to Section 9.6 — 24 types, no invention) + per-suite emission assertions: `test_checkpoint_endpoint.py`, `test_lease_expiring_warning.py`, `attachments/test_pipeline_entry.py`, `test_policy_transitions.py`, `test_review_endpoint.py`, `test_merge_queue.py`, `test_alerts.py` |
| The audit viewer is read-only (no mutation path) | `backend/tests/test_security_authorization_review.py` (URLConf exposes only the two read routes; no mutation handler on either view; unsafe methods refuse through the catalog envelope with **zero** rows written) |
| The application DB role cannot update or delete audit rows | `backend/tests/events/test_insert_only_permissions.py` (trigger-guarded UPDATE/DELETE denied on `events_event` and `tasks_tasktransition` with raw SQL bypass attempts; INSERT/SELECT keep working; idempotent setup) |
| Login and token events | **GAP — OQ-16**: Section 9.6 has no `token.*`/`login.*` type, so logins/token actions write no Event row; catalog-first (Section 20.4 item 5) forbids inventing one. `test_event_catalog.py::test_no_token_or_login_type_was_invented` pins the gap honestly. → findings log **F-01** (owner decision required) |

## 4. Sections 12.4 / 17 — data protection and logging (MT-6.1-04)

| Property | Verification |
|---|---|
| No token/password/credential/FCM/tunnel credential or Authorization header value in any backend/worker/bridge log line (RISK-14) | `backend/tests/test_log_scrubbing.py` (9): login success+failure, token issuance, device registration, agent-request and attachment-upload flows captured through the production `JsonFormatter` at DEBUG; probes built from the redactor's own registered key names (`apps/core/scrub.py`), never a drifting copy; bridge twin `bridge/tests/test_logging.py` redaction cases (4, `-k redaction`), incl. every registered secret key/suffix, every level, and exception tracebacks |
| Attachment text truncated (no full OCR/extracted content, even at DEBUG) | `backend/tests/test_log_scrubbing.py::test_attachment_upload_logs_carry_no_bytes_and_truncate_excerpts` + `backend/tests/test_logging.py::test_attachment_text_is_truncated`; upload request lines never echo the body or filename |
| Exception/error paths scrubbed (stack traces) | `backend/tests/test_log_scrubbing.py::test_exception_tracebacks_are_scrubbed_on_the_error_path` (crashing view → scrubbed traceback, `[REDACTED]`, correlation id kept) + `bridge/tests/test_logging.py::test_redaction_applies_to_exception_tracebacks`; `backend/tests/test_logging.py::test_error_envelope_carries_correlation_id_and_scrubs_details` |
| Correlation ids remain present after scrubbing (NFR-10) | Asserted on every flow above (`X-Correlation-ID` round-trip preserved; the join key survives scrubbing) |
| Request logs carry no headers/body fields | `backend/tests/test_log_scrubbing.py::test_request_logging_carries_no_headers_or_body_fields` (middleware line shape cannot hold a credential) |
| Repository secret scan (Section 18 gate; FR-SEC-04) | CI gate `.github/workflows/security.yaml` + `.pre-commit-config.yaml` (detect-secrets over every tracked file) — **executed clean by MT-6.1-04** (full worktree + this WP's new files; fixture secrets carry `# pragma: allowlist secret`) |
| R5 diff-pattern scan feeding escalation (Section 12.1) | Row 11 (by pointer — WP-2.10/Policy Engine territory) |

## 5. FR-SEC-05 — rate limiting on agent and device endpoints

| Layer | Verification |
|---|---|
| API | `backend/tests/test_rate_limiting.py` (over-limit → 429 `RATE_LIMITED` envelope; per-token budget keying; window reset; **every** Section 9.2 Agent/Auditor/Bridge/Mobile route enumerated and throttle-pinned; Owner rows asserted unthrottled — FR-SEC-05 scope) + `backend/tests/test_authorization_matrix.py::test_rate_limit_burst_on_a_device_endpoint_returns_rate_limited` + `backend/tests/test_security_authorization_review.py::test_device_endpoint_trips_rate_limited_within_the_review` / `::test_agent_endpoint_trips_rate_limited_within_the_review` (both halves inside the WP-6.1 review command) |
| Edge | `infra/cloudflare/rate-limits.md` + `backend/tests/test_rate_limits_tunnel.py` (MT-5.2-03 — defined as code; local half executed; live application operator-pending → findings log F-03). Owner-auth is **deliberately edge-only** (E1 30/min/IP; FR-SEC-05 covers agent/device endpoints) — pinned by `test_rate_limiting.py::test_owner_session_endpoints_are_not_throttled` |

## 6. Section 12.2 — matrix cell coverage (FR-SEC-01/02; ADR-004/ADR-006)

| Assertion | Verification |
|---|---|
| Every cell (10 capabilities × 6 actors, plus anonymous) asserted yes/no | `backend/tests/test_permission_classes.py::test_matrix_row_grants_exactly_its_section_12_2_cells` (`ROW_GRANTS`, 70 cells) + `backend/tests/test_authorization_matrix.py::test_matrix_rows_against_the_running_api` (every row walked against the real route or a probe mounting the real permission class; denied actors must 403/401) + `::test_every_matrix_row_is_exercised_for_every_actor` (traceability — one case per cell, no silent drops) |
| Still-deferred cells/routes stay denied and asserted absent | `backend/tests/test_authorization_matrix.py::test_deferred_matrix_cells_are_recorded_and_still_denied`, `::test_deferred_section_9_2_endpoints_do_not_exist_yet` (`DEFERRED_ENDPOINTS` drift guard; `POST /tasks/{id}/transition` currently deferred — findings log F-04) |
| Edge identity headers never authenticate alone (15.3) | `backend/tests/test_device_token_binding.py::test_edge_identity_headers_alone_grant_nothing` + `backend/tests/test_token_lifecycle.py::test_edge_identity_headers_alone_authenticate_nothing` (both an events route and an agent route) + `infra/cloudflare/access-policy.md` review (MT-5.2-01) |

## 7. Section 18 Security row — gate crosswalk

| Security-row item | Verified by |
|---|---|
| Authorization matrix tests | Section 5 above |
| Token scoping | Row 1 + row 7 tests; **`backend/tests/test_token_lifecycle.py`** (cross-project denial end-to-end on real routes + body-craft rejection; expiry/revocation/kind-separation/hash-at-rest across all three kinds — WP-6.1 "token scoping tests in CI") |
| Path traversal | `backend/tests/attachments/test_upload_validation.py` (path components stripped; content-addressed keys) + **`backend/tests/attachments/test_upload_abuse.py`** (raw/encoded/absolute/symlink-style names — no write outside the root; **in CI**) |
| Upload abuse | **`backend/tests/attachments/test_upload_abuse.py`** (oversized → canonical 400 with no partial artifact; spoofed MIME → 415 by sniffing; worker hand-off asserted) |
| Dependency scanning | CI gate `.github/workflows/security.yaml` (pip-audit any-severity for backend+bridge, npm audit critical for web; mobile pub noted out of gate) — **MT-6.1-05 executed it at full depth**: backend/bridge clean; web remediated (js-yaml override, F-06 fixed) down to the single logged accepted risk (braces chain, F-07); container-image CVE scanning recorded as F-08 |
| Secrets scanning | Same workflow (detect-secrets over every tracked file; fixture pragmas for test secrets) — **MT-6.1-04 executed it clean** (full worktree + WP files) and added the log-scrubbing suites (Section 4) |

---

*Rows marked "appended by MT-6.1-0x" are pre-registered by MT-6.1-01; the named slice updates
the status cell and adds its findings to the shared log. Any disagreement between a test and
Sections 12.1–12.5 is a regression in the code or a plan-owner decision — never a silent
matrix edit (MT-6.1-01 risk note).*
