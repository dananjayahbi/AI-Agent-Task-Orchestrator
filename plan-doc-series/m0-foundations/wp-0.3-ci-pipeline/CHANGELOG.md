# WP-0.3 — CI pipeline: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-0.3-01** — Lint and type-check jobs created in
  `.github/workflows/lint-type.yaml` (new `.github/workflows/` directory — the
  repository's CI platform, GitHub Actions, is now recorded in CONTRIBUTING.md
  "Continuous integration" per the MT risk note). Three jobs, all required-check
  names: `lint` and `type-check` cover all four packages with VERBATIM copies of
  the WP-0.1 documented commands (backend/bridge: `ruff check` + `ruff format
  --check` in lint, `mypy` in type-check; web: `npm --prefix web run lint` +
  `format:check` in lint, `typecheck` in type-check; mobile:
  `dart format --set-exit-if-changed mobile/` in lint, `flutter analyze` — the
  documented mobile analyze/type check — in type-check, so neither package is
  skipped in either job and the analyzer runs exactly once). Plus
  `migration-schema-diff`: the Section 18 migration/schema-diff placeholder that
  passes while `backend/manage.py` is absent and automatically becomes the real
  `makemigrations --check --dry-run` gate when the Django project lands (WP-1.1,
  which then supplies the settings/env for `manage.py`); public-contract OpenAPI
  diffing stays with WP-1.1 / MT-1.1-04 — not simulated here. Triggers:
  pull requests, pushes to `main`, manual dispatch; `permissions: contents: read`
  only; no secrets and no environment-specific paths (Section 20.4 item 3).
  Toolchains pinned to the WP-0.1-verified versions (RISK-15): uv 0.12.10, Node 22
  LTS (no .nvmrc/engines pin exists — recorded CI choice with an open-question
  note), Flutter 3.35.6 stable. Actions use major version tags because the parent
  plan prescribes no SHA pinning. The eight required status-check names and the
  exact `gh api` branch-protection command are documented in CONTRIBUTING.md —
  application of the rule is a post-push admin step (local `gh` is
  unauthenticated).
- **MT-0.3-02** — Test jobs created in `.github/workflows/test.yaml` (dedicated
  test workflow). `unit-tests`: per-package suite detection feeding a documented,
  explicit allow-empty policy — every empty suite prints an `allow-empty` notice and
  is skipped, every non-empty suite runs its documented command verbatim
  (backend/bridge `uv run --directory … pytest`, web `npm --prefix web run test`,
  mobile `flutter test` from `mobile/`), and any failing test fails the job
  (no-new-failures; no `continue-on-error` anywhere). Setup steps are conditional on
  suite presence so the skeleton run stays fast. `integration-tests`: provisions
  real `postgres:16-alpine` + `redis:7.4-alpine` service containers (same image pins
  as `infra/compose`, health-check gated) with job-level CI-provided
  `ORCHESTRATOR_DATABASE_URL` / `ORCHESTRATOR_CACHE_URL` (WP-0.5 env naming) and
  trust auth on loopback — zero credential material in the workflow or caches
  (Section 20.4 item 3, RISK-14); runs `pytest backend/tests/integration` /
  `pytest bridge/tests/integration` under the same allow-empty policy. CONTRIBUTING.md
  gained "Test commands (unit and integration)" — the tables now document the test
  commands, the empty-suite behavior, the runner-dependency handoff (pytest arrives
  with the first work package that lands test files; CI fails closed), and the
  exclusion of e2e/web-mobile integration scenarios (their WPs). Both jobs are among
  the eight required status checks documented in MT-0.3-01.
- **MT-0.3-03** — Container build job created in
  `.github/workflows/container-build.yaml`. Discovery is pattern-based (`find` for
  every `Dockerfile` outside `.git`/`node_modules`/`.venv`/`.dart_tool`), so the two
  current placeholder images (`infra/compose/stubs/backend`, `infra/compose/stubs/web`)
  and every future image definition (real backend WP-1.1, real web WP-4.1, worker/
  beat reuse) are built without rewriting the job; zero discovered Dockerfiles is an
  explicit error (discovery broken while Compose still references images). Each image
  builds in its own log group with the Dockerfile path in the group title and in any
  `::error` line, all images are attempted, and the step fails at the end if any
  build failed — a broken Dockerfile therefore fails the check and, once required,
  blocks merge. Build-only posture per NFR-07: no registry login, no push, no
  privileged secrets, `permissions: contents: read` only (Section 20.4 item 3);
  image CVE scanning stays M6 and the bridge is not built as an image (Section
  10.11). One stable `container-build` status check instead of a per-image matrix, so
  required-check configuration does not drift as images are added. Docker layer
  caching is added by MT-0.3-05.
- **MT-0.3-04** — Security gates created in `.github/workflows/security.yaml`.
  `dependency-scan`: backend and bridge audit their synced uv environments
  (`uv sync` + `uvx pip-audit --path <pkg>/.venv`, lockfile graph) and web audits its
  npm dependency tree (`npm ci` + `npm --prefix web audit`), with severity thresholds
  documented in the workflow header and CONTRIBUTING.md per ecosystem: **Python =
  LOW and above (every advisory fails — pip-audit has no severity filter but does
  have per-advisory `--ignore-vuln` waivers)** and **npm = CRITICAL and above** (npm
  audit has no per-advisory ignore, so an unfixable upstream advisory would otherwise
  hard-block all merges with no remediation path; non-failing findings remain visible
  in the job log). The threshold decision is exercised, not theoretical: the clean
  tree currently carries GHSA-vfj7-8cjw-p6xm (braces, HIGH, dev-only eslint chain,
  **no fixed braces release exists** — OSV affected 0..3.0.3, upstream
  micromatch/braces#70, `npm audit fix --force` rejected as it downgrades
  eslint-config-next to 14.x), so a **recorded waiver** sits in the workflow header
  with owner and expiry (re-evaluate when braces ships a fix or at WP-4.1, then
  tighten back to `low`). Waiver process documented for new findings (never a
  disabled gate): fix preferred; Python via commented, owned, time-bounded
  `--ignore-vuln <GHSA-ID>` lines; npm via `overrides` pin or a reviewed threshold
  decision recorded beside the header. `secret-scan`: runs
  `uvx pre-commit run detect-secrets --all-files` — the SAME hook id, repo and pinned
  revision (Yelp/detect-secrets v1.5.0) as `.pre-commit-config.yaml`, i.e. the
  identical pattern source as the local hooks, over every tracked file; pairing with
  human review of config changes noted for the RISK-08 blind spot, inline-pragma
  documented as the only false-positive path. Both jobs are required checks (a leaked
  credential or vulnerable dependency blocks merge), `permissions: contents: read`,
  zero credentials in the file (Section 20.4 item 3). Recorded follow-ups, not silent
  skips: mobile/pub scanning with WP-5.5, managed scanner M3, image CVEs M6.
  **Local verification executed:** all four workflow files parse as YAML, and
  `uvx pre-commit run detect-secrets --files <the four workflows + CONTRIBUTING.md +
  WP-0.3 CHANGELOG.md + infra/compose/.env.example + .pre-commit-config.yaml>` passes
  (an earlier draft step name `secrets: detect-secrets …` was caught by the scan as a
  keyword-secret false-positive shape and renamed — the gate demonstrably fails on a
  keyword hit, i.e. it works). Then the FULL eventual-tracked file set
  (`git ls-files -c -o --exclude-standard`, 423 files) was scanned in two batches:
  one pre-existing hit surfaced — `docs/plan/conventions/pagination.md:56`
  (Base64 High Entropy on the illustrative `next_cursor` example, the string's only
  occurrence in the repository) — and was cleared by replacing the opaque example
  value with the self-describing `opaque-cursor-example` (both candidate replacements
  were probed against the scanner first; the canonical contract — key name, envelope
  shape, absence semantics — is unchanged). Re-scan of the full set: **both batches
  pass**, and a planted fake credential in a probe file **fails** the gate — positive
  and negative paths proven locally without committing anything. Dependency-scan
  commands executed locally against the clean tree: `uvx pip-audit --path
  backend/.venv` → 0 findings (exit 0), `uvx pip-audit --path bridge/.venv` → 0
  findings (exit 0), `npm --prefix web audit --audit-level=critical` → exit 0 with
  the recorded braces HIGH shown in the log (i.e. the threshold behaves exactly as
  documented), and the strict `--audit-level=low` run was executed too — it exits 1
  on the unfixable braces advisory, which is precisely why the threshold decision
  above is recorded.
- **MT-0.3-05** — Build caching added to the existing jobs (no gate touched):
  Python via `astral-sh/setup-uv` `enable-cache: true` +
  `cache-dependency-glob: "**/uv.lock"` (all setup-uv steps in `lint-type.yaml`,
  `test.yaml`, `security.yaml`); npm via `actions/setup-node` `cache: npm` +
  `cache-dependency-path: web/package-lock.json` (the web steps in the same three
  workflows); Docker layers via `docker/setup-buildx-action@v3` +
  `--cache-from/--cache-to type=gha` with one stable `img-<cleaned Dockerfile path>`
  scope per image and `mode=max`, `ignore-error=true` (cache-export problems such as
  fork-PR cache restrictions can never fail the build gate — the gate stays about
  build success; layers are content-addressed so Dockerfile/context changes
  invalidate exactly the affected layers). Invalidation on dependency change follows
  from lockfile-hash keys for uv/npm and content addressing for layers (no stale-cache
  false greens); caches contain dependency artifacts and image layers only, no gate
  outputs and no credential material (Section 20.4 item 3). No `continue-on-error`,
  no skipped or soft-failed job was introduced. CONTRIBUTING.md gained "Pipeline
  duration and caching": the cache/invalidation table, the candidate follow-ups left
  outside scope (Flutter SDK cache, pre-commit hook-env cache) and the measured-
  duration table + measurement procedure (`gh run view --json jobs`) — **cold/warm
  durations are marked TBD pending the first CI runs on GitHub**, since this workspace
  cannot execute GitHub Actions (recorded as a deviation in the WP report); the
  under-10-minutes criterion is re-verified at that point and re-measured per
  milestone.
