# WP-2.6 — Tools: checkpoint and submission with Git evidence: changelog

Short notes per parent plan Section 20.4, item 7.

* 2026-10-13 — **MT-2.6-01 done** — `log_task_checkpoint` lands
  (`tools/checkpoint.py`, spec in `schemas.py`, factory in `registration.py`).
  Wire body is the WP-1.8 `CheckpointCreateSerializer` contract
  (`session_id` + `lease_generation` fencing pair, `message`, `percent`);
  the response returns the backend's new `lease_expires_at` plus the RISK-02
  `next_checkpoint_due` hint, derived from *the same numbers the response
  returns*: interval = `checkpoint_interval_minutes` of the session's policy
  lease, instant clamped to the new expiry (never beyond the lease itself).
  `capped: true` switches the hint to the cap instant and the guidance to
  submit-or-release (Section 8.6 hard cap — no more lease is coming).
  `LEASE_EXPIRED` maps to the existing stop-and-reclaim hint/next action; the
  bridge adds no retry for non-retryable envelopes. Tests:
  `pytest bridge/tests/ -k log_task_checkpoint` (7).
* 2026-10-13 — **MT-2.6-02 done** — submission verification
  (`tools/submit_verify.py`), host-side only (ADR-007): repository identity
  is resolved from the manifest's directory *before any git work*
  (`repo_identity`; a manifest outside any work tree is rejected);
  `git_branch` must equal the WP-2.10 strict G-09 derivation and exist
  locally; `commit_sha` must be 4–64 hex (flag-injection guard) that
  resolves to a commit **reachable on that branch** (abbreviated shas are
  normalized to the full id). Clean state is *consumed* from WP-2.10's
  `clean_state`, never re-implemented — **recorded reading**: an in-progress
  merge/rebase/cherry-pick/revert rejects (unsettled evidence), while dirty
  or untracked files are reported in the outcome rather than rejected (the
  patch is commit-keyed, so working-tree state cannot leak into the
  evidence; "commit before submission" stays rule 4 for agents). **Catalog
  choice (risk note)**: bad branch/sha rejections use `VALIDATION_ERROR` —
  the plan names no dedicated code and Section 9.2 is closed; no code was
  invented. **Fencing**: a task never claimed in this process submits
  `lease_generation: 0`; the backend answers `LEASE_EXPIRED`/`LEASE_NOT_OWNED`
  authoritatively (Section 19.3) — the bridge never guesses locally. Tests:
  `pytest bridge/tests/ -k submit_verify` (11).
* 2026-10-13 — **MT-2.6-03 done** — merge-base patch capture
  (`tools/submit_capture.py`): WP-2.10 `merge_base_diff` of the task branch
  vs the **manifest's default branch**, keyed to the verified sha — capture
  **re-verifies the tip** (the MT's risk note) and refuses with a structured
  `VALIDATION_ERROR` if the branch moved between verification and capture,
  so evidence can never straddle two commits; working-tree churn is provably
  inert (ref-to-ref diff). Missing merge-base (unrelated histories / shallow
  clones) fails with the helper's clear error, never a wrong diff. **5 MB
  boundary coordination with WP-3.2 (risk note)**: the bridge mirrors the
  backend's constant exactly (`5 * 1024 * 1024`, inclusive — `size > cap` is
  oversize) and boundary tests pin both sides (`max_bytes == size` keeps the
  body; `size - 1` marks oversize). Division of labor matches WP-3.2:
  **bridge prepares, backend stores** — the evidence view replaces the body
  with the literal `"diff too large"` marker (the tool response never dumps a
  multi-MB diff), while the *upload* still carries the full patch text
  because the backend parses the received bytes for authoritative stats and
  applies the Section 9.7 storage cap itself; the bridge never truncates the
  wire. Tests: `pytest bridge/tests/ -k patch_capture` (9).
* 2026-10-13 — **MT-2.6-04 done** — `submit_task_resolution`
  (`tools/submit.py`, spec + factory registered): verify → capture →
  **persist to the spool** → upload. The wire body is the WP-3.2
  `ResolutionSubmitSerializer` contract (fencing pair, verified branch/sha,
  summary, self-flag + justification, full patch, provisional
  `changed_files`/`diff_summary` the server's parse replaces per Section
  9.7); the POST carries the `Idempotency-Key` minted per logical
  submission. The outcome reported to the agent is the backend's actual task
  state — `to_be_audited` (T7) or **`in_human_review` with `review_reason`**
  (T8; escalations are never hidden behind a success shape) — plus the
  `trigger` that fired and any `scope_violations`. `LEASE_EXPIRED` /
  `TASK_STATE_CONFLICT` are stop-and-orient answers (Section 11.1 step 7):
  non-retryable envelopes are not retried (asserted with retries enabled).
  Tests: `pytest bridge/tests/ -k submit_resolution` (11).
* 2026-10-13 — **MT-2.6-05 done** — submission spool
  (`submission_spool.py`): the assembled payload (patch, summary, flags,
  **idempotency key**) is written to the user-level data area (config-area
  `submission-spool/`, override `ORCHESTRATOR_SPOOL_DIR`; atomic
  temp+`os.replace`, `0o600` where the OS honors it) **before any network
  attempt** — proven at the send seam by a test that observes the file on
  disk inside the request handler. Retries (transport backoff in-call, or
  the startup sweep) replay the **stored key with the stored body**, so the
  backend replays instead of double-submitting (ADR-012 key-stability
  asserted, including across a simulated kill-mid-submission + restart).
  Ack clears the entry; only acknowledgments complete a submission.
  **Spool-entry resolution rule (risk note, recorded)**: retryable failures
  keep the entry (the decision is still pending on the network) and the
  surfaced error says the payload is retained; a **definitive backend
  rejection deletes it** — the payload can never succeed as-is and the agent
  must fix and resubmit; other projects' entries are never replayed by this
  session's token. Hygiene: no tokens/absolute host paths in payloads (auth
  rides headers only — test-proven), payload contents never logged (entry
  ids/task ids/error codes only), bounded retention (7 days) pruning stuck
  entries with an operator message (`event=spool_pruned`). Startup resume is
  wired in the stdio entrypoint (best-effort; startup never dies because the
  backend is unreachable); HTTP connections bind the spool so submissions
  still persist there. **Follow-up**: an HTTP-mode resume sweep needs a
  project-level cadence decision (per-connection sweeps would be spammy) —
  entries wait on disk for a stdio bridge of the project or for retention.
  Tests: `pytest bridge/tests/ -k submission_spool` (14; the POSIX
  permission-bit test skips on Windows).
* 2026-10-13 — **MT-2.6-06 done — G-11 deferral recorded (Could)**:
  *optional output-tail attachment per checkpoint is deferred; v1 live feed
  = the checkpoint stream* (parent plan Section 4, G-11 row, which cites
  "WP-2.6 note" — this entry — completing the cross-reference both ways).
  Why: the only v1 ingest path is `log_task_checkpoint`, whose contract
  stays `task_id`, `message`, `percentage` (Section 10.5; unchanged here).
  The deferred design would attach a tail of agent output to a checkpoint for
  the live terminal view; it is unblocked later by the attachment pipeline
  (WP-2.5/1.14) **plus an explicit product need** — if wanted, it changes
  scope from "Could" to shipped work and must be raised as a decision
  (Section 20.1), not folded in. Repository sweep for this entry: zero
  `output_tail`/`output-tail` references anywhere in `bridge/` and no stubs,
  dead parameters or partial capture path — the deferral is total (no new
  requirement IDs; traces to G-11 only).
* 2026-10-13 — WP-2.6 complete (MT-2.6-01..06). Catalog note: the MCP
  server now advertises the five WP-2.4 core tools plus
  `log_task_checkpoint` and `submit_task_resolution` (Section 10.5 order:
  the pair sits between `claim_task` and `release_task`); the catalog tests
  (`test_tool_schemas.py`, `test_layout.py`) and the entrypoint handshake
  tests follow `CORE_TOOL_NAMES`. One unrelated test-robustness fix rode
  along: `test_connection_lifecycle_failed_handshake_leaves_no_state`
  asserted the best-effort backend `/end` synchronously after the registry
  reservation dropped (app.py cancels the reservation *before* finalize),
  which flaked under full-suite load — it now uses the harness's documented
  bounded `wait_for`, same intent, no timing assumption. Battery: `ruff
  check`, `ruff format --check`, `mypy .` (strict) and `pytest -q` all green
  — 626 passed, 7 skipped (live opt-in tests stay gated). The previous pause
  note (2026-10-13, "paused at MT-2.6-01, no code written yet") is retired
  by these entries.
