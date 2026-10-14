"""MT-3.7-02 — the Section 11.4 Merge Executor loop over a mocked backend.

Acceptance source: plan-doc-series/m3-audit-policy-merge/wp-3.7-merge-executor/
MT-3.7-02-executor-loop.md (parent plan Sections 10.2, 10.10, 11.4, 9.2;
FR-AUD-06; ADR-007, ADR-012). The loop owns only the queue contract — poll
``GET /merge/pending`` → claim ``POST /merge/{task}/start`` → injected merge
step (MT-3.7-03's worktree + MT-3.7-04's strategies plug in there) → report
``POST /merge/{task}/result``. Everything Git lives behind the
:class:`~orchestrator_bridge.merge_executor.loop.MergeStep` seam, so every
test here drives a fake step against ``tests.conftest.FakeBackend`` and a
scratch repository (Section 10.2's allowlist uses real paths).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from orchestrator_bridge.config import ConfigError
from orchestrator_bridge.entrypoints import EXIT_OK
from orchestrator_bridge.entrypoints import executor as executor_module
from orchestrator_bridge.idempotency import IDEMPOTENCY_HEADER
from orchestrator_bridge.merge_executor import (
    DEFAULT_POLL_SECONDS,
    MUTATION_BACKOFF_ATTEMPTS,
    RESULT_CONFLICT,
    RESULT_FAILED,
    RESULT_SUCCEEDED,
    MergeExecutorLoop,
    MergeOutcome,
    MergeQueueClient,
    MergeReportError,
    MergeStep,
    QueueItem,
    WorktreeStrategyStep,
    resolve_merge_step,
)
from orchestrator_bridge.transport import ApiClient
from tests.conftest import FakeBackend, build_settings, envelope_wire
from tests.git_fixtures import make_repo

_SHA = "0123456789abcdef0123456789abcdef01234567"  # pragma: allowlist secret
_TASK = "PID00007-T006"
_PENDING_PATH = "/api/v1/merge/pending"
_PROJECT_PATH = "/api/v1/projects/PID00007"
_START_PATH = f"/api/v1/merge/{_TASK}/start"
_RESULT_PATH = f"/api/v1/merge/{_TASK}/result"

_PENDING_ROW: dict[str, Any] = {
    "id": _TASK,
    "project_id": "PID00007",
    "title": "Merge invoice export",
    "state": "in_human_review",
    "version": 6,
    "merge_status": "pending",
    "branch_name": "feat/PID00007-T006",
}

_START_TASK: dict[str, Any] = {
    "id": _TASK,
    "state": "in_human_review",
    "version": 7,
    "review_reason": None,
    "merge_status": "merging",
}

_MERGED_TASK: dict[str, Any] = {
    "id": _TASK,
    "state": "completed",
    "version": 8,
    "review_reason": None,
    "merge_status": "merged",
}


class _StopLoop(Exception):
    """Sentinel: breaks ``run_forever`` at its next injected sleep."""


def _error(status: int, code: str, *, retryable: bool = False) -> dict[str, Any]:
    """One Section 9.2 error envelope as a route payload."""
    payload: dict[str, Any] = json.loads(
        envelope_wire(status, code, f"backend said {code}", retryable=retryable).body
    )
    return payload


def _pending_payload(*rows: dict[str, Any]) -> dict[str, Any]:
    return {"results": list(rows), "next_cursor": None}


def _happy_backend(repo_path: str) -> FakeBackend:
    """The Section 11.4 happy path: pending row, project, claim, merge, result."""
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload(_PENDING_ROW))
    fake.route("GET", _PROJECT_PATH, 200, {"id": "PID00007", "repo_path": repo_path})
    fake.route(
        "POST",
        _START_PATH,
        200,
        {"task": dict(_START_TASK)},
    )
    fake.route(
        "POST",
        _RESULT_PATH,
        200,
        {"task": dict(_MERGED_TASK), "result": RESULT_SUCCEEDED, "sha": _SHA},
    )
    return fake


def _loop(
    fake: FakeBackend,
    step: MergeStep,
    *,
    repo_paths: tuple[str, ...],
    base_delay: float = 0.0,
) -> tuple[MergeExecutorLoop, list[float]]:
    """A wired loop over the fake; returns it plus the injected sleep record."""
    settings = build_settings(merge_repo_paths=repo_paths, retry_base_delay_seconds=base_delay)
    api = ApiClient(settings, send=fake.send, sleep=lambda _: None)
    sleeps: list[float] = []
    loop = MergeExecutorLoop(settings, MergeQueueClient(api), step, sleep=sleeps.append)
    return loop, sleeps


def _successful_step(calls: list[tuple[QueueItem, str]]) -> MergeStep:
    def step(item: QueueItem, repo_path: Any, project: Any) -> MergeOutcome:
        calls.append((item, str(repo_path)))
        return MergeOutcome(result=RESULT_SUCCEEDED, sha=_SHA)

    return step


# --- MergeOutcome catalog discipline (Section 7.2, 20.4 item 5) ----------------


def test_outcome_rejects_values_outside_the_catalog() -> None:
    with pytest.raises(ValueError, match=r"\['conflict', 'failed', 'succeeded'\]"):
        MergeOutcome(result="aborted")


def test_outcome_requires_a_sha_on_success_t17_guard() -> None:
    with pytest.raises(ValueError, match="sha"):
        MergeOutcome(result=RESULT_SUCCEEDED)


def test_documented_poll_default_is_thirty_seconds() -> None:
    """The unspecified poll interval's default lives in the loop contract."""
    assert DEFAULT_POLL_SECONDS == 30.0


# --- empty queue ---------------------------------------------------------------


def test_empty_queue_is_idle(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload())
    step_calls: list[tuple[QueueItem, str]] = []
    loop, _ = _loop(fake, _successful_step(step_calls), repo_paths=(str(repo),))

    assert loop.run_once() == 0
    assert [call.path for call in fake.calls] == [_PENDING_PATH]
    assert step_calls == []


# --- one successful cycle (pending → merging → result) -------------------------


def test_one_successful_cycle_reports_the_sha(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    fake = _happy_backend(str(repo))
    step_calls: list[tuple[QueueItem, str]] = []
    loop, _ = _loop(fake, _successful_step(step_calls), repo_paths=(str(repo),))

    assert loop.run_once() == 1

    # Section 11.4 order: poll, project context, claim, merge step, result.
    assert [call.path for call in fake.calls] == [
        _PENDING_PATH,
        _PROJECT_PATH,
        _START_PATH,
        _RESULT_PATH,
    ]
    # The claim CASes the listing version (FR-TSK-06); the result chains the
    # claim's incremented version and carries the resulting sha (T17).
    assert fake.calls_to("POST", _START_PATH)[0].body == {"version": 6}
    result = fake.calls_to("POST", _RESULT_PATH)[0]
    assert result.body == {
        "result": RESULT_SUCCEEDED,
        "sha": _SHA,
        "details": "",
        "version": 7,
    }
    # ADR-012: every mutation carries exactly one key.
    for call in fake.calls:
        if call.method == "POST":
            assert IDEMPOTENCY_HEADER in call.headers
    # The step received the allowlist-verified repo, never the dev tree.
    assert [(item.id, path) for item, path in step_calls] == [(_TASK, str(repo.resolve()))]


# --- failure report (conflict → T18 path) --------------------------------------


def test_conflict_outcome_is_reported_with_details(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload(_PENDING_ROW))
    fake.route("GET", _PROJECT_PATH, 200, {"id": "PID00007", "repo_path": str(repo)})
    fake.route("POST", _START_PATH, 200, {"task": dict(_START_TASK)})
    fake.route(
        "POST",
        _RESULT_PATH,
        200,
        {"task": dict(_MERGED_TASK), "result": RESULT_CONFLICT, "sha": None},
    )

    def conflict_step(item: QueueItem, repo_path: Any, project: Any) -> MergeOutcome:
        return MergeOutcome(result=RESULT_CONFLICT, details="src/billing/invoice.py")

    loop, _ = _loop(fake, conflict_step, repo_paths=(str(repo),))

    assert loop.run_once() == 1
    # sha is omitted when absent (the schema default) — only a success
    # carries one, so a conflict report never advertises a phantom sha.
    assert fake.calls_to("POST", _RESULT_PATH)[0].body == {
        "result": RESULT_CONFLICT,
        "details": "src/billing/invoice.py",
        "version": 7,
    }


def test_step_exception_is_contained_as_a_failed_report(tmp_path: Path) -> None:
    """An unexpected step crash never kills the loop — it reports T18 ``failed``."""
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload(_PENDING_ROW))
    fake.route("GET", _PROJECT_PATH, 200, {"id": "PID00007", "repo_path": str(repo)})
    fake.route("POST", _START_PATH, 200, {"task": dict(_START_TASK)})
    fake.route(
        "POST",
        _RESULT_PATH,
        200,
        {"task": dict(_MERGED_TASK), "result": RESULT_FAILED, "sha": None},
    )

    def exploding_step(item: QueueItem, repo_path: Any, project: Any) -> MergeOutcome:
        raise RuntimeError("worktree vanished")

    loop, _ = _loop(fake, exploding_step, repo_paths=(str(repo),))

    assert loop.run_once() == 1
    body = fake.calls_to("POST", _RESULT_PATH)[0].body
    assert body is not None and body["result"] == RESULT_FAILED
    assert body is not None and "RuntimeError: worktree vanished" in str(body["details"])


def test_success_without_a_sha_is_downgraded_to_failed(tmp_path: Path) -> None:
    """A step bug must never reach T17's Guard un-sha'd (defensive downgrade)."""
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload(_PENDING_ROW))
    fake.route("GET", _PROJECT_PATH, 200, {"id": "PID00007", "repo_path": str(repo)})
    fake.route("POST", _START_PATH, 200, {"task": dict(_START_TASK)})
    fake.route(
        "POST",
        _RESULT_PATH,
        200,
        {"task": dict(_MERGED_TASK), "result": RESULT_FAILED, "sha": None},
    )

    def unsha_step(item: QueueItem, repo_path: Any, project: Any) -> MergeOutcome:
        return cast(MergeOutcome, SimpleNamespace(result=RESULT_SUCCEEDED, sha=None, details=""))

    loop, _ = _loop(fake, unsha_step, repo_paths=(str(repo),))

    assert loop.run_once() == 1
    body = fake.calls_to("POST", _RESULT_PATH)[0].body
    assert body is not None and body["result"] == RESULT_FAILED


# --- backend outage: backoff + retry, never a duplicate completion (10.10) -----


def test_report_outage_backs_off_and_replays_the_same_key(tmp_path: Path) -> None:
    """One logical report → one idempotency key across every retry (ADR-012)."""
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload(_PENDING_ROW))
    fake.route("GET", _PROJECT_PATH, 200, {"id": "PID00007", "repo_path": str(repo)})
    fake.route("POST", _START_PATH, 200, {"task": dict(_START_TASK)})
    attempts: list[int] = []

    def result_route(body: Any) -> tuple[int, Any]:
        attempts.append(1)
        if len(attempts) == 1:
            return 503, _error(503, "SERVER_ERROR", retryable=True)
        return 200, {"task": dict(_MERGED_TASK), "result": RESULT_SUCCEEDED, "sha": _SHA}

    fake.route_fn("POST", _RESULT_PATH, result_route)
    step_calls: list[tuple[QueueItem, str]] = []
    loop, sleeps = _loop(
        fake, _successful_step(step_calls), repo_paths=(str(repo),), base_delay=2.0
    )

    assert loop.run_once() == 1
    assert len(attempts) == 2
    # Section 10.10: one exponential backoff at the configured base delay…
    assert sleeps == [2.0]
    # …and the replayed report is byte-identical, key included — the
    # backend can dedupe it instead of applying a second transition.
    reports = fake.calls_to("POST", _RESULT_PATH)
    assert reports[0].body == reports[1].body
    assert reports[0].headers[IDEMPOTENCY_HEADER] == reports[1].headers[IDEMPOTENCY_HEADER]


def test_claim_outage_replays_the_same_start_key(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload(_PENDING_ROW))
    fake.route("GET", _PROJECT_PATH, 200, {"id": "PID00007", "repo_path": str(repo)})
    claims: list[int] = []

    def start_route(body: Any) -> tuple[int, Any]:
        claims.append(1)
        if len(claims) == 1:
            return 503, _error(503, "SERVER_ERROR", retryable=True)
        return 200, {"task": dict(_START_TASK)}

    fake.route_fn("POST", _START_PATH, start_route)
    fake.route(
        "POST",
        _RESULT_PATH,
        200,
        {"task": dict(_MERGED_TASK), "result": RESULT_SUCCEEDED, "sha": _SHA},
    )
    step_calls: list[tuple[QueueItem, str]] = []
    loop, _ = _loop(fake, _successful_step(step_calls), repo_paths=(str(repo),))

    assert loop.run_once() == 1
    starts = fake.calls_to("POST", _START_PATH)
    assert len(starts) == 2
    assert starts[0].headers[IDEMPOTENCY_HEADER] == starts[1].headers[IDEMPOTENCY_HEADER]


def test_unconfirmed_report_stops_the_loop_for_crash_recovery(tmp_path: Path) -> None:
    """Retryable-but-forever-down report → MergeReportError, key logged, loop stops
    (never guesses a second completion — MT-3.7-06 reconciles)."""
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload(_PENDING_ROW))
    fake.route("GET", _PROJECT_PATH, 200, {"id": "PID00007", "repo_path": str(repo)})
    fake.route("POST", _START_PATH, 200, {"task": dict(_START_TASK)})
    fake.route("POST", _RESULT_PATH, 503, _error(503, "SERVER_ERROR", retryable=True))
    step_calls: list[tuple[QueueItem, str]] = []
    loop, sleeps = _loop(
        fake, _successful_step(step_calls), repo_paths=(str(repo),), base_delay=1.0
    )

    with pytest.raises(MergeReportError, match="remains merging"):
        loop.run_once()

    reports = fake.calls_to("POST", _RESULT_PATH)
    assert len(reports) == MUTATION_BACKOFF_ATTEMPTS
    keys = {call.headers[IDEMPOTENCY_HEADER] for call in reports}
    assert len(keys) == 1  # every attempt replays the original key
    assert sleeps == [1.0, 2.0]  # capped exponential backoff between attempts


# --- catalog refusals: skip, never double-claim (Section 9.2, 20.4 item 5) -----


def test_claim_conflict_is_skipped_without_a_result(tmp_path: Path) -> None:
    """TASK_STATE_CONFLICT = another executor won the race; do nothing."""
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload(_PENDING_ROW))
    fake.route("GET", _PROJECT_PATH, 200, {"id": "PID00007", "repo_path": str(repo)})
    fake.route("POST", _START_PATH, 409, _error(409, "TASK_STATE_CONFLICT"))
    step_calls: list[tuple[QueueItem, str]] = []
    loop, _ = _loop(fake, _successful_step(step_calls), repo_paths=(str(repo),))

    assert loop.run_once() == 0
    assert fake.calls_to("POST", _RESULT_PATH) == []
    assert step_calls == []


def test_report_version_conflict_is_absorbed(tmp_path: Path) -> None:
    """A stale CAS on the report answered VERSION_CONFLICT applies nothing —
    and must not crash the loop (the catalog answered; nothing to redo)."""
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload(_PENDING_ROW))
    fake.route("GET", _PROJECT_PATH, 200, {"id": "PID00007", "repo_path": str(repo)})
    fake.route("POST", _START_PATH, 200, {"task": dict(_START_TASK)})
    fake.route("POST", _RESULT_PATH, 409, _error(409, "VERSION_CONFLICT"))
    step_calls: list[tuple[QueueItem, str]] = []
    loop, _ = _loop(fake, _successful_step(step_calls), repo_paths=(str(repo),))

    assert loop.run_once() == 1  # the attempt completed; only the report was refused
    assert len(fake.calls_to("POST", _RESULT_PATH)) == 1


def test_unreadable_project_skips_the_entry_before_claiming(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload(_PENDING_ROW))
    fake.route("GET", _PROJECT_PATH, 404, _error(404, "TASK_NOT_FOUND"))
    step_calls: list[tuple[QueueItem, str]] = []
    loop, _ = _loop(fake, _successful_step(step_calls), repo_paths=(str(repo),))

    assert loop.run_once() == 0
    assert fake.calls_to("POST", _START_PATH) == []


# --- Section 10.2: repos outside the allowlist are never opened ----------------


def test_repo_outside_the_allowlist_is_never_claimed_or_opened(tmp_path: Path) -> None:
    allowed = make_repo(tmp_path / "allowed")
    outside = tmp_path / "outside"  # not in merge_repo_paths — never touched
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload(_PENDING_ROW))
    fake.route("GET", _PROJECT_PATH, 200, {"id": "PID00007", "repo_path": str(outside)})
    step_calls: list[tuple[QueueItem, str]] = []
    loop, _ = _loop(fake, _successful_step(step_calls), repo_paths=(str(allowed),))

    assert loop.run_once() == 0
    # Pre-claim refusal: nothing was started, nothing was merged, and the
    # outside path was never handed to a step.
    assert fake.calls_to("POST", _START_PATH) == []
    assert fake.calls_to("POST", _RESULT_PATH) == []
    assert step_calls == []
    assert not outside.exists()


def test_project_without_a_repo_path_is_skipped(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload(_PENDING_ROW))
    fake.route("GET", _PROJECT_PATH, 200, {"id": "PID00007"})
    step_calls: list[tuple[QueueItem, str]] = []
    loop, _ = _loop(fake, _successful_step(step_calls), repo_paths=(str(repo),))

    assert loop.run_once() == 0
    assert fake.calls_to("POST", _START_PATH) == []


# --- long-running form (Section 10.2) ------------------------------------------


def test_run_forever_idles_at_the_configured_poll_interval(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    fake.route("GET", _PENDING_PATH, 200, _pending_payload())
    step_calls: list[tuple[QueueItem, str]] = []
    sleeps: list[float] = []

    def stop_after_first_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        raise _StopLoop

    settings = build_settings(merge_repo_paths=(str(repo),))
    api = ApiClient(settings, send=fake.send, sleep=lambda _: None)
    loop = MergeExecutorLoop(
        settings, MergeQueueClient(api), _successful_step(step_calls), sleep=stop_after_first_sleep
    )
    with pytest.raises(_StopLoop):
        loop.run_forever(poll_seconds=7.0)
    assert sleeps == [7.0]


def test_run_forever_backs_off_through_a_poll_outage(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    fake = FakeBackend()
    polls: list[int] = []

    def pending_route(body: Any) -> tuple[int, Any]:
        polls.append(1)
        if len(polls) == 1:
            return 503, _error(503, "SERVER_ERROR", retryable=True)
        return 200, _pending_payload()

    fake.route_fn("GET", _PENDING_PATH, pending_route)
    step_calls: list[tuple[QueueItem, str]] = []
    sleeps: list[float] = []

    def stop_after_two_sleeps(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) >= 2:
            raise _StopLoop

    settings = build_settings(merge_repo_paths=(str(repo),), retry_base_delay_seconds=3.0)
    api = ApiClient(settings, send=fake.send, sleep=lambda _: None)
    loop = MergeExecutorLoop(
        settings,
        MergeQueueClient(api),
        _successful_step(step_calls),
        sleep=stop_after_two_sleeps,
    )
    with pytest.raises(_StopLoop):
        loop.run_forever(poll_seconds=9.0)
    # Outage backoff at the base delay, then the idle poll interval —
    # one worker, retrying, never doubling its own claims.
    assert sleeps == [3.0, 9.0]
    assert len(polls) == 2


# --- the step resolver boundary (wired since MT-3.7-03/04) ----------------------


def test_resolve_merge_step_returns_the_composed_step(tmp_path: Path) -> None:
    """The resolver hands back the worktree+strategy step — never a refusal."""
    settings = build_settings(merge_repo_paths=(str(tmp_path),))
    step = resolve_merge_step(settings)
    assert isinstance(step, WorktreeStrategyStep)


# --- the entry point's on-demand launch form (Section 10.2) --------------------


def test_executor_run_once_serves_the_queue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = make_repo(tmp_path / "repo")
    fake = _happy_backend(str(repo))
    step_calls: list[tuple[QueueItem, str]] = []
    step = _successful_step(step_calls)
    settings = build_settings(merge_repo_paths=(str(repo),))

    monkeypatch.setattr(executor_module, "resolve_merge_step", lambda _settings: step)
    monkeypatch.setattr(
        executor_module,
        "ApiClient",
        lambda config: ApiClient(config, send=fake.send, sleep=lambda _: None),
    )

    assert executor_module.run(settings, once=True) == EXIT_OK
    assert [call.path for call in fake.calls] == [
        _PENDING_PATH,
        _PROJECT_PATH,
        _START_PATH,
        _RESULT_PATH,
    ]


def test_executor_run_refuses_without_an_allowlist() -> None:
    with pytest.raises(ConfigError, match="merge_repo_paths"):
        executor_module.run(build_settings())
