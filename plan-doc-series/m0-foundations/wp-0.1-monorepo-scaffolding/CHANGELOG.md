# WP-0.1 — Monorepo scaffolding and tooling: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-0.1-01** — Root layout created per parent plan Appendix A (ADR-001): `docs/`
  (`plan/`, `adr/`, `runbooks/`, `agent-guides/`), `backend/` with 11 app placeholders
  (`accounts`, `projects`, `tasks`, `leases`, `attachments`, `audit`, `merge`, `events`,
  `notifications`, `agents`, `core`) plus `tests/`, `bridge/` (`src/`, `capability_table/`,
  `tests/`), `web/`, `mobile/`, `schemas/`, `infra/` (`compose/`, `cloudflare/`, `backup/`),
  `e2e/` — each empty directory carries a `.gitkeep`. Added root `README.md` (links
  `docs/plan/`, names per-package command locations) and `CONTRIBUTING.md` with one
  package-boundary section per package. Decision recorded: layout follows Appendix A of the
  parent plan; tooling configs are deliberately deferred to MT-0.1-02..05.
- **MT-0.1-02** — Python tooling configured for `backend/` and `bridge/`: `pyproject.toml`
  in each package with Ruff (format + lint: E, W, F, I, B, UP; line length 100, target
  py312) and mypy (`strict`, `python_version = "3.12"`), dev tools pinned to the same
  versions in both packages (`ruff==0.17.0`, `mypy==2.4.0`). Tool brand decision recorded:
  Ruff + mypy (parent plan fixes the languages, not the tool brands). Bridge is
  uv-managed with committed `bridge/uv.lock`; Python 3.12 pinned via `.python-version` at
  the repository root and in each package directory (uv honors the pin per project —
  verified). Added `backend/tests/__init__.py` and `bridge/tests/__init__.py` package
  markers so the documented mypy command has a source file on the initial skeleton
  (mypy exits non-zero on a directory with no Python files). One documented command each
  for lint, format, format check, and type check per package in `CONTRIBUTING.md`.
- **MT-0.1-03** — Web tooling configured in `web/`: `package.json` with `lint`, `typecheck`,
  `format`, and `format:check` scripts; ESLint 10 flat config (`eslint.config.mjs`) using
  `eslint-config-next` (core-web-vitals + typescript) plus `eslint-config-prettier` per the
  official Next.js docs; Prettier config (`.prettierrc.json`: printWidth 100, single
  quotes) with `.prettierignore`; `tsconfig.json` (strict, bundler resolution, JSX
  preserve) and committed `next-env.d.ts`. Minimal App Router placeholder
  (`app/layout.tsx`, `app/page.tsx`) exists so the tooling commands have input files —
  the real app lands in WP-4.1. Package-manager decision recorded: **npm** with committed
  `web/package-lock.json` (Next 16.4, React 19.3). Placeholder `.gitkeep` removed from
  `web/`. End-of-wave gate finding: `typescript-eslint` (via `eslint-config-next`)
  rejected TypeScript 7, so the TypeScript version is pinned to `^5.9.3`; lint, type
  check, and format check then passed.
- **MT-0.1-04** — Mobile tooling configured in `mobile/`: `pubspec.yaml` as a minimal
  Flutter package placeholder (`orchestrator_mobile`, Flutter SDK dependency +
  `flutter_lints: ^6.0.0` dev dependency resolved by `flutter pub add`) and
  `analysis_options.yaml` including `package:flutter_lints/flutter.yaml` as the committed
  baseline rule set. Documented commands: `flutter pub get -C mobile` (resolution,
  verified), `flutter analyze` from `mobile/` (type check), and
  `dart format --set-exit-if-changed mobile/` (format check). Placeholder `.gitkeep`
  removed from `mobile/`. App content itself deferred to WP-5.5.
- **MT-0.1-05** — Pre-commit hooks added: root `.pre-commit-config.yaml` with
  `detect-secrets` (`v1.5.0`) as the secret-scan hook over all staged files, plus local
  hooks for every documented per-package command (backend/bridge: ruff check,
  `ruff format --check`, mypy; web: eslint, `tsc --noEmit`, `prettier --check`; mobile:
  `flutter analyze`, `dart format --set-exit-if-changed`) — entries are verbatim copies
  of the `CONTRIBUTING.md` commands (single source). Scanner decision recorded:
  **detect-secrets** instead of gitleaks, because gitleaks' pre-commit hooks require a Go
  toolchain that is not guaranteed on contributor machines; detect-secrets needs no
  config file, so no `.gitleaks.toml` is committed (MT-0.1-05 target path allows an
  equivalent scanner config only "if the chosen scanner needs one"). Root `.gitignore`
  added: Python/Node/Flutter artifacts plus `.env` / `.env.*` exclusion with an explicit
  `!.env.example` exception (keeps the WP-0.2 template trackable). Install command
  recorded: `uvx pre-commit install`.
- **MT-0.1-06** — Documentation skeleton created under `docs/`: `plan/README.md` (index
  to the root parent plan, `plan-doc-series/overview.md`, `roadmap.md`, and the WP-0.4
  decision review notes), `runbooks/README.md` plus seven stubs matching the parent plan
  Section 17 list (`stuck-lease`, `failed-merge`, `tunnel-down`, `restore-from-backup`,
  `rotate-tokens`, `add-a-project`, `onboard-new-agent-client`) each naming WP-6.5 (M6)
  as content owner, and `agent-guides/README.md` (per-client guide index, client list
  provisional until OQ-05 is decided in WP-0.4; content owner WP-2.11). Root
  `README.md` and `CONTRIBUTING.md` now link the full documentation tree. Coordination
  note: `docs/adr/` was populated concurrently by WP-0.4 (MT-0.4-01/02 — all thirteen
  ADR records and an index already exist with status `accepted`), so the MT-0.1-06
  "pending" index was intentionally NOT overwritten; regressing it to `pending` would
  misrepresent decision state (MT-0.1-06 risk note). Placeholder `.gitkeep` removed
  from all four `docs/` subdirectories.
- **End-of-wave verification (all six micro-tasks)** — Gates run after all files were
  written: backend and bridge `ruff check` / `ruff format --check` / `mypy` green on
  Python 3.12; web `eslint` / `tsc --noEmit` / `prettier --check` green; mobile
  `flutter analyze` and `dart format --set-exit-if-changed` green (format check verified
  to exit 1 on an unformatted file); `uvx pre-commit install` completed and all 12 hooks
  pass over the full 401-file tree, including the secret scan (no findings on the parent
  plan or any config file). Rejection verified without staging: a format-violating file
  and an F821 lint violation were both rejected by their hooks, and a fake-credential
  file (`AKIA…` / `ghp_…` examples) was rejected by the secret scan; all probe files
  were deleted immediately. Fixes made during verification: hook `name` values quoted
  (YAML colons), detect-secrets hook id corrected to `detect-secrets`, and the
  `mobile-analyze` hook switched from `bash -c` to a `python -c` cwd wrapper (the host's
  Flutter SDK checkout has CRLF shell scripts, which breaks bash shebangs; the wrapper
  resolves `flutter.bat` on Windows and `flutter` on POSIX).
