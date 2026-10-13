"""MT-2.10-04 — secret-like pattern scan of added lines (parent plan
Sections 9.4 rule R5, 10.8, 12.4; FR-MCP-07).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.10-git-helper/
MT-2.10-04-secret-scan.md. Redaction is a security gate, not polish: no
test may ever find matched secret material in scanner output. The bundles
are real merge-base diffs from temp fixture repositories.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.git_helper import (
    GitHelperError,
    MergeBaseDiff,
    merge_base_diff,
    scan_patch,
)
from orchestrator_bridge.git_helper.secret_scan import load_patterns
from tests.git_fixtures import commit_all, git, make_repo, write_files

SECRET_FIXTURES: dict[str, str] = {
    "private-key": (
        "config:\n"
        "  signing_key: |\n"
        "    -----BEGIN RSA PRIVATE KEY-----\n"  # pragma: allowlist secret
        "    MIIEpAIBAAKCAQEAyMock\n"
        "    -----END RSA PRIVATE KEY-----\n"
    ),
    "aws-key": 'AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"\n',  # pragma: allowlist secret
    "assignment": 'api_key = "s3cr3t-value-9x"\n',  # pragma: allowlist secret
    "bearer": "headers = {'Authorization': 'Bearer 1234567890abcdef1234567890abcdef'}\n",
    "github": 'token = "ghp_abcdefghijklmnopqrstuvwx1234567890AB"\n',  # pragma: allowlist secret
}


def _diff_with(tmp_path: Path, name: str, content: str) -> MergeBaseDiff:
    repo = make_repo(tmp_path / "repo")
    git(repo, "switch", "-qc", "feat")
    write_files(repo, {f"config/{name}.yaml": content})
    commit_all(repo, f"add {name}")
    return merge_base_diff(repo, "feat", "main")


# --- true positives, one per documented pattern family ------------------------


@pytest.mark.parametrize(("family", "content"), sorted(SECRET_FIXTURES.items()))
def test_secret_scan_true_positive_per_family(tmp_path: Path, family: str, content: str) -> None:
    expected_pattern = {
        "private-key": "private-key-block",
        "aws-key": "aws-access-key-id",
        "assignment": "secret-assignment",
        "bearer": "bearer-token-literal",
        "github": "github-token",
    }[family]
    diff = _diff_with(tmp_path, family, content)
    result = scan_patch(diff)
    assert expected_pattern in {f.pattern_id for f in result.findings}
    assert result.by_file, "findings must group per file"


def test_secret_scan_reports_pattern_path_line_and_summary(tmp_path: Path) -> None:
    diff = _diff_with(tmp_path, "assignment", SECRET_FIXTURES["assignment"])
    result = scan_patch(diff)
    finding = result.findings[0]
    assert finding.path == "config/assignment.yaml"
    assert finding.line >= 1
    assert finding.severity in {"high", "medium"}
    assert finding.pattern_id
    payload = result.as_dict()
    assert payload["count"] == result.count
    assert payload["findings"][0]["pattern_id"] == finding.pattern_id


# --- redaction is a gate ------------------------------------------------------


@pytest.mark.parametrize(("family", "content"), sorted(SECRET_FIXTURES.items()))
def test_secret_scan_never_echoes_matched_material(
    tmp_path: Path, family: str, content: str
) -> None:
    """The matched secret material must not appear anywhere in the
    findings' text (Section 12.4)."""
    diff = _diff_with(tmp_path, family, content)
    result = scan_patch(diff)
    assert result.count >= 1
    serialized = str(result.as_dict())
    for secret in (
        "MIIEpAIBAAKCAQEAyMock",  # pragma: allowlist secret
        "AKIAIOSFODNN7EXAMPLE",  # pragma: allowlist secret
        "s3cr3t-value-9x",  # pragma: allowlist secret
        "1234567890abcdef1234567890abcdef",  # pragma: allowlist secret
        "ghp_abcdefghijklmnopqrstuvwx1234567890AB",  # pragma: allowlist secret
    ):
        if secret in content:
            assert secret not in serialized


def test_secret_scan_excerpt_shows_redaction_marker(tmp_path: Path) -> None:
    diff = _diff_with(tmp_path, "assignment", SECRET_FIXTURES["assignment"])
    finding = scan_patch(diff).findings[0]
    assert "[REDACTED:" in finding.excerpt


# --- added-lines-only scoping -------------------------------------------------


def test_secret_scan_ignores_removed_and_context_lines(tmp_path: Path) -> None:
    """A secret that *leaves* the codebase (a '-' line) is not a new leak."""
    repo = make_repo(tmp_path / "repo", {"app.conf": 'password = "old-secret-abcdef"\nkeep = 1\n'})
    git(repo, "switch", "-qc", "feat")
    write_files(repo, {"app.conf": "keep = 1\npassword_moved_out = 1\n"})
    commit_all(repo, "remove the secret")
    diff = merge_base_diff(repo, "feat", "main")
    assert "-password = " in diff.patch  # the removed line is in the patch
    result = scan_patch(diff)
    assert all("old-secret-abcdef" not in f.excerpt for f in result.findings)
    assert result.count == 0


def test_secret_scan_empty_diff_has_no_findings(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    git(repo, "switch", "-qc", "feat")
    diff = merge_base_diff(repo, "feat", "main")
    result = scan_patch(diff)
    assert result.count == 0
    assert result.lines_scanned == 0


def test_secret_scan_binary_files_yield_no_lines(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    git(repo, "switch", "-qc", "feat")
    (repo / "data.bin").write_bytes(b"\x00AKIAIOSFODNN7EXAMPLE\xff" * 8)  # pragma: allowlist secret
    commit_all(repo, "binary blob")
    diff = merge_base_diff(repo, "feat", "main")
    result = scan_patch(diff)
    assert result.count == 0, "binary content is outside the added-lines contract"


# --- false-positive sanity ----------------------------------------------------


@pytest.mark.parametrize(
    "innocent",
    [
        "The password policy requires twelve characters.\n",  # prose
        "password_length = 10\n",  # identifier + number, no literal
        "print('token refresh scheduled')\n",  # word in a string, too short
        "authorization: Bearer <token from vault>\n",  # placeholder, not a literal
    ],
)
def test_secret_scan_ordinary_code_is_clean(tmp_path: Path, innocent: str) -> None:
    diff = _diff_with(tmp_path, "innocent", innocent)
    result = scan_patch(diff)
    assert result.count == 0, f"false positive on {innocent!r}: {result.as_dict()}"


# --- configuration ------------------------------------------------------------


def test_secret_scan_default_patterns_are_the_documented_set() -> None:
    patterns = load_patterns()
    ids = {pattern.id for pattern in patterns}
    assert ids == {
        "private-key-block",
        "aws-access-key-id",
        "secret-assignment",
        "bearer-token-literal",
        "github-token",
    }
    for pattern in patterns:
        assert pattern.description and pattern.regex


def test_secret_scan_custom_pattern_file_is_honoured(tmp_path: Path) -> None:
    """Adding a pattern is a data edit — no code change (Section 9.10)."""
    pattern_file = tmp_path / "patterns.toml"
    pattern_file.write_text(
        "\n".join(
            [
                "[[patterns]]",
                'id = "acme-license"',
                'severity = "medium"',
                'description = "Acme license literal"',
                'regex = "ACME-[0-9A-Z]{4}-[0-9A-Z]{4}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    diff = _diff_with(tmp_path, "acme", 'license = "ACME-AB12-CD34"\n')
    result = scan_patch(diff, patterns=load_patterns(pattern_file))
    assert result.count == 1
    assert result.findings[0].pattern_id == "acme-license"
    assert "ACME-AB12-CD34" not in result.findings[0].excerpt


def test_secret_scan_ignore_rules_apply_narrowly(tmp_path: Path) -> None:
    diff = _diff_with(tmp_path, "assignment", SECRET_FIXTURES["assignment"])
    full = scan_patch(diff)
    ignored = scan_patch(diff, ignore_pattern_ids={full.findings[0].pattern_id})
    assert full.count >= 1
    assert ignored.count < full.count


def test_secret_scan_broken_pattern_file_fails_loudly(tmp_path: Path) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text("[[patterns]]\nid = 'x'\n", encoding="utf-8")
    with pytest.raises(GitHelperError) as excinfo:
        load_patterns(bad)
    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR


def test_secret_scan_invalid_regex_in_pattern_file_fails_loudly(tmp_path: Path) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text(
        "[[patterns]]\nid='x'\nseverity='high'\ndescription='d'\nregex='('\n", encoding="utf-8"
    )
    with pytest.raises(GitHelperError):
        load_patterns(bad)
