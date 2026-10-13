"""Fixture repositories for the Git-helper tests (MT-2.10-01..06).

Temp repositories only — never this repository's Git state (the HARD rule of
the WP-2.10 test protocol): every helper here takes a directory (pytest's
``tmp_path``) and builds a self-contained repository there with local
``user.*``/``gpgsign``/``autocrlf`` config, so a developer's or CI runner's
global Git configuration cannot leak into fixture behavior.

The raw :func:`git` used for *setup* is deliberately unguarded — the
MT-2.10-01 capability guard constrains the **helper's** invocations, not the
test harness that must create unusual repository states (mid-merge, orphan
branches, stale worktrees) to exercise it.
"""

from __future__ import annotations

import subprocess  # noqa: S404 - test fixture setup: list args, shell=False
from pathlib import Path

__all__ = ["commit_all", "git", "make_repo", "write_files"]


def git(
    repo: Path, *args: str | list[str] | tuple[str, ...], check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run one raw Git command in *repo* (fixture setup; no helper guard).

    Accepts either varargs (``git(repo, "status")``) or a single sequence
    (``git(repo, ["rev-parse", "HEAD"])``) — both spellings appear in tests.
    """
    flattened: list[str] = []
    for arg in args:
        if isinstance(arg, str):
            flattened.append(arg)
        else:
            flattened.extend(arg)
    completed = subprocess.run(  # noqa: S603 - list args, shell=False
        ["git", *flattened],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"fixture git {' '.join(flattened)} failed ({completed.returncode}): "
            f"{completed.stderr.strip()}"
        )
    return completed


def write_files(repo: Path, files: dict[str, str]) -> None:
    """Write relative-path → content into the repository tree."""
    for relative, content in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")


def commit_all(repo: Path, message: str) -> None:
    """Stage everything and commit with deterministic local identity."""
    git(repo, "add", "-A")
    git(repo, "commit", "--cleanup=verbatim", "-m", message)


def make_repo(path: Path, files: dict[str, str] | None = None, *, branch: str = "main") -> Path:
    """A fresh repository at *path* with one initial commit on *branch*.

    Isolated from global config: local ``user.*``, no signing, no autocrlf
    (byte-stable fixtures on every OS — MT-2.10-06), ``init.defaultBranch``
    forced via ``init -b``.
    """
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", branch)
    git(path, "config", "user.email", "fixtures@orchestrator.invalid")
    git(path, "config", "user.name", "Bridge Fixture")
    git(path, "config", "commit.gpgsign", "false")
    git(path, "config", "core.autocrlf", "false")
    write_files(path, files if files is not None else {"README.md": "# fixture\n"})
    commit_all(path, "initial")
    return path
