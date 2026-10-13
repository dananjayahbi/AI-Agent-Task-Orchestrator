"""MT-3.4-03 — rules R3 (critical), R4 (migrations), R5 (sensitive), table-driven.

Run with ``pytest backend/tests -k policy_rules_r3_r4_r5 -q``:

* R3/R4/R5(a) glob matches against the policy's Section 7.2 lists,
  through the shared matcher (never a second implementation).
* R5(b) scans the **stored patch's added lines** with the documented
  pattern set — the backend mirror of the bridge's Section 10.8 helper
  (asserted equal here: one conceptual list).
* Absent patch body (oversize/missing artifact) fails R5 closed
  (MT-3.4-03 risk note) — never a vacuous pass.
* Combined case: R3+R4+R5 all fail with all three reasons listed.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from apps.audit.policy import DECISION_APPROVE, DECISION_ESCALATE
from apps.audit.policy.rules import SECRET_PATTERNS, added_lines_of

from .wp34_helpers import PolicyCase, clean_context, run_policy_table

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BRIDGE_PATTERNS = (
    _REPO_ROOT / "bridge" / "src" / "orchestrator_bridge" / "git_helper" / "secret_patterns.toml"
)

# pragma: allowlist secret
_AWS_LITERAL_LINE = 'api_key = "AKIA1234567890ABCDEF"'  # pragma: allowlist secret


def test_r3_r4_r5_table() -> None:
    """The Section 9.4 glob trio: pass/fail each and combined."""
    run_policy_table(
        [
            PolicyCase(
                "clean-patch-passes-all-three",
                clean_context(
                    critical_path_globs=(".github/workflows/*",),
                    migration_path_globs=("alembic/versions/*",),
                    sensitive_config_globs=(".env*", "**/*.pem"),
                ),
                DECISION_APPROVE,
            ),
            PolicyCase(
                "r3-fail-critical-glob",
                clean_context(
                    target_scope=(".github/**", "src/**"),
                    changed_files=(".github/workflows/ci.yml",),
                ),
                DECISION_ESCALATE,
                frozenset({"R3"}),
                "critical_path_changed",
            ),
            PolicyCase(
                "r4-fail-migration-glob",
                clean_context(
                    target_scope=("alembic/**", "src/**"),
                    changed_files=("alembic/versions/0001_init.py",),
                ),
                DECISION_ESCALATE,
                frozenset({"R4"}),
                "migration_detected",
            ),
            PolicyCase(
                "r5-fail-sensitive-glob",
                clean_context(target_scope=(".env*", "src/**"), changed_files=(".env.local",)),
                DECISION_ESCALATE,
                frozenset({"R5"}),
                "sensitive_config_changed",
            ),
            PolicyCase(
                "r5-fail-secret-in-added-lines",
                clean_context(added_lines=(_AWS_LITERAL_LINE,)),
                DECISION_ESCALATE,
                frozenset({"R5"}),
                "sensitive_config_changed",
            ),
            PolicyCase(
                "r5-fail-body-unavailable-fail-closed",
                clean_context(added_lines=None),
                DECISION_ESCALATE,
                frozenset({"R5"}),
                "sensitive_config_changed",
            ),
            PolicyCase(
                "combined-r3-r4-r5-all-fail",
                clean_context(
                    target_scope=(".github/**", "alembic/**", ".env*", "src/**"),
                    changed_files=(
                        ".github/workflows/ci.yml",
                        "alembic/versions/0001_init.py",
                        ".env.local",
                    ),
                ),
                DECISION_ESCALATE,
                frozenset({"R3", "R4", "R5"}),
                "critical_path_changed",  # deterministic primary: first failing rule
            ),
            PolicyCase(
                "unparseable-policy-glob-fails-closed",
                clean_context(critical_path_globs=("src/**/broken[",)),
                DECISION_ESCALATE,
                frozenset({"R3"}),
                "critical_path_changed",
            ),
        ]
    )


@pytest.mark.parametrize(
    "line",
    [
        "-----BEGIN RSA PRIVATE KEY-----",  # pragma: allowlist secret
        'token = "AKIA1234567890ABCDEF"',  # pragma: allowlist secret
        'password = "hunter2hunter2"',  # pragma: allowlist secret
        "Authorization: Bearer aGVsbG8wd29ybGRmYWtlY3JlZGVudGlhbA",
        'github = "ghp_abcdefghijklmnopqrstuv"',  # pragma: allowlist secret
        'install = "github_pat_11ABCDEFGHijklmnopQRSTUVWX"',  # pragma: allowlist secret
    ],
    ids=[
        "private-key-block",
        "aws-access-key-id",
        "secret-assignment-password",
        "bearer-token-literal",
        "github-token-pat",
        "github-token-installation",
    ],
)
def test_every_documented_pattern_fires_in_added_lines(line: str) -> None:
    """Each pattern of the documented set flags an added line (§12.1)."""
    run_policy_table(
        [
            PolicyCase(
                f"r5-pattern-{line[:12]}",
                clean_context(added_lines=(line,)),
                DECISION_ESCALATE,
                frozenset({"R5"}),
                "sensitive_config_changed",
            )
        ]
    )


def test_benign_added_lines_pass_the_scan() -> None:
    """Conservative patterns: innocent work is not escalated (risk note)."""
    from apps.audit.policy import evaluate

    benign = (
        "print('hello')",
        "api_key = get_env('API_KEY')",  # not a literal
        "token = ''",  # below the 8-char floor
        "# token: rotate quarterly",
    )
    result = evaluate(clean_context(added_lines=benign))
    r5 = next(outcome for outcome in result.rule_results if outcome.rule == "R5")
    assert r5.passed is True


def test_secret_pattern_set_mirrors_the_bridge_helper() -> None:
    """One conceptual list with the Section 10.8 helper (MT-3.4-03 risk)."""
    document = tomllib.loads(_BRIDGE_PATTERNS.read_text(encoding="utf-8"))
    bridge = {(row["id"], row["severity"], row["regex"]) for row in document["patterns"]}
    backend = {(p.id, p.severity, p.regex.pattern) for p in SECRET_PATTERNS}
    assert backend == bridge, "backend scan and bridge helper share one pattern list"


def test_added_lines_of_tracks_hunk_boundaries() -> None:
    """Header lines never scan; in-hunk ``+++`` content does (pure parse)."""
    patch = (
        "diff --git a/src/app.py b/src/app.py\n"
        "--- a/src/app.py\n"
        "+++ b/src/app.py\n"
        "@@ -1,2 +1,3 @@\n"
        " context\n"
        "+added-one\n"
        "+++ weird-content-line\n"  # in-hunk: added content "++ weird-…"
        "-removed\n"
        "diff --git a/next.py b/next.py\n"
        "--- a/next.py\n"
        "+++ b/next.py\n"
        "@@ -1 +1 @@\n"
        "+added-two\n"
    )
    assert added_lines_of(patch) == ("added-one", "++ weird-content-line", "added-two")
    assert added_lines_of("") == ()
