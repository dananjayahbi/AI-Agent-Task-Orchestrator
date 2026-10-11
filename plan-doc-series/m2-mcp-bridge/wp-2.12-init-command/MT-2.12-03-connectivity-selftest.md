# MT-2.12-03 — Run the Connectivity Self-Test

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.12-03 |
| Title | Run the connectivity self-test |
| Parent WP | WP-2.12 — Init command (Milestone M2) |
| Requirements | FR-MCP-08 (self-test duty), NFR-10 (debuggability), FR-SEC-01 |
| Priority | M |
| Dependencies | MT-2.12-01 (manifest), MT-2.12-02 (token stored), MT-2.2-04 (session open used as the probe), MT-2.1-03 (logging) |
| Parent sections | 10.11 (init duty 3), 10.3 (steps 3–4), 19.1 (WP-2.12 acceptance), 20.4, 20.5 |

## Context
FR-MCP-08's third duty: init "runs a self-test." Section 10.11 lists it among init's
outputs; WP-2.12's acceptance — "new repo usable by agent in under 2 minutes" — is
only meaningful if init proves the loop end-to-end before the user walks away: manifest
valid, token accepted, backend reachable, project binding correct. The cheapest honest
probe is the real flow the bridge will use anyway — Section 10.3's steps 3–4: load the
token (MT-2.2-03), open an agent session (`POST /agent-sessions` via MT-2.2-04's
client) — because it verifies credential, binding (`AUTH_FORBIDDEN_PROJECT` would
fail here first, which is exactly MT-2.2-05's UX for a wrong token), and API
reachability in one call. A weaker probe (unauthenticated ping) would pass on a
wrong-project token and defeat the acceptance's intent. The self-test runs **after**
manifest and token storage in the same init invocation (FR-MCP-08 duty order), and
its output is the user's go/no-go signal (NFR-10: diagnosable from one screen).

## Inputs / Prerequisites
* MT-2.12-01 / MT-2.12-02 — manifest and token in place (self-test proves them).
* MT-2.2-03 / MT-2.2-04 — loader and session-open client reused here, not
  reimplemented (Section 19.6 single implementation).
* MT-2.2-05 — mismatch abort messaging reused when the self-test hits a
  wrong-project token (same clear-message path).
* MT-2.1-02 — backend base URL config; MT-2.1-03 — structured result logging.
* Parent plan Section 10.11 — init duty 3; Section 10.3 — steps 3–4 as the probe
  sequence; Section 10.10 — bounded retries for transient failures.

## Scope (in)
* A `--self-test`-style step chained at the end of `orchestrator init` (and runnable
  standalone for re-verification, since MT-2.12-04's snippets reference it): checks,
  in order —
  1. **Manifest present and schema-valid** (reuse MT-2.2-01/02 — local, instant).
  2. **Token resolvable** (reuse MT-2.2-03 — reports which source supplied it:
     environment or user-level config, never the value).
  3. **Backend reachable and credential accepted**: open an agent session (MT-2.2-04)
     against the configured endpoint; then close it (session end from the same
     module) so init does not leak sessions.
* Bounded, event-driven retries for transient network failures per Section 10.10 —
  a small fixed attempt budget with clear per-attempt logs; no indefinite hangs
  (user-visible progress for the "under 2 minutes" flow).
* Verdict output: a per-check pass/fail summary on stdout (human-readable, one line
  each) plus structured logs (MT-2.1-03); failure names the failing step and the
  remedy (fix manifest → re-run init; fix token source; fix endpoint config) —
  `AUTH_FORBIDDEN_PROJECT` during step 3 routes to MT-2.2-05's clear message.
* Exit code: non-zero if any check fails (so CI scripts and agent guides can gate on
  it); zero only when all three pass.
* The self-test must not print secrets (token redaction — MT-2.1-03 discipline) and
  must not modify the manifest or config (read-only verification).
* Tests: all-pass; each failure mode (missing manifest, unresolvable token,
  unreachable backend, 403 wrong project) with correct verdict/exit code/remedy
  text; session closed after a passed probe; bounded retry count respected;
  redaction; changelog note (Section 20.4 item 7).

## Out of scope
* Writing manifest/token — MT-2.12-01 / MT-2.12-02; config snippets — MT-2.12-04.
* Backend health/metrics endpoints beyond what the session-open call exercises — no
  new `/health` endpoint is invented here (if none exists in the M1 API, the
  session-open probe is the plan-supported check; note any desire for a lighter
  endpoint as a new OQ `OQ-15+`).
* Tool-level verification (`list_projects` smoke call) — tool implementations arrive
  with WP-2.4; the self-test proves binding, not the tool surface (record this
  boundary in the changelog).
* Monitoring/alerting of connectivity post-init — Section 17's backend concern.

## Target paths
* `bridge/` init command module — self-test step (chained after MT-2.12-02's storage)
* Reused bridge modules: manifest (MT-2.2-01/02), token (MT-2.2-03), session
  (MT-2.2-04) — no parallel implementations
* `bridge/tests/` (verdict matrix, retry bounds, session cleanup, redaction)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] `orchestrator init` ends with the self-test: manifest validity, token
  resolution, and a real session-open probe — FR-MCP-08 third duty; Section 10.11
  (WP-2.12 second/third slice).
- [ ] The probe verifies credential + binding + reachability together (session open),
  not an unauthenticated ping — Section 10.3 steps 3–4 (FR-SEC-01 exercised
  server-side).
- [ ] Per-check verdicts print with remedy text; exit code non-zero on any failure;
  wrong-project failure reuses MT-2.2-05's clear message (NFR-10; WP-2.12
  acceptance).
- [ ] Transient failures retried with a fixed bound per Section 10.10; no hang —
  the full init flow stays inside the WP's "under 2 minutes" target (recorded in
  the changelog).
- [ ] The opened probe session is closed after the test; no manifest/config
  mutation; no secret in output or logs (Section 17; Section 20.4 item 3).
- [ ] Tests, lint and type check green in CI (item 2); changelog note added (item 7).

## Test command
`uv run --directory bridge pytest tests/test_init_selftest.py -v` — all-pass path,
four failure verdicts with exit codes and remedy text, bounded retries, session
cleanup, redaction; `uv run --directory bridge ruff check .` green; end-to-end
manual/CI run: `orchestrator init` in a scratch repo, all checks pass (record per
Section 20.4 item 1).

## Attachments
* [FR-MCP-08 — Init command duties](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.11 — Init and packaging](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.3 — Binding steps used as the probe](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Opening a real session in init creates backend-side artifacts (an agent_session
  row) — close it explicitly; if the backend lacks a session-end call usable without
  a running bridge, reuse MT-2.2-04's end path and record the dependency; do not
  leave sessions dangling hoping staleness sweeps them (note the sweep's existence
  or absence in the changelog).
* Self-test against a mocked backend in tests proves wiring, not connectivity — the
  WP acceptance needs at least one recorded real run (Section 20.4 item 1 proof in
  the changelog).
* Ordering matters: probing before token storage (if a user skips steps) yields a
  confusing "no token" verdict — enforce FR-MCP-08's duty order in the command
  flow and test the partial-completion message.
