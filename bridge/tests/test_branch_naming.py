"""MT-2.10-02 — branch naming derivation (G-09) and create-or-switch
(parent plan gap G-09, Sections 10.5, 10.6 rule 1, 10.8).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.10-git-helper/
MT-2.10-02-branch-naming.md. The G-09 example is asserted byte-for-byte
(Section 20.5 traceability); temp fixture repositories only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.git_helper import (
    GitHelperError,
    clean_state,
    create_or_switch_branch,
    derive_branch_name,
)
from tests.git_fixtures import git, make_repo, write_files

# --- derivation matrix (pure, no Git) -----------------------------------------


def test_branch_naming_g09_example_exactly() -> None:
    """The plan's example, byte-for-byte (Section 20.5 traceability)."""
    assert derive_branch_name("PID00007-T004", auto_branch_prefix="feat/PID00007-") == (
        "feat/PID00007-T004"
    )


def test_branch_naming_default_prefix_uses_task_pid() -> None:
    """Absent manifest key → documented default ``feat/{PID}-`` (G-09)."""
    assert derive_branch_name("PID00012-T001") == "feat/PID00012-T001"


def test_branch_naming_manifest_prefix_wins_over_default() -> None:
    derived = derive_branch_name("PID00007-T004", auto_branch_prefix="chore/tea-")
    assert derived == "chore/tea-T004"


def test_branch_naming_empty_prefix_falls_back_to_default() -> None:
    assert derive_branch_name("PID00007-T004", auto_branch_prefix="") == "feat/PID00007-T004"


@pytest.mark.parametrize(
    "task_id",
    [
        "PID00007",  # no task segment
        "PID0007-T004",  # short project id
        "PRJ00007-T004",  # wrong prefix
        "PID00007-X004",  # non-T index
        "PID00007-T",  # index without digits
        "pid00007-t004",  # wrong case
        "PID00007-T004/extra",  # separator smuggled in
        "",
    ],
)
def test_branch_naming_rejects_unparseable_task_ids(task_id: str) -> None:
    with pytest.raises(GitHelperError) as excinfo:
        derive_branch_name(task_id)
    error = excinfo.value
    assert error.code is ErrorCode.VALIDATION_ERROR
    assert error.hint and error.next_action


@pytest.mark.parametrize(
    "prefix",
    [
        "-leading-dash-",
        "has space-",
        "double..dot-",
        "tilde~",
        "caret^",
        "colon:",
        "question?",
        "star*",
        "bracket[",
        "back\\slash-",
        "trail//",  # empty segment once the index is appended
        ".hidden-",  # leading dot — invalid ref component
        "seg/.hidden-",
    ],
)
def test_branch_naming_rejects_prefixes_that_form_invalid_refs(prefix: str) -> None:
    """Never silently sanitize — a bad prefix is a structured error."""
    with pytest.raises(GitHelperError) as excinfo:
        derive_branch_name("PID00007-T004", auto_branch_prefix=prefix)
    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR


# --- create-or-switch (fixture repositories) ----------------------------------


def test_branch_naming_create_new_branch_from_default(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    switched = create_or_switch_branch(repo, "feat/PID00007-T004", default_branch="main")
    assert switched.created is True
    assert switched.branch == "feat/PID00007-T004"
    current = git(repo, "branch", "--show-current")
    assert current.stdout.strip() == "feat/PID00007-T004"
    assert switched.head_sha == git(repo, ["rev-parse", "HEAD"]).stdout.strip()


def test_branch_naming_switch_existing_branch(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    git(repo, "branch", "feat/PID00007-T004", "main")
    switched = create_or_switch_branch(repo, "feat/PID00007-T004", default_branch="main")
    assert switched.created is False
    assert git(repo, "branch", "--show-current").stdout.strip() == "feat/PID00007-T004"


def test_branch_naming_dirty_tree_refused_with_hint(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    write_files(repo, {"README.md": "# agent arrived early\n"})
    with pytest.raises(GitHelperError) as excinfo:
        create_or_switch_branch(repo, "feat/PID00007-T004", default_branch="main")
    error = excinfo.value
    assert error.code is ErrorCode.VALIDATION_ERROR
    assert "not clean" in error.message
    assert "MT-2.10-02" in error.hint or "rule 1" in error.hint
    # nothing was created or switched
    assert (
        git(
            repo,
            ["rev-parse", "--verify", "--quiet", "refs/heads/feat/PID00007-T004"],
            check=False,
        ).returncode
        != 0
    )


def test_branch_naming_untracked_file_also_blocks_the_switch(tmp_path: Path) -> None:
    """Untracked files are pre-existing content too — a later ``git add -A``
    on the task branch would sweep them into agent work, so the precondition
    refuses them as strictly as tracked changes."""
    repo = make_repo(tmp_path / "repo")
    write_files(repo, {"notes.untracked": "x\n"})
    assert clean_state(repo).untracked_files == 1
    with pytest.raises(GitHelperError) as excinfo:
        create_or_switch_branch(repo, "feat/PID00007-T004", default_branch="main")
    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert "untracked" in excinfo.value.message


def test_branch_naming_missing_default_branch_is_structured(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    with pytest.raises(GitHelperError) as excinfo:
        create_or_switch_branch(repo, "feat/PID00007-T004", default_branch="trunk")
    error = excinfo.value
    assert error.code is ErrorCode.VALIDATION_ERROR
    assert "trunk" in error.message
    assert "fetch" in error.next_action.lower()


def test_branch_naming_invalid_branch_name_refused_before_git(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    with pytest.raises(GitHelperError) as excinfo:
        create_or_switch_branch(repo, "-bad-name", default_branch="main")
    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    # nothing was created
    listed = git(repo, ["branch", "--list", "--format=%(refname:short)"])
    assert listed.stdout.strip() == "main"


def test_branch_naming_no_push_or_delete_during_creation(tmp_path: Path) -> None:
    """The creation path's only verbs are reads and branch creation — the
    sentinel: after create-or-switch, the default branch is intact and no
    ref was removed."""
    repo = make_repo(tmp_path / "repo")
    create_or_switch_branch(repo, "feat/PID00007-T004", default_branch="main")
    branches = git(repo, ["branch", "--list"]).stdout
    assert "main" in branches and "feat/PID00007-T004" in branches
