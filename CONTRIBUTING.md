# Contributing

This repository is a single monorepo (ADR-001 in the parent
[architecture plan](ai_agent_task_orchestrator_architecture_plan.md)). Before changing
anything, read the package-boundary section below so every change lands in the package that
owns it.

---

## Package boundaries

Each package owns exactly one responsibility. Do not move concerns across boundaries; if a
change seems to need that, raise it as an open question against the parent plan first
(parent plan Section 20.1, rule 5).

### Backend (`backend/`)

- **Owns:** the Django control plane — API, task state machine, leases, events, policy,
  notifications, and persistence (parent plan Sections 8–9).
- **Never owns:** access to Git repositories or host filesystem content. The backend never
  touches repositories (Principle P2, ADR-007); all repository evidence arrives from
  host-side components (bridge, Merge Executor).
- **Stack:** Django 5.x, Python 3.12+, managed with `uv`.

### Bridge (`bridge/`)

- **Owns:** the MCP bridge and Merge Executor — tools, prompts, client discovery, the Git
  helper, evidence upload, and host-side merges (parent plan Sections 10, 16).
- **Never owns:** task state or policy decisions; it reports to the backend API and never
  writes backend data directly.
- **Stack:** Python, `uv`-managed, MCP Python SDK; layout `src/`, `capability_table/`,
  `tests/`.

### Web (`web/`)

- **Owns:** the Next.js (App Router) operations board UI (parent plan Section 13).
- **Never owns:** direct database access or repository access; it is an API-only client of
  the backend over HTTP and SSE.
- **Stack:** Next.js, React, Tailwind CSS, shadcn/ui.

### Mobile (`mobile/`)

- **Owns:** the Flutter mobile client — monitoring, approvals, and push handling (parent
  plan Section 14).
- **Never owns:** direct database or repository access; API-only client of the backend.
  Authentication follows the layered model in ADR-006.
- **Stack:** Flutter (Dart), Riverpod, `local_auth`, FCM.

### Schemas (`schemas/`)

- **Owns:** shared contracts — manifest schema, OpenAPI snapshot, MCP tool schemas.
- **Rule:** all packages consume these contracts; contract changes are reviewed as schema
  diffs (parent plan Section 20.4, item 4).

### Infra (`infra/`)

- **Owns:** deployment and operations configuration only — `compose/`, `cloudflare/`,
  `backup/` (parent plan Sections 15–17).
- **Never owns:** application code or environment-specific secrets (secrets live in
  environment variables, never in Git — parent plan Section 12.4).

### Docs (`docs/`)

- **Owns:** the documentation tree — `plan/`, `adr/`, `runbooks/`, `agent-guides/`
  (see [docs/plan/](docs/plan/)).
- **Never owns:** executable code or configuration consumed at runtime.

### End-to-end (`e2e/`)

- **Owns:** scenario scripts that exercise the whole stack against the Compose deployment
  (parent plan Section 18).
- **Never owns:** package-internal unit or integration tests (those live inside each
  package, e.g. `backend/tests/`, `bridge/tests/`).

---

## Tooling commands

One documented command each for lint, format, and type check per package. These are the
single source of truth: pre-commit hooks and CI invoke the identical commands.

### Backend (Python)

Formatter/linter: **Ruff**; type checker: **mypy** (`strict`). Both are pinned identically
in `backend/pyproject.toml` and `bridge/pyproject.toml`. Python **3.12** is pinned via
`.python-version` in each package (and at the repository root).

| Concern | Command (from the repository root) |
|---|---|
| Sync dependencies | `uv sync --directory backend` |
| Lint | `uv run --directory backend ruff check .` |
| Format | `uv run --directory backend ruff format .` |
| Format check (used by hooks/CI) | `uv run --directory backend ruff format --check .` |
| Type check | `uv run --directory backend mypy .` |
| Django system check | `uv run --directory backend python manage.py check` |
| Migration drift check | `uv run --directory backend python manage.py makemigrations --check --dry-run` |
| Regenerate OpenAPI snapshot | `uv run --directory backend python manage.py spectacular --file ../schemas/openapi.yaml` |

**OpenAPI snapshot** (WP-1.1, MT-1.1-04): `schemas/openapi.yaml` is generated —
never hand-edited. Any change to routes, serializers or `SPECTACULAR_SETTINGS`
must be followed by the regen command above; CI regenerates the document and
fails on drift against the committed snapshot (Section 18 contract gate). The
document is served by the backend at `/api/v1/schema` (Swagger UI at
`/api/v1/schema/swagger-ui`) — the path is fixed and recorded in the WP-1.1
changelog because clients hardcode or discover it.

The same artifact feeds the web client (NFR-11, MT-4.1-03): the typed client
under `web/lib/api/generated/` is regenerated from it with
`npm --prefix web run generate:api`, and CI runs
`npm --prefix web run check:api`, which fails when the committed client and a
fresh generation differ (stale client, hand edit, or a schema change whose
regen was not recommitted). After a reviewed OpenAPI change, run the regen
command above **and** the web generate command, then commit both.

**Settings layout** (WP-1.1, MT-1.1-01 decision — one module per environment, no
second mechanism): `backend/apps/core/settings/` holds `base.py` (every shared
setting, read from its canonical `ORCHESTRATOR_*` name with a documented default
per parent plan 9.10 and [configuration.md](docs/plan/conventions/configuration.md)),
plus `dev.py` and `prod.py` which import the base and differ only in validation
strictness — `prod.py` implements the Section 16.2 fail-fast refusal of weak or
missing required values. The module is selected exactly once, through Django's own
`DJANGO_SETTINGS_MODULE`:

| Run context | Selected module | Why |
|---|---|---|
| Host (`manage.py`, Uvicorn, pytest, CI) | `apps.core.settings.dev` — the default set in `manage.py` and `config/asgi.py` | a fresh clone boots with no secrets committed (plan 20.4 item 3) |
| Container image (any Compose render) | `apps.core.settings.prod` — the image `ENV`; the compose dev overlay overrides it to `...dev` | the prod render enforces Section 16.2; the dev render stays one-command startable |

Run commands (parent plan Section 6.6 — ASGI via Uvicorn):

| Concern | Command (from the repository root) |
|---|---|
| Run dev server (ASGI) | `uv run --directory backend python -m uvicorn config.asgi:application --host 127.0.0.1 --port 8000 --reload --no-access-log` |

(`--no-access-log` is deliberate: request lines are emitted as structured JSON by
the backend's own request logging — MT-1.1-02 — so Uvicorn's plain-text access log
never duplicates or replaces them.)

### Bridge (Python)

Formatter/linter: **Ruff**; type checker: **mypy** (`strict`) — the same tools and pinned
versions as the backend, so CI and hooks run one identical command shape everywhere. The
bridge is `uv`-managed with a committed `bridge/uv.lock` (parent plan Section 6.6).

| Concern | Command (from the repository root) |
|---|---|
| Sync dependencies | `uv sync --directory bridge` |
| Lint | `uv run --directory bridge ruff check .` |
| Format | `uv run --directory bridge ruff format .` |
| Format check (used by hooks/CI) | `uv run --directory bridge ruff format --check .` |
| Type check | `uv run --directory bridge mypy .` |

### Web (Next.js)

Package manager: **npm** (lockfile `web/package-lock.json` — recorded here per MT-0.1-03;
CI and hooks must use npm too). ESLint flat config via `eslint-config-next`
(core-web-vitals + typescript), Prettier for formatting, `tsc --noEmit` for type check.

| Concern | Command (from the repository root) |
|---|---|
| Sync dependencies (fresh clone) | `npm ci --prefix web` |
| Lint | `npm --prefix web run lint` |
| Type check | `npm --prefix web run typecheck` |
| Format | `npm --prefix web run format` |
| Format check (used by hooks/CI) | `npm --prefix web run format:check` |
| Regenerate typed API client | `npm --prefix web run generate:api` |
| Typed client drift check (used by CI) | `npm --prefix web run check:api` |

### Mobile (Flutter)

Analyzer/lint: **flutter analyze** with the **flutter_lints** rule set
(`mobile/analysis_options.yaml`). Package manager: the Dart/Flutter SDK (`pub`).
Requires a Flutter SDK on `PATH` (host setup; CI pins a specific Flutter version).

| Concern | Command |
|---|---|
| Sync dependencies (repo root) | `flutter pub get -C mobile` |
| Analyze (type check) | `flutter analyze` — run from `mobile/` (it auto-runs `pub get`) |
| Format | `dart format mobile/` (repo root) |
| Format check (used by hooks/CI) | `dart format --set-exit-if-changed mobile/` (repo root) |

### Git hooks

Hooks run the exact commands documented above (single source of truth — the hook
entries in `.pre-commit-config.yaml` are verbatim copies) plus a secret scan over every
staged file (conservative default patterns covering config files and `.env`-style
assignments, parent plan Section 18 / RISK-08; scanner: `detect-secrets`). Real `.env`
files are excluded by `.gitignore`, so they can never be staged.

Install the hooks on a fresh clone with one command:

```bash
uvx pre-commit install
```

Run the full set manually with `uvx pre-commit run --all-files`. Prerequisites on
`PATH`: `uv`, Node.js (`npm`), the Flutter/Dart SDK, and `git` — the same prerequisites
as the commands above. If a package has never been set up on this machine, sync it first
(`uv sync --directory backend`, `uv sync --directory bridge`, `npm ci --prefix web`,
`flutter pub get -C mobile`).

---

## Continuous integration

**Platform: GitHub Actions** — the repository host (recorded here because the parent
plan does not name a CI platform; MT-0.3-01 risk note). Workflows live in
`.github/workflows/`, one file per concern — never one combined pipeline:

| Workflow | Jobs (status-check names) | Section 18 gates covered |
|---|---|---|
| `lint-type.yaml` | `lint`, `type-check`, `migration-schema-diff` | lint + format checks, type checks, migration/schema-diff placeholder |
| `test.yaml` | `unit-tests`, `integration-tests`, `coverage-gate` | unit tests, integration tests (against Postgres + Redis), Section 18 coverage target (85% on the state machine and lease/sweeper logic — MT-1.15-05) |
| `container-build.yaml` | `container-build` | container build |
| `security.yaml` | `dependency-scan`, `secret-scan` | dependency scanning, secrets scanning |

Every workflow runs on pull requests, on pushes to `main`, and on manual dispatch.

**CI runs the exact commands documented in the tables above** — the same strings the
pre-commit hooks copy verbatim, so hooks, docs and CI cannot drift. Hooks additionally
filter by changed paths; CI always runs every package. To change a command, change it
in the table above first, then mirror it in `.pre-commit-config.yaml` and the workflow.

### Required status checks (merge gate)

Parent plan 19.1 (WP-0.3): a failing gate blocks merge. The nine check names listed
in the table above are the required status checks for `main`. Configure them once in
the GitHub UI (**Settings → Branches →** add a branch protection rule for `main`,
enable *Require status checks to pass before merging*, tick all nine contexts, enable
*Include administrators*), or with the GitHub CLI as a repository admin — run after
the workflows have run at least once so every check name exists:

```bash
gh api -X PUT "repos/<owner>/<repo>/branches/main/protection" --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "lint", "type-check", "migration-schema-diff",
      "unit-tests", "integration-tests", "coverage-gate",
      "container-build",
      "dependency-scan", "secret-scan"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

This workspace's `gh` CLI is unauthenticated, so the rule has not been applied from
here — enabling it is a post-push, repository-admin step. Until it is enabled the
jobs report their status but do not physically block a merge.

### Test commands (unit and integration)

MT-0.3-02 establishes the test entry points (WP-0.1 documented only lint, format and
type check). This table is the single source of truth for tests, exactly like the
tooling tables above — the CI jobs copy it verbatim:

| Concern | Command (from the repository root) | Empty-suite behavior (documented allow-empty) |
|---|---|---|
| Unit — backend | `uv run --directory backend pytest` | CI skips explicitly while no `test_*.py` exists under `backend/` (excluding `.venv`) |
| Unit — bridge | `uv run --directory bridge pytest` | CI skips explicitly while no `test_*.py` exists under `bridge/` |
| Unit — web | `npm --prefix web run test` | CI skips explicitly while no `web/**/*.test.*` or `web/**/*.spec.*` file exists (script + runner arrive with WP-4.11) |
| Unit — mobile | `flutter test` (run from `mobile/`) | CI skips explicitly while no `mobile/test/*_test.dart` exists |
| Integration — backend | `uv run --directory backend pytest tests/integration --ds apps.core.settings.dev` | CI skips explicitly while no `test_*.py` exists under `backend/tests/integration/`; the path is relative to `--directory`'s cwd and `--ds` selects the Postgres/Redis settings module (without it the unit SQLite settings skip the layer — MT-1.4-02) |
| Integration — bridge | `uv run --directory bridge pytest bridge/tests/integration` | same, for `bridge/tests/integration/` |
| Coverage gate — backend | `uv run --directory backend pytest --cov=apps.tasks.state_machine --cov=apps.leases --cov-append -q` then `uv run --directory backend pytest --ds apps.core.settings.dev tests/integration/test_claim_race_postgres.py tests/integration/test_sweeper_chaos_postgres.py tests/integration/test_idempotency_postgres.py tests/auth tests/test_authorization_matrix.py --cov=apps.tasks.state_machine --cov=apps.leases --cov-append --cov-report=term-missing --cov-report=json:coverage-report.json -q` then `uv run --directory backend python scripts/coverage_gate.py coverage-report.json apps.tasks.state_machine apps.leases --fail-under 85` | The two pytest invocations share one coverage data file (Section 18's unit layer, then the four WP-1.15 suites on Postgres); only the third command is the gate. The Postgres invocation needs `ORCHESTRATOR_DATABASE_URL` pointed at a disposable database locally (pytest-django creates `test_<name>` itself). Section 18 target: >= 85% line coverage **per gated module**; the gate fails when either module drops below (MT-1.15-05) |

- **Allow-empty is explicit, never silent:** the `unit-tests` / `integration-tests`
  jobs detect each suite, print an `allow-empty` notice for every empty one, and run
  whatever a suite contains once it is non-empty. No placeholder tests are invented,
  and a non-empty suite that fails always fails the job (no-new-failures).
- The Python runner (`pytest`) becomes a dev dependency of `backend`/`bridge` with
  the first work package that lands test files — CI fails closed if a test file
  appears before its runner is declared.
- Integration jobs receive endpoints only from CI-provided environment —
  `ORCHESTRATOR_DATABASE_URL` / `ORCHESTRATOR_CACHE_URL` (WP-0.5 env naming) point at
  ephemeral, runner-local `postgres:16-alpine` + `redis:7.4-alpine` service
  containers (same image pins as `infra/compose/`, NFR-06 parity). The containers use
  trust auth on loopback: no password exists in the workflow, in a secret, or in any
  cache (Section 20.4 item 3, RISK-14).
- Web/mobile integration and end-to-end scenarios run against the Compose stack in
  their own work packages (Section 18 end-to-end row) — not in `integration-tests`.

### Dependency and secret scanning (threshold and waivers)

MT-0.3-04 documents the two scan gates in `security.yaml` (both required checks):

- **Severity thresholds (documented per ecosystem, with the reason):**
  - **Python — LOW and above: every advisory fails.** The steps run `uvx pip-audit`
    with no severity filter (any reported vulnerability exits non-zero), which is
    sustainable because pip-audit supports per-advisory waivers (`--ignore-vuln`).
  - **npm — CRITICAL and above fails** (`npm --prefix web audit --audit-level=critical`
    over the whole tree, dev tooling included; non-failing findings stay visible in
    the job log). npm audit has no per-advisory ignore list, so a single unfixable
    upstream advisory would otherwise block every merge with no remediation path.
    **Recorded waiver:** GHSA-vfj7-8cjw-p6xm (braces, HIGH — stack-exhaustion DoS,
    dev-only eslint chain, no fixed braces release exists: OSV affected 0..3.0.3,
    upstream micromatch/braces#70; `npm audit fix --force` would downgrade
    eslint-config-next to 14.x and is rejected). Owner: repository maintainer.
    Expiry: re-evaluate when braces ships a fixed release (or at WP-4.1), then
    tighten the threshold back to `low`.
  - Mobile/pub scanning is a recorded follow-up with the real Flutter app (WP-5.5);
    external managed-secret-scanner integration is scheduled M3 (RISK-08); image
    CVE scanning is M6.
- **Waiver process for a NEW flagged dependency (the gate is never disabled):**
  1. Preferred: upgrade or pin to a fixed version — a normal dependency-bump PR.
  2. Python with no fixed release: add a commented, owned, time-bounded waiver line
     next to the audit step in `security.yaml`
     (`# waiver: --ignore-vuln <GHSA-ID> — <owner>, <justification>, expires <date>`)
     and only then append that `--ignore-vuln` flag.
  3. npm has no per-advisory ignore list: pin an unaffected alternative via
     `overrides` if one exists, otherwise raise an issue and record an explicit,
     reviewed threshold decision beside the header of `security.yaml` (as done for
     the braces waiver) — still not a deleted or `continue-on-error` job.
- **Secret scan** is the same scanner and pattern source as the local hook:
  `uvx pre-commit run detect-secrets --all-files` resolves the hook id, repository and
  pinned revision from `.pre-commit-config.yaml` (Yelp/detect-secrets v1.5.0) over
  every tracked file. Pattern-based scanning can miss leaks (RISK-08), so config and
  environment-file changes also get human review; a finding blocks merge. A false
  positive is marked with the scanner's inline `# pragma: allowlist secret` comment on
  the offending line, with a reason — never by turning the job off.

### Pipeline duration and caching

MT-0.3-05 keeps the whole pipeline inside the WP-0.3 budget (parent plan 19.1:
**under 10 minutes for the skeleton, warm**) without weakening any gate:

| Cache | Where | Key / invalidation |
|---|---|---|
| Python (`uv`) | `astral-sh/setup-uv` `enable-cache` in `lint-type`, `test`, `security` | `**/uv.lock` via `cache-dependency-glob` — a dependency bump changes the key, so a stale cache can never green a changed graph |
| npm | `actions/setup-node` `cache: npm` in `lint-type`, `test`, `security` | `web/package-lock.json` via `cache-dependency-path` — same invalidation rule |
| Docker layers | `type=gha` buildx cache exporters in `container-build` | one stable scope per Dockerfile path; layers are content-addressed, so a Dockerfile/context change rebuilds exactly the affected layers |

Caches hold dependency artifacts and image layers only — never gate outputs, `.env`
files or credential material (Section 20.4 item 3). No gate was skipped, weakened or
made non-blocking to save time. Candidate follow-ups outside MT-0.3-05's scope (add
only if the budget demands them): the Flutter SDK cache
(`subosito/flutter-action` `cache: true`) and the pre-commit hook-environment cache.

**Measured durations** (recorded here per MT-0.3-05; the budget is re-measured at
every milestone — a miss raises a follow-up, gates are never disabled):

| Run | Date | Total duration | Measurement |
|---|---|---|---|
| Cold (empty caches) | TBD — first CI run after push | TBD | Actions run page, or `gh run view <run-id> --json jobs` → `max(completedAt) − min(startedAt)` across jobs |
| Warm (immediately repeated run) | TBD — second CI run | TBD | same; must be **under 10:00** with every required check green |

Procedure: push the workflows, trigger each workflow once (cold), trigger again
without changes (warm), and fill in both rows. A dependency bump must show as a cache
key change (`enable-cache` / `cache-dependency-path` keys) and a rebuild of the
affected layers — that is the no-stale-cache check.

## Documentation

- [Plan documents](docs/plan/) — parent architecture plan index and micro-document series
- [Architecture decision records](docs/adr/) — ADR-001 through ADR-013 (statuses tracked in the index; records written by WP-0.4)
- [Runbooks](docs/runbooks/) — one stub per parent plan Section 17 runbook (content: WP-6.5)
- [Agent client guides](docs/agent-guides/) — per-client setup page stubs (content: WP-2.11)

## Changelog

Every work package keeps a changelog (parent plan Section 20.4, item 7). For WP-0.1, add a
short note to
[`plan-doc-series/m0-foundations/wp-0.1-monorepo-scaffolding/CHANGELOG.md`](plan-doc-series/m0-foundations/wp-0.1-monorepo-scaffolding/CHANGELOG.md)
whenever you complete a change in this work package.
