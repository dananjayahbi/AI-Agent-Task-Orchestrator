"""MT-3.7-06 — crash recovery on executor restart.

Acceptance source: plan-doc-series/m3-audit-policy-merge/wp-3.7-merge-executor/
MT-3.7-06-crash-recovery.md (parent plan Sections 19 WP-3.7 acceptance, 10.2,
10.10, 9.9, 7.2, 8.2 T17/T18, 20.4; ADR-008, ADR-012, P6). Simulated crashes
in scratch repositories: kill-after-start and kill-mid-merge both converge on
**exactly one** T18 outcome after restart, leftover worktrees are removed
before new work, the dev tree stays byte-identical through crash and
recovery, a second restart performs no duplicate work, backend-down recovery
backs off (and stops without fabricating results), the journal is written by
the live loop, and the single-worker lock refuses a second executor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from orchestrator_bridge.config import Settings
from orchestrator_bridge.entrypoints import EXIT_OK
from orchestrator_bridge.idempotency import IDEMPOTENCY_HEADER
from orchestrator_bridge.merge_executor import worktree as worktree_module
from orchestrator_bridge.merge_executor.journal import MergeJournal, journal_path
from orchestrator_bridge.merge_executor.loop import (
    MUTATION_BACKOFF_ATTEMPTS,
    MergeExecutorLoop,
    MergeOutcome,
    MergeReportError,
)
from orchestrator_bridge.merge_executor.queue import MergeQueueClient, QueueItem
from orchestrator_bridge.merge_executor.recovery import (
    MergeRecoveryError,
    acquire_executor_lock,
    reconcile_on_startup,
)
from orchestrator_bridge.transport import ApiClient
from tests.conftest import FakeBackend, build_settings, envelope_wire
from tests.git_fixtures import git, make_repo, write_files

_TASK = "PID00007-T006"
_TASK_PATH = f"/api/v1/tasks/{_TASK}"
_RESULT_PATH = f"/api/v1/merge/{_TASK}/result"
_SHA = "0123456789abcdef0123456789abcdef01234567"  # pragma: allowlist secret


@pytest.fixture()
def wt_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the executor's temp root (worktrees, journal, lock) under tmp_path."""
    root = tmp_path / "exec-temp"
    monkeypatch.setattr(worktree_module, "temp_worktree_root", lambda: root)
    return root


def _error(status: int, code: str, *, retryable: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(
        envelope_wire(status, code, f"backend said {code}", retryable=retryable).body
    )
    return payload


def _task_payload(merge_status: str = "merging", *, version: int = 7) -> dict[str, Any]:
    return {
        "id": _TASK,
        "project_id": "PID00007",
        "title": "Merge invoice export",
        "state": "in_human_review",
        "version": version,
        "review_reason": None,
        "merge_status": merge_status,
        "branch_name": "feat/PID00007-T006",
    }


def _recovery_backend(task_payload: dict[str, Any]) -> FakeBackend:
    fake = FakeBackend()
    fake.route("GET", _TASK_PATH, 200, task_payload)
    fake.route(
        "POST",
        _RESULT_PATH,
        200,
        {
            "task": {
                "id": _TASK,
                "state": "in_human_review",
                "version": 8,
                "review_reason": "merge_conflict",
                "merge_status": "conflict",
            }
        },
    )
    return fake


def _queue_over(
    fake: FakeBackend, *, base_delay: float = 0.0, repo_paths: tuple[str, ...] = ()
) -> tuple[Settings, MergeQueueClient]:
    settings = build_settings(
        merge_repo_paths=repo_paths or ("nonexistent-for-cleanup",),
        retry_base_delay_seconds=base_delay,
    )
    api = ApiClient(settings, send=fake.send, sleep=lambda _: None)
    return settings, MergeQueueClient(api)


def _snapshot(repo: Path) -> dict[str, bytes]:
    state: dict[str, bytes] = {}
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or ".git" in path.relative_to(repo).parts:
            continue
        state[str(path.relative_to(repo))] = path.read_bytes()
    return state


def _dirty_repo(tmp_path: Path) -> Path:
    repo = make_repo(tmp_path / "repo", {"README.md": "# fixture\n", "app.py": "V = 1\n"})
    (repo / "app.py").write_text("V = 2  # uncommitted work\n", encoding="utf-8")
    git(repo, "add", "app.py")
    write_files(repo, {"notes.local.md": "personal scratch notes\n"})
    return repo


def _journal() -> MergeJournal:
    return MergeJournal(journal_path())


# --- kill-after-start: exactly one T18, then a no-op restart ------------------


def test_crash_recovery_after_start_reports_one_t18_then_no_op_restart(
    wt_root: Path, tmp_path: Path
) -> None:
    _journal().record_started(_TASK, version=7)  # the claim happened; crash before report

    fake = _recovery_backend(_task_payload())
    settings, queue = _queue_over(fake)
    assert reconcile_on_startup(settings, queue) == 1

    reports = fake.calls_to("POST", _RESULT_PATH)
    assert len(reports) == 1
    assert reports[0].body["result"] == "failed"
    assert "restart" in reports[0].body["details"]
    assert IDEMPOTENCY_HEADER in reports[0].headers
    # Journal compacted: the open entry closed with its outcome.
    assert _journal().unresolved() == {}

    # Second restart: no journal entries → zero calls, zero duplicate work.
    assert reconcile_on_startup(settings, queue) == 0
    assert len(fake.calls_to("POST", _RESULT_PATH)) == 1


# --- kill-mid-merge: leftovers cleaned, dev tree untouched ---------------------


def test_crash_recovery_mid_merge_cleans_leftover_and_keeps_dev_tree_intact(
    wt_root: Path, tmp_path: Path
) -> None:
    repo = _dirty_repo(tmp_path)
    before = _snapshot(repo)
    status_before = git(repo, "status", "--porcelain").stdout
    main_before = git(repo, "rev-parse", "main").stdout.strip()

    # The crashed run: a worktree left mid-merge (conflicted, staged) …
    crashed = worktree_module._create(repo, "main")  # noqa: SLF001 - crash fixture
    git(crashed.path, "checkout", "-qb", "feat/crashed")
    write_files(crashed.path, {"README.md": "half-applied merge\n"})
    git(crashed.path, "add", "-A")
    git(crashed.path, "commit", "-m", "mid-merge state that never reported")
    # … and a journal entry still owed an outcome.
    _journal().record_started(_TASK, version=7)

    fake = _recovery_backend(_task_payload())
    settings, queue = _queue_over(fake, repo_paths=(str(repo),))
    assert reconcile_on_startup(settings, queue) == 1

    # Leftover gone before any new merge can start; exactly one T18 report.
    assert worktree_module.list_leftover_worktrees(repo) == ()
    assert len(fake.calls_to("POST", _RESULT_PATH)) == 1
    # The developer's tree: every byte and even `git status` unchanged.
    assert _snapshot(repo) == before
    assert git(repo, "status", "--porcelain").stdout == status_before
    assert git(repo, "rev-parse", "main").stdout.strip() == main_before
    assert _journal().unresolved() == {}


# --- already decided elsewhere: apply nothing (ADR-012) -----------------------


def test_crash_recovery_closes_entry_when_task_already_left_merging(
    wt_root: Path, tmp_path: Path
) -> None:
    _journal().record_started(_TASK, version=7)
    fake = _recovery_backend(_task_payload(merge_status="completed", version=9))
    settings, queue = _queue_over(fake)

    assert reconcile_on_startup(settings, queue) == 1
    assert fake.calls_to("POST", _RESULT_PATH) == []  # never a second apply
    assert _journal().unresolved() == {}


# --- backend down: backoff, then stop without fabricating ---------------------


def test_crash_recovery_backs_off_while_backend_unreachable_then_resumes(
    wt_root: Path, tmp_path: Path
) -> None:
    _journal().record_started(_TASK, version=7)
    fake = FakeBackend()
    attempts = {"count": 0}

    def _details_then_works(_body: Any) -> tuple[int, Any]:
        attempts["count"] += 1
        if attempts["count"] <= 2:
            return 503, _error(503, "SERVICE_UNAVAILABLE", retryable=True)
        return 200, _task_payload()

    fake.route_fn("GET", _TASK_PATH, _details_then_works)
    fake.route("POST", _RESULT_PATH, 200, {"task": {"id": _TASK}})

    settings, queue = _queue_over(fake, base_delay=3.0)
    sleeps: list[float] = []
    assert reconcile_on_startup(settings, queue, sleep=sleeps.append) == 1
    # Section 10.10 exponential backoff: 3s then 6s, then the API returned.
    assert sleeps == [3.0, 6.0]
    assert len(fake.calls_to("POST", _RESULT_PATH)) == 1


def test_crash_recovery_stops_without_fabricating_results_on_persistent_outage(
    wt_root: Path, tmp_path: Path
) -> None:
    _journal().record_started(_TASK, version=7)
    fake = FakeBackend()
    fake.route_fn(
        "GET",
        _TASK_PATH,
        lambda _body: (503, _error(503, "SERVICE_UNAVAILABLE", retryable=True)),
    )
    settings, queue = _queue_over(fake, base_delay=1.0)
    sleeps: list[float] = []

    with pytest.raises(MergeRecoveryError, match="unconfirmed"):
        reconcile_on_startup(settings, queue, sleep=sleeps.append)

    assert len(sleeps) == MUTATION_BACKOFF_ATTEMPTS - 1
    assert fake.calls_to("POST", _RESULT_PATH) == []  # nothing fabricated
    # The journal entry stays open for the next start.
    assert list(_journal().unresolved()) == [_TASK]


# --- the live loop writes the journal's evidence ------------------------------


def test_crash_recovery_journal_records_claim_and_report_from_the_loop(
    wt_root: Path, tmp_path: Path
) -> None:
    """A healthy run leaves no open entry — claim and report both journaled."""
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    journal = MergeJournal(wt_root / "journal.jsonl")
    settings = build_settings(merge_repo_paths=(str(repo),), retry_base_delay_seconds=0.0)
    api = ApiClient(settings, send=fake.send, sleep=lambda _: None)
    step_calls: list[QueueItem] = []

    def step(item: QueueItem, repo_path: Path, project: Any) -> MergeOutcome:
        step_calls.append(item)
        return MergeOutcome(result="succeeded", sha=_SHA)

    # Minimal happy routes for one queue pass (pending → claim → report).
    fake.route(
        "GET",
        "/api/v1/merge/pending",
        200,
        {
            "results": [
                {
                    "id": _TASK,
                    "project_id": "PID00007",
                    "title": "t",
                    "state": "in_human_review",
                    "version": 6,
                    "merge_status": "pending",
                    "branch_name": "feat/PID00007-T006",
                }
            ],
            "next_cursor": None,
        },
    )
    fake.route("GET", "/api/v1/projects/PID00007", 200, {"repo_path": str(repo)})
    fake.route(
        "POST",
        f"/api/v1/merge/{_TASK}/start",
        200,
        {
            "task": {
                "id": _TASK,
                "state": "in_human_review",
                "version": 7,
                "review_reason": None,
                "merge_status": "merging",
            }
        },
    )
    fake.route(
        "POST",
        _RESULT_PATH,
        200,
        {
            "task": {
                "id": _TASK,
                "state": "completed",
                "version": 8,
                "review_reason": None,
                "merge_status": "merged",
            }
        },
    )

    loop = MergeExecutorLoop(settings, MergeQueueClient(api), step, journal=journal)
    loop.run_once()

    phases = [
        json.loads(line)["phase"]
        for line in journal.path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert phases == ["started", "reported"]
    assert journal.unresolved() == {}


def test_crash_recovery_lost_report_leaves_entry_open_for_the_next_start(
    wt_root: Path, tmp_path: Path
) -> None:
    """Report unconfirmed (MergeReportError) → journal still open → recovery closes it."""
    repo = make_repo(tmp_path / "repo")
    journal = MergeJournal(wt_root / "journal.jsonl")
    fake = FakeBackend()
    settings = build_settings(merge_repo_paths=(str(repo),), retry_base_delay_seconds=0.0)
    api = ApiClient(settings, send=fake.send, sleep=lambda _: None)
    fake.route(
        "GET",
        "/api/v1/merge/pending",
        200,
        {
            "results": [
                {
                    "id": _TASK,
                    "project_id": "PID00007",
                    "title": "t",
                    "state": "in_human_review",
                    "version": 6,
                    "merge_status": "pending",
                    "branch_name": "feat/PID00007-T006",
                }
            ],
            "next_cursor": None,
        },
    )
    fake.route("GET", "/api/v1/projects/PID00007", 200, {"repo_path": str(repo)})
    fake.route(
        "POST",
        f"/api/v1/merge/{_TASK}/start",
        200,
        {
            "task": {
                "id": _TASK,
                "state": "in_human_review",
                "version": 7,
                "review_reason": None,
                "merge_status": "merging",
            }
        },
    )
    fake.route_fn(
        "POST",
        _RESULT_PATH,
        lambda _body: (503, _error(503, "SERVICE_UNAVAILABLE", retryable=True)),
    )

    loop = MergeExecutorLoop(
        settings,
        MergeQueueClient(api),
        lambda item, repo_path, project: MergeOutcome(result="succeeded", sha=_SHA),
        journal=journal,
    )
    with pytest.raises(MergeReportError):
        loop.run_once()

    assert list(journal.unresolved()) == [_TASK]  # the crash-shaped evidence

    # The restarted executor closes it with exactly one T18 report.
    recovery_fake = _recovery_backend(_task_payload())
    recovery_settings, recovery_queue = _queue_over(recovery_fake)
    assert reconcile_on_startup(recovery_settings, recovery_queue, journal=journal) == 1
    assert len(recovery_fake.calls_to("POST", _RESULT_PATH)) == 1
    assert journal.unresolved() == {}


# --- single-worker lock (RISK-03; the MT risk note's startup locking) ---------


def test_crash_recovery_lock_refuses_a_second_executor(wt_root: Path) -> None:
    first = acquire_executor_lock()
    try:
        with pytest.raises(MergeRecoveryError, match="another Merge Executor"):
            acquire_executor_lock()
    finally:
        first.close()
    # Released → the next start takes it (a crash never wedges the lock).
    second = acquire_executor_lock()
    second.close()


# --- the run's happy path (loop + strategy untouched by recovery) -------------


def test_crash_recovery_run_once_still_serves_the_queue_after_wiring(
    monkeypatch: pytest.MonkeyPatch, wt_root: Path, tmp_path: Path
) -> None:
    """The wired startup path (lock + recovery + journal) coexists with a pass."""
    import orchestrator_bridge.entrypoints.executor as executor_module

    repo = make_repo(tmp_path / "repo")
    fake = _recovery_backend(_task_payload(merge_status="pending", version=1))
    settings = build_settings(merge_repo_paths=(str(repo),))
    api = ApiClient(settings, send=fake.send, sleep=lambda _: None)
    monkeypatch.setattr(executor_module, "ApiClient", lambda _settings: api)
    monkeypatch.setattr(
        executor_module,
        "MergeExecutorLoop",
        lambda *_args, **_kwargs: type(
            "Loop",
            (),
            {"run_once": lambda self: 0, "run_forever": lambda self: None},
        )(),
    )
    assert executor_module.run(settings, once=True) == EXIT_OK
    # The lock file exists (acquired) and the journal survived the run.
    assert (wt_root / "merge-executor.lock").exists()
