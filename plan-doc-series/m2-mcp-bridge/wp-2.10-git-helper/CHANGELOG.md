# WP-2.10 — Local Git helper: changelog

Short notes per parent plan Section 20.4, item 7 — one entry per micro-task of
WP-2.10. All six MTs completed 2026-10-13 in dependency order under
`bridge/src/orchestrator_bridge/git_helper/`; every test runs against temp
fixture repositories (`tests/git_fixtures.py`) and never touches this
repository's Git state. The helper is read-mostly by construction: one
guarded invocation function (`git_helper.runner.run_git`) default-denies
every operation outside Section 10.8's "read operations plus branch
creation", so **never pushes or deletes** is a structural property with
refusal tests on every OS, not a convention.

## 2026-10-13 — MT-2.10-01: Repository identity, clean-state checks, capability guard

* `git_helper/errors.py` — `GitHelperError`: Section 9.2 catalog code
  (closed set via `api_errors.ErrorCode`; `VALIDATION_ERROR` for
  caller-fixable input, `SERVER_ERROR` for Git/environment failures), the
  Section 10.5 hint/next-action pair, optional `details`, and
  `failure_payload()` shaped for a future tool layer (mirrors
  `tools.errors.payload_text`'s JSON body).
* `git_helper/runner.py` — the security boundary:
  * **default-deny allowlist**: read-only subcommands (`status`,
    `rev-parse`, `rev-list`, `log`, `show`, `diff`, `cat-file`,
    `ls-files`, `ls-tree`, `merge-base`, `describe`) plus mutation-shaped
    forms of `branch` (create/list), `switch` (no force forms), `tag`
    (list only), and `worktree` (`list`/`add` only — `remove`/`prune` are
    the recorded OQ, never an implemented call). Anything else — `push`,
    `reset`, `clean`, `rebase`, `commit`, `add`, `fetch`, `clone`,
    `branch -D`, `tag -d`, `worktree remove`, `update-ref`, unknown
    subcommands — is refused *before a process exists*;
  * per-subcommand flag validators (e.g. `branch` rejects `-d/-D/-m/-f/
    --delete/--move/--force/--set-upstream-to`; `switch` rejects
    `-f/--force/--discard-changes/-C`); a global deny for
    `--output`/`--ext-diff`/`--textconv` (writes/programs from "reads");
  * no caller global options: `args[0]` must be the subcommand, so
    `--git-dir`, `--work-tree`, `-c`, `--exec-path` cannot redirect or
    redefine the command; the runner owns its fixed prefix
    (`-c core.quotepath=false -c color.ui=false --no-pager` — the
    MT-2.10-06 quoting/locale stability);
  * scrubbed environment (`GIT_CONFIG_GLOBAL`/`GIT_CONFIG_SYSTEM`/
    `GIT_CONFIG_NOSYSTEM` neutralize aliases and `core.*` redefinitions,
    `GIT_TERMINAL_PROMPT=0`, `GIT_PAGER=cat`, `LC_ALL=C`), array args,
    `shell=False`, `cwd` = the repository root, bounded timeout (30 s
    default) degrading to a retryable structured error — Section 12.3.
* `git_helper/repo.py` — `repo_identity()` resolves `--show-toplevel` /
  `--absolute-git-dir` and confirms the session's manifest-discovered root
  (mismatch → structured error naming both roots, before any evidence is
  collected; comparisons are `normcase`+`resolve` so Windows drive-letter
  case and symlink spellings cannot fake a mismatch); `clean_state()` is a
  structured porcelain-v1 `-z` report — clean flag, uncommitted/untracked
  counts, merge/rebase/cherry-pick/revert in-progress flags from the
  well-known `.git` markers. Reporting only: enforcement belongs to later
  consumers (WP-2.6), except branch creation's precondition (MT-2.10-02).
* Tests (`tests/test_git_repo_state.py`, 42): identity from root and
  subdirectory, expected-root mismatch, not-a-repository; clean/dirty/
  untracked/merge/rebase fixtures; the guard's both-ways proof — every
  allowed call runs, every forbidden operation (26-case parametrized
  matrix + a push/reset/delete sentinel that also asserts nothing was
  deleted) refuses with `VALIDATION_ERROR` before Git is involved; global
  option, write-flag, and missing-root seams.

## 2026-10-13 — MT-2.10-02: Branch naming derivation (G-09) and create-or-switch

* `git_helper/branch.py` — the **single G-09 derivation source**:
  `derive_branch_name(task_id, auto_branch_prefix=...)` is pure (no Git):
  the canonical task id `PID#####-T###` parses to its index part, the
  manifest's `auto_branch_prefix` always wins, and the documented default
  `feat/{PID}-` fills the PID from the task id — the plan's example holds
  byte-for-byte (`feat/PID00007-` + `PID00007-T004` →
  `feat/PID00007-T004`, Section 20.5 traceability, test-pinned). Invalid
  ids and prefixes that would form an invalid ref are **rejected, never
  sanitized** (structured error; ref validation mirrors
  `git check-ref-format`'s documented shapes).
* `create_or_switch_branch(root, branch, default_branch=...)` — the
  clean-state precondition refuses any non-clean tree (uncommitted
  changes, untracked files, or an in-progress merge/rebase — pre-existing
  content must never mix into agent work, Section 10.6 rule 1), verifies
  the default branch exists (missing → structured error whose next action
  says to fetch/create it outside the helper), then switches to an existing
  branch or creates it from the default via the MT-2.10-01 guard
  (`switch` / `switch -c` — reads plus branch creation only). Returns
  `BranchSwitch(branch, created, head_sha)`.
* Contract note: `tools.claim.branch_name_for` (WP-2.4, committed) remains
  the claim-response derivation and agrees with G-09 for canonical ids; the
  wiring to converge it on this function is explicitly out of this MT's
  scope ("the claim_task response wiring" is listed out of scope) and is
  recorded as a CI/consolidation follow-up below.
* Tests (`tests/test_branch_naming.py`, 32): the G-09 example verbatim,
  default/manifest/empty prefix precedence, nine unparseable task ids,
  thirteen invalid-prefix refusals, create-new vs switch-existing,
  dirty-tree and untracked refusal (with proof nothing was created),
  missing default branch, flag-like branch names refused before Git, and
  the post-creation sentinel (default branch intact, no ref removed).

## 2026-10-13 — MT-2.10-03: Merge-base diff, stats and changed-file list

* `git_helper/diff.py` — `merge_base_diff(root, branch, default_branch)`
  produces the Section 9.7 evidence bundle: `merge_base_sha`, `head_sha`,
  unified patch (`--no-color --no-ext-diff --unified=3 --no-renames`),
  `patch_size_bytes` (true UTF-8 byte size for the 5 MB cap decision —
  the helper never truncates), `DiffStats(insertions, deletions,
  files_changed)` and per-file `ChangedFile(path, status, insertions,
  deletions, binary)` from `--name-status -z` + `--numstat -z` (parsed
  NUL-separated, so spaces and non-ASCII paths never break the parse;
  binary rows follow Git's own `-` marker and count zero lines).
* The diff is branch-vs-**merge-base**, never branch-vs-default-HEAD or a
  worktree diff; missing refs and unrelated histories produce
  structured `VALIDATION_ERROR`s with actionable hints; ref arguments are
  validated so they can never become Git flags.
* Paths are repository-relative, forward-slash on every OS (Section 12.3;
  git emits `/` natively, the normalization is pinned by test).
* Tests (`tests/test_merge_base_diff.py`, 11): the divergent-base fixture
  (main advances after the fork — main's file must not appear in the
  bundle), stats accuracy, empty branch, byte-size reporting, forward-slash
  normalization, deleted-file status, binary marking, missing branch /
  missing default / unrelated-histories (orphan branch) errors, and
  flag-injection refusal.

## 2026-10-13 — MT-2.10-04: Secret-like pattern scan of added lines (feeds R5)

* `git_helper/secret_scan.py` + `git_helper/secret_patterns.toml` — a
  read-only scanner over the **added lines only** of the MT-2.10-03
  bundle: hunk-aware parsing tracks file and new-file line numbers
  (declared hunk line counts, so an added line whose content starts with
  `+++` cannot impersonate a file header). Findings carry pattern id,
  severity, path, line and a **redacted excerpt** — the matched span is
  replaced by `[REDACTED:<id>]` and the surviving context clipped
  (Section 12.4; the redaction test is a gate: matched material must never
  appear in output). `SecretScanResult` reports count, files/lines
  scanned, and per-file grouping — the R5-corroboration shape
  (`sensitive_config_changed`; the `sensitive_config_globs` half stays
  backend-side per Section 9.4).
* Patterns are **configuration with documented defaults**
  (Section 9.10): the default set ships as a TOML data file with exactly
  the families the plan names — private-key blocks, AWS-style key ids,
  secret-looking assignments, bearer-token literals, GitHub token
  prefixes — and `load_patterns(path)` reads a caller file in the same
  shape, so adding a pattern is a data edit, never a code change. Broken
  or invalid pattern files fail loudly (`VALIDATION_ERROR`), never
  silently scan less. Narrow per-scan ignore ids default to none.
* Tests (`tests/test_secret_scan.py`, 24): true positive per family,
  redaction gate per family (parametrized over real merge-base diffs from
  fixture repos), finding shape, added-lines-only scoping (a secret that
  leaves the codebase is not flagged), empty diff and binary paths,
  false-positive sanity (prose, identifiers, placeholders), the
  documented default set, custom pattern file, narrow ignores, and
  loud-failure on broken pattern files.

## 2026-10-13 — MT-2.10-05: Optional per-task worktree helper (OQ-03)

* `git_helper/worktree.py` — strictly opt-in on the manifest's
  `agent_hints.worktree_mode` (default false, Section 10.3): disabled is a
  structured no-op `WorktreeOutcome` that creates nothing, so the OQ-03
  default (one concurrent task per project) is preserved bit-for-bit.
  Enabled: the canonical G-09 branch ties the worktree to the task, the
  documented location is `<repo>/.worktrees/<task id>` (inside the
  repository's control, Section 12.3; meant for the project's
  `.gitignore` — the helper never edits tracked files), creation is
  idempotent (existing worktree resolves, never duplicates), and two
  tasks always yield distinct roots (the G-26 mitigation).
* Teardown restraint: `inspect_worktree` reports a **stale** registration
  (registered in Git, directory gone) with a next action telling the
  operator to run `git worktree prune` themselves — the helper never
  removes worktrees, branches or any other ref. Worktree removal is
  recorded as **OQ-10** (open question), not implemented (Section 20.1
  item 5).
* Tests (`tests/test_worktree_helper.py`, 11): disabled-by-default no-op
  (nothing created), enabled creation on the canonical branch, idempotent
  lookup, distinct per-task roots, root-inside-repository assertion,
  main-tree untouched (branch and status), stale reporting without
  deletion, unparseable task id (path traversal) refusal, and the
  push/reset/delete sentinel with worktrees in play from both the main
  tree and the worktree.

## 2026-10-13 — MT-2.10-06: OS matrix tests (Windows, macOS, Linux; paths with spaces)

* `tests/test_git_helper_os_matrix.py` (7) — the suite the CI matrix runs
  per leg (the matrix job itself is the CI follow-up below; pipeline
  config is outside this WP's file protocol): every fixture repository
  lives under a path **containing a space** (asserted before trusting any
  result — a fixture that avoided the hard case proves nothing), and the
  Windows leg adds a non-ASCII path component with a **named skip** on
  other OSes (no silent skips, Section 20.4 item 1). The sweep exercises
  identity/status, branch create, merge-base diff (forward-slash
  normalization asserted on the spaced nested path), secret scan and the
  worktree helper against the spaced paths; the push/reset/delete
  rejection sentinel runs unconditionally on every OS; refusals are shown
  to be pre-process (they cannot depend on the OS or the Git build).
* Cross-platform invocation notes pinned by these tests: the runner
  prefixes the command line with `git` itself (Windows parses the
  executable from the first token — the fixed `-c` prefix would be
  mistaken for it), fixtures pin `core.autocrlf=false` and local
  `user.*`/`commit.gpgsign=false` so developer/CI global config cannot
  leak into fixture behavior, and machine-format outputs (`-z`,
  porcelain, `--numstat`) carry no locale-dependent parsing.

## Verification-finisher pass (2026-10-13)

* This work package was lost with the original bridge agent's machine
  outage (no WP-2.10 files survived in the working tree or git history);
  all six MTs were re-implemented and verified in this pass.
* `uv run ruff check .`, `ruff format --check .`, `mypy .` (strict) and
  the targeted suites are green; the full bridge suite is green
  (live-backend opt-in skips remain skipped by design).

## Open items / CI follow-ups

* **OQ-10 — worktree removal**: the helper reports stale worktrees but
  deliberately never removes them (Section 10.8 forbids deletes). If
  operator ergonomics demand a helper-side removal, it needs a parent-plan
  decision first (Section 20.1 item 5).
* **CI OS matrix job**: MT-2.10-06's suite is written for three OS legs,
  but the workflow matrix (Windows/macOS/Linux bridge job) lives in the
  CI pipeline config, outside this WP's file protocol — adding the matrix
  leg is recorded for the CI owner (WP-0.3).
* **claim_task wiring convergence**: `tools.claim.branch_name_for` agrees
  with G-09 for canonical ids but is a separate (WP-2.4, committed)
  implementation; converging it on `git_helper.branch.derive_branch_name`
  is the recorded consolidation follow-up (MT-2.10-02 lists the wiring as
  out of scope).
* **Numeric defaults flagged for review** (MT-2.10-01 risk note): the
  30 s Git invocation timeout is a helper-chosen conservative value, not
  plan-specified.
