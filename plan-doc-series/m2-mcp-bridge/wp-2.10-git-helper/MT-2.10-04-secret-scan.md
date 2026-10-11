# MT-2.10-04 — Implement secret-like pattern scan of added lines (feeds rule R5)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.10-04 |
| Title | Implement secret-like pattern scan of added lines (feeds rule R5) |
| Parent WP | WP-2.10 — Local Git helper (Milestone M2) |
| Requirements | FR-MCP-07; feeds Policy Engine rule R5 (Section 9.4) |
| Priority | M |
| Dependencies | MT-2.10-03 (diff and added lines), MT-2.10-01 (guard) |
| Parent sections | 9.4 (rule R5), 10.8, 12.4, 19 (WP-2.10), 20.4, 20.5 |

## Context
Section 10.8 lists "detect secret-like patterns in added lines (feeds R5)" as a helper
capability, and Section 9.4 rule R5 fails when env/key patterns appear in added lines
(review reason `sensitive_config_changed` — alongside `sensitive_config_globs` file
matches computed backend-side from the stored patch). This slice is the local,
read-only scanner over the merge-base diff's added lines: it flags patterns that look
like credentials before or during submission, giving the bridge and the agent a
chance to stop a leak, and supplying corroborating evidence for R5. Section 12.4's
discipline applies: secrets never reach Git, logs, or committed files.

## Inputs / Prerequisites
* Parent plan Section 10.8 — the secret-pattern detection capability feeding R5.
* Parent plan Section 9.4 — rule R5: env/key patterns in added lines; review reason
  `sensitive_config_changed`.
* Parent plan Section 12.4 — secrets only in environment variables; logs scrub
  tokens.
* MT-2.10-03 — the added-line source (unified diff of the task branch).
* WP-0.5 conventions — correlation with error/reporting conventions where a finding
  is surfaced.

## Scope (in)
* A scanner over added lines (`+` lines of the merge-base diff) applying a documented
  pattern set of secret-like indicators: private-key blocks, common API/token
  prefixes, `password=`/`api_key=`-style assignments, AWS-style key shapes,
  bearer-token literals — the "env/key patterns" family Section 9.4 names. The exact
  pattern list is configuration with documented defaults (Section 9.10), not
  hard-coded folklore.
* Structured findings: pattern id, file path, line number, and a redacted excerpt —
  the excerpt must never contain the matched secret material itself (Section 12.4:
  logs and output scrub secrets; findings are safe to show in tool output).
* Severity/summary shape: a count and per-file findings list so callers (submission
  flow, rules surface) can warn the agent and so R5-style evidence can reference
  them.
* Configurable ignore rules for known-safe fixtures (documented default: none
  beyond test fixtures), applied narrowly.
* Unit tests: true positives across each pattern family, false-positive sanity
  (ordinary code with words like "password" in prose/identifiers vs actual
  assignments), redaction proof (matched secret never appears in output), empty-diff
  and binary-file paths.

## Out of scope
* Matching `sensitive_config_globs` file paths — backend Policy Engine R5 computes
  that half from the stored patch (Section 9.4 design note).
* Blocking submission or editing files — policy/UX decisions for WP-2.6 and the
  rules block; this task only detects and reports.
* Backend-side scanning of the uploaded patch — WP-3.4/Policy Engine.
* Entropy-based ML scanning — not specified in the plan; do not invent beyond the
  pattern families Section 9.4 names (raise an OQ-xx if stronger scanning is wanted).

## Target paths
* `bridge/src/` (secret-pattern scanner in the Git helper; pattern config file)
* `bridge/tests/` (scanner tests)
* WP changelog entry

## Acceptance criteria
- [ ] The scanner flags added-line matches for each documented secret-like pattern
  family and reports file, line, pattern id and redacted excerpt — with no matched
  secret material present in any output (Section 12.4, Section 10.8).
- [ ] Findings are produced from the MT-2.10-03 merge-base diff's added lines only
  (unchanged/removed lines are not scanned), asserted by test.
- [ ] Patterns are configuration with documented defaults; adding a pattern does not
  require code change (Section 9.10).
- [ ] Output shape supports R5 corroboration: summary count plus per-file findings
  usable by the submission flow (Section 9.4 rule R5).
- [ ] Tests pass in CI, including redaction and false-positive sanity cases
  (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the scanner tests, e.g. `uv run pytest bridge/tests/ -k secret_scan`; assert
true positives per pattern family, added-lines-only scoping, redaction of matched
material, and clean results on the fixture false-positive cases.

## Attachments
* [Section 9.4 — Policy Engine rules](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.8 — Local Git helper](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Redaction is a security requirement, not polish: a finding excerpt that echoes the
  secret defeats the feature — the redaction test must be part of the gate.
* Pattern drift cuts both ways: over-broad patterns spam agents with false alarms
  (they will learn to ignore them); keep the default set tight and configurable.
