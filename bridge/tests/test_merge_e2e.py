"""MT-3.7-07 — the merge end-to-end suite (success + conflict + restart).

Acceptance source: plan-doc-series/m3-audit-policy-merge/wp-3.7-merge-executor/
MT-3.7-07-merge-e2e-test.md (parent plan Sections 18, 19 WP-3.7 acceptance,
8.1–8.2 T15/T17/T18, 11.4–11.5, 20.4, 20.5; ADR-008). The real backend
(wp16-pg), a real scratch Git repository and the real executor components
(loop + worktree + strategies + queue client over live HTTP):

* **Success path** — a merge-pending task (the state T15's approval leaves,
  seeded directly: WP-3.6's approval surface is its own suite's contract)
  is claimed, squash-merged in the temp worktree, landed on the default
  branch and completed with ``merge_status = merged`` (T17) — with the
  ``merge.succeeded`` event observed in the live database;
* **Conflict path** — overlapping seeded branches abort cleanly: T18 puts
  the task back to ``in_human_review`` with ``review_reason =
  merge_conflict`` (verbatim Section 8.4), ``merge.failed`` is observed,
  and the developer's working tree stays byte-identical (Section 19);
* **Restart recovery** — a claim whose result never left the process (the
  journal's open entry, MT-3.7-06) is reconciled by ``reconcile_on_startup``
  to exactly one terminal outcome, twice-run as a no-op;
* **Invariant 2** — no e2e task ever reaches ``completed`` without
  ``merge_status = merged`` (Section 8.3, ADR-008).

Gated exactly like the other live suites (``ORCHESTRATOR_BRIDGE_LIVE_TESTS=1``
plus Postgres): CI sets the flag with the wp16 stack up (Section 18), local
runs skip without it. Each scenario builds its own scratch repository and
seeds its own task/token (RISK-15 / Section 18 isolation — a conflict test
never mutates a shared fixture).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from orchestrator_bridge.config import RunMode, Settings
from orchestrator_bridge.merge_executor.journal import MergeJournal
from orchestrator_bridge.merge_executor.loop import MergeExecutorLoop
from orchestrator_bridge.merge_executor.queue import MergeQueueClient
from orchestrator_bridge.merge_executor.recovery import reconcile_on_startup
from orchestrator_bridge.merge_executor.step import resolve_merge_step
from orchestrator_bridge.transport import ApiClient
from tests import _live_backend
from tests.conftest import build_settings
from tests.git_fixtures import commit_all, git, make_repo, write_files

pytestmark = pytest.mark.skipif(
    _live_backend.skip_reason() is not None,
    reason=_live_backend.skip_reason() or "unreachable",
)

_PID = "PID00007"
_SHA = "0123456789abcdef0123456789abcdef01234567"  # pragma: allowlist secret


#: The shared seed's ``store_patch_artifact`` call is not re-run idempotent
#: (the known ``artifact_one_per_resolution_kind`` duplicate-key crash the
#: conformance suite documents); deleting the patch rows first lets the seed
#: recreate exactly what its own flow stores.
_PRECLEAN = """
from apps.tasks.models import TaskArtifact, ArtifactKind
TaskArtifact.objects.filter(kind=ArtifactKind.PATCH).delete()
print("MERGE_E2E_PRECLEAN done")
"""


@pytest.fixture(scope="module")
def live() -> Iterator[_live_backend.LiveBackend]:
    """One migrated, seeded live backend for the whole e2e module."""
    preclean = _live_backend._run_backend(  # noqa: SLF001 - shared live harness seam
        ["python", "manage.py", "shell", "-c", _PRECLEAN], timeout=120
    )
    if preclean.returncode != 0:
        pytest.skip(f"live database not resettable for merge e2e: {preclean.stderr[-400:]}")
    backend = _live_backend.start_live_backend()
    try:
        yield backend
    finally:
        _live_backend.stop_live_backend(backend)


def _run_seed(script: str) -> str:
    completed = _live_backend._run_backend(  # noqa: SLF001 - shared live harness seam
        ["python", "manage.py", "shell", "-c", script], timeout=120
    )
    if completed.returncode != 0:
        pytest.fail(
            f"merge e2e seed failed: stdout={completed.stdout!r} stderr={completed.stderr[-800:]!r}"
        )
    return completed.stdout


def _seed_merge_task(task_id: str, branch: str, repo_path: Path, token: str) -> None:
    """Point the project at this scenario's repo; seed the post-T15 queue state.

    The task lands exactly where WP-3.6's approval leaves it (carrier
    state + ``merge_status = pending`` + the attempt's resolution
    branch), so this suite tests the *merge* journey, not review again.
    """
    _run_seed(
        f"""
import hashlib
from apps.accounts.models import ApiToken, TokenKind, User
from apps.projects.models import Project
from apps.tasks.models import Task, TaskResolution, TaskState

project = Project.objects.get(pk={_PID!r})
project.repo_path = {str(repo_path)!r}
project.save(update_fields=["repo_path"])
owner = User.objects.get(username="bridge-it-owner")

Task.objects.get_or_create(
    id={task_id!r},
    project=project,
    defaults={{"title": "merge e2e task", "state": TaskState.IN_HUMAN_REVIEW}},
)
Task.objects.filter(id={task_id!r}).update(
    state=TaskState.IN_HUMAN_REVIEW,
    merge_status="pending",
    review_reason=None,
    attempt_number=1,
    archived_at=None,
    worker_agent_id=None,
    worker_session_id=None,
    claimed_role=None,
    lease_acquired_at=None,
)
TaskResolution.objects.get_or_create(
    task_id={task_id!r},
    attempt_number=1,
    defaults={{
        "branch_name": {branch!r},
        "commit_sha": {_SHA!r},
        "execution_summary": "merge e2e seeded submission",
        "submitted_by_session": "sess-merge-e2e",
    }},
)
plaintext = {token!r}
digest = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
ApiToken.objects.get_or_create(
    hash=digest,
    defaults={{
        "kind": TokenKind.AGENT,
        "user": owner,
        "project_id": {_PID!r},
        "scopes": ["merge_executor"],
    }},
)
print("MERGE_E2E_SEED ok")
"""
    )


def _task_events(task_id: str) -> list[str]:
    """Every event type recorded for *task_id*, straight from the live DB."""
    stdout = _run_seed(
        f"""
from apps.events.models import Event
for event in Event.objects.filter(task_id={task_id!r}).order_by("id"):
    print("E2E_EVENT", event.type)
"""
    )
    return [line.split()[1] for line in stdout.splitlines() if line.startswith("E2E_EVENT")]


def _settings(live: _live_backend.LiveBackend, repo: Path, token: str) -> Settings:
    """Executor settings bound to this scenario's live origin, repo and token."""
    return build_settings(
        api_base_url=live.api_base_url,
        agent_token=token,
        mode=RunMode.MERGE_EXECUTOR,
        merge_repo_paths=(str(repo),),
        timeout_seconds=15.0,
        retry_max_attempts=3,
        retry_base_delay_seconds=0.2,
    )


def _run_executor_once(settings: Settings) -> None:
    """One real queue pass through the wired loop (worktree + strategies)."""
    api = ApiClient(settings)
    loop = MergeExecutorLoop(settings, MergeQueueClient(api), resolve_merge_step(settings))
    assert loop.run_once() >= 1


def _snapshot(repo: Path) -> dict[str, bytes]:
    state: dict[str, bytes] = {}
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or ".git" in path.relative_to(repo).parts:
            continue
        state[str(path.relative_to(repo))] = path.read_bytes()
    return state


def _queue(settings: Settings) -> MergeQueueClient:
    return MergeQueueClient(ApiClient(settings))


# --- success path --------------------------------------------------------------


def test_merge_e2e_success_completes_the_task_with_a_landed_merge(
    live: _live_backend.LiveBackend, tmp_path: Path
) -> None:
    """Approve-equivalent pending → claim → squash merge → T17 completed+merged."""
    task_id = "PID00007-T010"
    branch = "feat/merge-e2e-ok"
    token = "bridge-it-merge-e2e-success"  # pragma: allowlist secret - dev-only DB
    repo = make_repo(tmp_path / "merge-e2e-repo", {"README.md": "# base\n", "app.py": "V = 1\n"})
    git(repo, "checkout", "-qb", branch)
    write_files(repo, {"feature.py": "NEW = True\n"})
    commit_all(repo, f"{branch}: add feature")
    git(repo, "checkout", "-q", "main")
    main_before = git(repo, "rev-parse", "main").stdout.strip()
    before = _snapshot(repo)

    _seed_merge_task(task_id, branch, repo, token)
    _run_executor_once(_settings(live, repo, token))

    # The backend's T17: completed with merge_status merged — and the
    # merged result really landed as the default branch's new tip
    # (the working tree itself stays the developer's — Section 11.4
    # step 5: files on disk are only resynced by the developer, never
    # written by the executor).
    task = _queue(_settings(live, repo, token)).task(task_id)
    assert task["state"] == "completed"
    assert task["merge_status"] == "merged"
    assert git(repo, "rev-parse", "main").stdout.strip() != main_before
    assert git(repo, "show", "main:feature.py").stdout.strip() == "NEW = True"
    assert _snapshot(repo) == before  # untouched dev tree, byte-identical
    # The event the T17 row writes (Section 9.6) — observed in the DB.
    assert "merge.succeeded" in _task_events(task_id)
    # Invariant 2 (Section 8.3, ADR-008): completed implies merged.
    assert task["merge_status"] == "merged"


# --- conflict path -------------------------------------------------------------


def test_merge_e2e_conflict_escalates_and_leaves_the_dev_tree_untouched(
    live: _live_backend.LiveBackend, tmp_path: Path
) -> None:
    """Overlapping branches: T18 to review with merge_conflict; tree untouched."""
    task_id = "PID00007-T011"
    branch = "feat/merge-e2e-conflict"
    token = "bridge-it-merge-e2e-conflict"  # pragma: allowlist secret - dev-only DB
    repo = make_repo(tmp_path / "merge-e2e-repo", {"README.md": "# base\n", "app.py": "V = 1\n"})
    git(repo, "checkout", "-qb", branch)
    write_files(repo, {"README.md": "# the branch's README\n"})
    commit_all(repo, f"{branch}: rewrite README")
    git(repo, "checkout", "-q", "main")
    write_files(repo, {"README.md": "# main's competing README\n"})
    commit_all(repo, "main: competing README")
    main_before = git(repo, "rev-parse", "main").stdout.strip()
    before = _snapshot(repo)
    status_before = git(repo, "status", "--porcelain").stdout

    _seed_merge_task(task_id, branch, repo, token)
    _run_executor_once(_settings(live, repo, token))

    settings = _settings(live, repo, token)
    task = _queue(settings).task(task_id)
    # T18 verbatim: back to review, Section 8.4's canonical reason, conflict.
    assert task["state"] == "in_human_review"
    assert task["review_reason"] == "merge_conflict"
    assert task["merge_status"] == "conflict"
    assert "merge.failed" in _task_events(task_id)
    # Section 19: the developer's working tree is byte-identical; nothing landed.
    assert _snapshot(repo) == before
    assert git(repo, "status", "--porcelain").stdout == status_before
    assert git(repo, "rev-parse", "main").stdout.strip() == main_before


# --- restart recovery (MT-3.7-06 contract, live) ------------------------------


def test_merge_e2e_restart_converges_on_exactly_one_outcome(
    live: _live_backend.LiveBackend, tmp_path: Path
) -> None:
    """A claim whose report never left the process reconciles once, then no-ops."""
    task_id = "PID00007-T012"
    branch = "feat/merge-e2e-recover"
    token = "bridge-it-merge-e2e-recover"  # pragma: allowlist secret - dev-only DB
    repo = make_repo(tmp_path / "merge-e2e-repo", {"README.md": "# base\n", "app.py": "V = 1\n"})
    git(repo, "checkout", "-qb", branch)
    write_files(repo, {"recover.py": "R = 1\n"})
    commit_all(repo, f"{branch}: recoverable work")
    git(repo, "checkout", "-q", "main")
    before = _snapshot(repo)

    _seed_merge_task(task_id, branch, repo, token)
    settings = _settings(live, repo, token)
    queue = _queue(settings)

    # The crashed run: claim accepted (→ merging), journal opened, process dies.
    pending = queue.pending()
    item = next(entry for entry in pending.items if entry.id == task_id)
    queue.start(item)
    journal = MergeJournal(tmp_path / "merge-e2e-journal.jsonl")
    journal.record_started(task_id, version=int(queue.task(task_id)["version"]))

    # The restarted executor reconciles: exactly one terminal outcome (T18
    # with the recovery's honest ``failed`` flavor — nothing is claimed to
    # be a conflict we never observed).
    assert reconcile_on_startup(settings, queue, journal=journal) == 1
    task = queue.task(task_id)
    assert task["state"] == "in_human_review"
    assert task["review_reason"] == "merge_conflict"
    assert task["merge_status"] == "failed"
    events = _task_events(task_id)
    assert "merge.failed" in events
    assert "merge.succeeded" not in events  # never a fabricated completion

    # Second restart: no journal entries left — a pure no-op.
    assert reconcile_on_startup(settings, queue, journal=journal) == 0
    assert queue.task(task_id)["version"] == task["version"]
    assert _snapshot(repo) == before


# --- invariant sweep -----------------------------------------------------------


def test_merge_e2e_invariant_no_completed_without_merged(live: _live_backend.LiveBackend) -> None:
    """Section 8.3 invariant 2 across every e2e task this module created."""
    stdout = _run_seed(
        """
import json
from apps.tasks.models import Task
breaches = list(
    Task.objects.filter(
        id__in=["PID00007-T010", "PID00007-T011", "PID00007-T012"],
        state="completed",
    )
    .exclude(merge_status="merged")
    .values_list("id", flat=True)
)
print("E2E_BREACH", json.dumps(list(breaches)))
"""
    )
    marker = next(line for line in stdout.splitlines() if line.startswith("E2E_BREACH"))
    assert json.loads(marker.split(" ", 1)[1]) == []
