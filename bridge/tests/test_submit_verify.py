"""MT-2.6-02 — branch and commit-sha verification before submission.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.6-checkpoint-submit-tools/
MT-2.6-02-branch-sha-verification.md (parent plan Sections 10.5, 10.8, 11.1;
FR-MCP-07; ADR-007). Every rejection is a structured ``VALIDATION_ERROR``
(the catalog choice recorded in the WP changelog) carrying a hint and a next
action; repository identity is verified against the manifest binding before
any git work; clean state is consumed from WP-2.10, never re-implemented.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.manifest import StartupBinding
from orchestrator_bridge.submission_spool import SubmissionSpool
from orchestrator_bridge.tools.errors import ToolFailure
from orchestrator_bridge.tools.submit_verify import VerifiedSubmission, verify_submission
from tests.conftest import MINIMAL_MANIFEST, FakeBackend, build_runtime
from tests.git_fixtures import commit_all, git, make_repo, write_files

_TASK_ID = "PID00007-T004"
_ASSIGNED_BRANCH = "feat/PID00007-T004"


def _manifest_files() -> dict[str, str]:
    return {"README.md": "# fixture\n", "orchestrator.json": json.dumps(MINIMAL_MANIFEST)}


def _binding(repo: Path) -> StartupBinding:
    manifest = dict(MINIMAL_MANIFEST)
    return StartupBinding(manifest_path=repo / "orchestrator.json", manifest=manifest)


@pytest.fixture
def task_repo(tmp_path: Path) -> Path:
    """A repository with the manifest committed and the assigned branch tip."""
    repo = make_repo(tmp_path / "repo", _manifest_files())
    git(repo, "checkout", "-q", "-b", _ASSIGNED_BRANCH)
    write_files(repo, {"feature.py": "print('feature')\n"})
    commit_all(repo, "implement the feature")
    return repo


def test_submit_verify_accepts_the_assigned_branch_tip(task_repo: Path) -> None:
    tip = git(task_repo, "rev-parse", "HEAD").stdout.strip()

    verified = verify_submission(
        _binding(task_repo),
        task_id=_TASK_ID,
        git_branch=_ASSIGNED_BRANCH,
        commit_sha=tip,
    )

    assert isinstance(verified, VerifiedSubmission)
    assert verified.branch == _ASSIGNED_BRANCH
    assert verified.commit_sha == tip  # full resolved id, never the spelling
    assert verified.root == task_repo.resolve()
    assert verified.working_tree["clean"] is True


def test_submit_verify_accepts_an_abbreviated_sha(task_repo: Path) -> None:
    short = git(task_repo, "rev-parse", "--short", "HEAD").stdout.strip()
    full = git(task_repo, "rev-parse", "HEAD").stdout.strip()

    verified = verify_submission(
        _binding(task_repo), task_id=_TASK_ID, git_branch=_ASSIGNED_BRANCH, commit_sha=short
    )

    assert verified.commit_sha == full  # normalized for capture and upload


def test_submit_verify_rejects_a_nonexistent_commit_sha(task_repo: Path) -> None:
    with pytest.raises(ToolFailure) as excinfo:
        verify_submission(
            _binding(task_repo),
            task_id=_TASK_ID,
            git_branch=_ASSIGNED_BRANCH,
            commit_sha="deadbeef" * 5,  # 40 hex chars of nothing
        )

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert translated.hint and translated.next_action  # Section 10.5 error rule
    assert "commit" in translated.next_action  # what to fix, concretely


def test_submit_verify_rejects_an_unusable_sha_spelling(task_repo: Path) -> None:
    with pytest.raises(ToolFailure) as excinfo:
        verify_submission(
            _binding(task_repo),
            task_id=_TASK_ID,
            git_branch=_ASSIGNED_BRANCH,
            commit_sha="not-a-sha --upload-pack=evil",
        )

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert translated.retryable is False


def test_submit_verify_rejects_a_sha_from_another_branch(task_repo: Path) -> None:
    # A real commit on `main`, never merged into the assigned branch.
    git(task_repo, "checkout", "-q", "main")
    write_files(task_repo, {"other.py": "x = 1\n"})
    commit_all(task_repo, "main-side work")
    main_sha = git(task_repo, "rev-parse", "HEAD").stdout.strip()
    git(task_repo, "checkout", "-q", _ASSIGNED_BRANCH)

    with pytest.raises(ToolFailure) as excinfo:
        verify_submission(
            _binding(task_repo),
            task_id=_TASK_ID,
            git_branch=_ASSIGNED_BRANCH,
            commit_sha=main_sha,
        )

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert "not reachable" in translated.message
    assert translated.hint and translated.next_action


def test_submit_verify_rejects_a_branch_that_is_not_the_assigned_one(task_repo: Path) -> None:
    main_tip = git(task_repo, "rev-parse", "main").stdout.strip()

    with pytest.raises(ToolFailure) as excinfo:
        verify_submission(
            _binding(task_repo), task_id=_TASK_ID, git_branch="main", commit_sha=main_tip
        )

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert _ASSIGNED_BRANCH in translated.hint  # the rejection names the assigned branch
    assert translated.details is not None
    assert translated.details["assigned_branch"] == _ASSIGNED_BRANCH


def test_submit_verify_rejects_the_assigned_branch_when_absent(task_repo: Path) -> None:
    tip = git(task_repo, "rev-parse", "HEAD").stdout.strip()
    git(task_repo, "checkout", "-q", "main")
    git(task_repo, "branch", "-q", "-D", _ASSIGNED_BRANCH)

    with pytest.raises(ToolFailure) as excinfo:
        verify_submission(
            _binding(task_repo),
            task_id=_TASK_ID,
            git_branch=_ASSIGNED_BRANCH,
            commit_sha=tip,
        )

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert "does not exist" in translated.message


def test_submit_verify_rejects_a_manifest_outside_any_repository(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "orchestrator.json").write_text(json.dumps(MINIMAL_MANIFEST), encoding="utf-8")

    with pytest.raises(ToolFailure) as excinfo:
        verify_submission(
            _binding(plain), task_id=_TASK_ID, git_branch=_ASSIGNED_BRANCH, commit_sha="a" * 40
        )

    translated = excinfo.value.translated  # repo identity first, before any git work
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert "Git working tree" in translated.message
    assert translated.hint and translated.next_action


def test_submit_verify_rejects_an_in_progress_merge(task_repo: Path) -> None:
    # Build a real conflict: both branches change the same line.
    git(task_repo, "checkout", "-q", "main")
    write_files(task_repo, {"feature.py": "print('main version')\n"})
    commit_all(task_repo, "main moves the line")
    git(task_repo, "checkout", "-q", _ASSIGNED_BRANCH)
    write_files(task_repo, {"feature.py": "print('feature version')\n"})
    commit_all(task_repo, "feature moves the line")
    conflicted = git(task_repo, "merge", "main", check=False)
    assert conflicted.returncode != 0  # the fixture's intended state
    tip = git(task_repo, "rev-parse", "HEAD").stdout.strip()

    with pytest.raises(ToolFailure) as excinfo:
        verify_submission(
            _binding(task_repo), task_id=_TASK_ID, git_branch=_ASSIGNED_BRANCH, commit_sha=tip
        )

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert "in progress" in translated.message
    assert translated.details is not None
    assert translated.details["working_tree"]["merge_in_progress"] is True


def test_submit_verify_reports_a_dirty_tree_without_rejecting(task_repo: Path) -> None:
    # Recorded reading (WP-2.6 changelog): the patch is commit-keyed, so
    # uncommitted edits cannot leak into the evidence — they are *reported*
    # in the outcome, while "commit before submit" stays rule 4 for agents.
    tip = git(task_repo, "rev-parse", "HEAD").stdout.strip()
    write_files(task_repo, {"feature.py": "print('uncommitted edit')\n"})

    verified = verify_submission(
        _binding(task_repo), task_id=_TASK_ID, git_branch=_ASSIGNED_BRANCH, commit_sha=tip
    )

    assert verified.working_tree["clean"] is False
    assert verified.working_tree["uncommitted_changes"] == 1


def test_submit_verify_never_touches_the_backend(task_repo: Path) -> None:
    # ADR-007: verification is host-side only — zero wire calls, spool or not.
    tip = git(task_repo, "rev-parse", "HEAD").stdout.strip()
    fake = FakeBackend()
    runtime = build_runtime(
        fake, binding=_binding(task_repo), spool=SubmissionSpool(task_repo.parent / "spool")
    )

    verify_submission(
        runtime.binding, task_id=_TASK_ID, git_branch=_ASSIGNED_BRANCH, commit_sha=tip
    )

    assert fake.calls == []
