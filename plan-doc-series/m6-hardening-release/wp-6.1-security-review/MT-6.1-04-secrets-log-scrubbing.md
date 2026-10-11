# MT-6.1-04 — Audit Secrets and Log Scrubbing (No Tokens, No Attachment Text)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.1-04 |
| Title | Audit secrets and log scrubbing (no tokens, no attachment text) |
| Parent WP | WP-6.1 — Security review (Milestone M6) |
| Requirements | NFR-07, FR-SEC-04 |
| Priority | M |
| Dependencies | MT-1.1-02 (structured logging), MT-2.1-03 (bridge log redaction), MT-0.3-04 (CI secret scans), MT-6.1-01 (findings log) |
| Parent sections | 12.1 (secrets in diffs threat), 12.4 (data protection: logs scrub tokens, truncate attachment text), 17 (Logging row: token/secret scrubbing), 18 (Quality gates: secrets scanning), 19 (WP-6.1), 20.4 (item 3), 20.5; 21 (RISK-08, RISK-14) |

## Context
Section 12.4 fixes two log rules: "Logs scrub tokens and truncate attachment text."
Section 17 repeats them in the Logging row: structured JSON, correlation id
propagated, token/secret scrubbing. FR-SEC-04 keeps secrets out of the repo and
manifest; RISK-14 (agent token leakage in config files or logs) and RISK-08 (secret
detection misses) are the register entries this audit retires. Section 20.4 item 3
makes "no secrets committed" a global DoD check. This slice audits both directions —
nothing secret in the repository, and nothing secret in the runtime logs — and
converts the log side into tests, since scanning output after the fact is the only
way to keep the scrubbing honest over time.

## Inputs / Prerequisites
* MT-1.1-02 — backend structured logging with redaction; MT-2.1-03 — bridge
  logging with redaction; MT-0.3-04 — the CI secret-scan gate from WP-0.3.
* Parent plan Section 12.4 — the two scrubbing rules verbatim; Section 17 — logging
  row requirements.
* Parent plan Section 9.10 / WP-0.5 conventions — correlation-id handling (headers
  conventions from MT-0.5-03) so correlation ids are present but never entangled
  with secrets.
* Fixture flows that generate sensitive log lines: login/token issuance, bridge
  session start with a stored token, attachment upload + OCR pipeline run, claim and
  submission with correlation id.
* MT-6.1-01 — findings log, severity scale and mapping to update.

## Scope (in)
* **Repository audit:** run the existing secret scans (Section 18 quality gates)
  across backend, bridge, web, mobile and infra; additionally confirm the manifest
  and any committed config/env-template carry no real values (FR-SEC-04; Section
  16.2 "real values live outside Git"). Record any hit with severity (RISK-08: a
  missed leak is high).
* **Log scrubbing tests:** drive the sensitive flows above and assert on captured
  log output that:
  * no token, password, session key, FCM/tunnel credential or Authorization header
    value appears in any backend, worker, bridge or web log line (Sections 12.4,
    17; RISK-14);
  * attachment text is truncated per Section 12.4 — no full OCR/extracted content
    in logs, even at debug level;
  * correlation ids remain present and unchanged (NFR-10 observability preserved —
    scrubbing must not remove the join key).
* A config review: scrubbing applies at all log levels and to exception/log-error
  paths (stack traces are a classic leak channel); any gap becomes a finding.
* Append results to the threat-to-test mapping (secrets-in-diffs and token-theft
  log-facing rows) and the findings log; fix or file high/critical gaps.
* Changelog note (Section 20.4 item 7).

## Out of scope
* The R5 secret-pattern scan of agent diffs feeding escalation — WP-2.10/Policy
  Engine territory (Section 12.1 row; reference by pointer in the mapping).
* Changing the WP-0.5 conventions or the log schema — verify, don't redesign.
* External log-management products — the plan ships logs via Section 17's approach;
  no new infrastructure here.
* The other review slices — MT-6.1-01/02/03/05 (shared log only).

## Target paths
* `backend/tests/` — log scrubbing test module (fixture flows → captured logs →
  assertions)
* `bridge/tests/` — bridge-side scrubbing assertions (extend MT-2.1-03's redaction
  tests)
* `docs/plan/security-threat-test-mapping.md` (secrets/log rows updated)
* `docs/plan/security-findings-log.md` (findings appended)
* WP changelog entry

## Acceptance criteria
- [ ] Repository-wide secret scan runs clean (or findings logged with severity and
  remediated for critical/high) — Section 20.4 item 3; FR-SEC-04.
- [ ] Tests assert no token/credential values in backend, worker and bridge logs
  across the sensitive fixture flows (Sections 12.4, 17; RISK-14).
- [ ] Attachment-text truncation asserted — no full extracted content in logs at any
  level (Section 12.4 verbatim rule).
- [ ] Correlation ids still present after scrubbing (NFR-10 preserved).
- [ ] Exception/error paths covered by the assertions, not only happy-path lines.
- [ ] Mapping and findings log updated; zero open critical/high from this slice;
  tests green in CI (Sections 19, 20.4); changelog note added (item 7).

## Test command
`pytest backend/tests/ -k log_scrubbing -v` plus the bridge counterpart
`uv run --directory bridge pytest tests/ -k redaction -v` — captured logs from the
fixture flows contain no token/secret values, truncated attachment text only, and
kept correlation ids; then run the CI secret scan and confirm zero unreviewed hits.

## Attachments
* [Section 12.4 — Data protection](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 17 — Observability and Operations (Logging row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 21 — RISK-08, RISK-14](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Scrubbing rules and test patterns must share a single definition — a test that
  hardcodes its own pattern list will drift from the runtime redactor and pass
  while real secrets leak; assert against the redactor's own registered patterns.
* Debug-level logs are enabled in dev profiles (Section 16.1 `dev` profile) — the
  rules still apply (a dev log pasted into an issue leaks just as well); test the
  level that is most verbose, not only default production level.
* Attachment-text truncation length is a judgment call not fixed by the plan — pick
  a small value, record it in the changelog, and assert the property (no complete
  document body), not an exact byte count, unless the conventions doc fixes one.
