"""MT-2.6-04 — resolution upload: wire contract, outcomes, idempotency.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.6-checkpoint-submit-tools/
MT-2.6-04-resolution-upload.md (parent plan Sections 8.2 (T7/T8), 9.2, 10.5,
10.10, 11.1; FR-MCP-07; ADR-012). The response shapes are WP-3.2's frozen
``ResolutionWriteResponseSerializer``; the persist-before-network ordering
(MT-2.6-05) is proven here at the send seam; stale-lease and conflict
answers stop-and-orient (Section 11.1 step 7) with no blind retry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.config import Settings
from orchestrator_bridge.idempotency import IDEMPOTENCY_HEADER
from orchestrator_bridge.manifest import StartupBinding
from orchestrator_bridge.submission_spool import SubmissionSpool
from orchestrator_bridge.tools.errors import ToolFailure
from orchestrator_bridge.tools.runtime import ToolRuntime
from orchestrator_bridge.tools.submit import submit_task_resolution
from tests.conftest import (
    FIXTURE_TOKEN,
    MINIMAL_MANIFEST,
    FakeBackend,
    build_runtime,
    build_settings,
    envelope_wire,
)
from tests.git_fixtures import commit_all, git, make_repo, write_files

_TASK_ID = "PID00007-T004"
_ASSIGNED_BRANCH = "feat/PID00007-T004"
_RESOLUTON_PATH = f"/api/v1/tasks/{_TASK_ID}/resolution"

_WIRE_KEYS = {
    "session_id",
    "lease_generation",
    "git_branch",
    "commit_sha",
    "execution_summary",
    "requires_human_attention",
    "risk_justification",
    "patch",
    "changed_files",
    "diff_summary",
}


def _resolution_wire(
    *,
    state: str = "to_be_audited",
    review_reason: str | None = None,
    trigger: str = "submit",
    commit_sha: str = "c" * 40,
    requires_human_attention: bool = False,
) -> dict[str, Any]:
    """The WP-3.2 ``ResolutionWriteResponseSerializer`` shape, frozen."""
    return {
        "resolution": {
            "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "task_id": _TASK_ID,
            "attempt_number": 1,
            "branch_name": _ASSIGNED_BRANCH,
            "commit_sha": commit_sha,
            "execution_summary": "Ran the tests; all green.",
            "diff_summary": {"files": 1, "insertions": 1, "deletions": 0},
            "changed_files": ["feature.py"],
            "requires_human_attention": requires_human_attention,
            "risk_justification": "",
            "submitted_by_session": "fixture-session-0001",
            "submitted_at": "2026-10-13T10:30:00Z",
        },
        "task": {
            "id": _TASK_ID,
            "state": state,
            "version": 2,
            "review_reason": review_reason,
            "merge_status": "none",
        },
        "trigger": trigger,
        "scope_violations": [],
    }


@pytest.fixture
def task_repo(tmp_path: Path) -> Path:
    """A clean repository with the manifest committed and the assigned tip."""
    repo = make_repo(
        tmp_path / "repo",
        {"README.md": "# fixture\n", "orchestrator.json": json.dumps(MINIMAL_MANIFEST)},
    )
    git(repo, "checkout", "-q", "-b", _ASSIGNED_BRANCH)
    write_files(repo, {"feature.py": "print('feature')\n"})
    commit_all(repo, "implement the feature")
    return repo


def _manifest() -> dict[str, object]:
    return dict(MINIMAL_MANIFEST)


def _binding(repo: Path) -> StartupBinding:
    return StartupBinding(manifest_path=repo / "orchestrator.json", manifest=_manifest())


def _submit_env(
    task_repo: Path,
    fake: FakeBackend,
    *,
    settings: Settings | None = None,
    with_spool: bool = True,
) -> tuple[ToolRuntime, SubmissionSpool]:
    spool = SubmissionSpool(task_repo.parent / "spool")
    runtime = build_runtime(
        fake,
        binding=_binding(task_repo),
        settings=settings,
        spool=spool if with_spool else None,
    )
    return runtime, spool


def _head(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def test_submit_resolution_posts_the_wire_contract_and_clears_the_spool(
    task_repo: Path, fake_backend: FakeBackend
) -> None:
    tip = _head(task_repo)
    captured: dict[str, Any] = {}

    def _respond(body: Any) -> tuple[int, Any]:
        captured["body"] = body
        return 201, _resolution_wire(commit_sha=tip)

    fake_backend.route_fn("POST", _RESOLUTON_PATH, _respond)
    runtime, spool = _submit_env(task_repo, fake_backend)

    result = submit_task_resolution(
        runtime,
        task_id=_TASK_ID,
        git_branch=_ASSIGNED_BRANCH,
        commit_sha=tip,
        execution_summary="Ran the tests; all green.",
    )

    # The outcome the agent is told is the backend's actual state (T7).
    assert result["outcome"] == "to_be_audited"
    assert result["review_reason"] is None
    assert result["trigger"] == "submit"
    assert result["resolution_id"] == "7c9e6679-7425-40de-944b-e07fc1f90ae7"
    assert result["changed_files"] == ["feature.py"]  # the server's authoritative list
    assert result["diff_summary"] == {"files": 1, "insertions": 1, "deletions": 0}
    assert result["diff_too_large"] is False
    assert result["scope_violations"] == []
    assert "audit" in result["next_action"]

    # The ResolutionSubmitSerializer wire contract, field for field.
    (call,) = fake_backend.calls_to("POST", _RESOLUTON_PATH)
    assert set(captured["body"]) == _WIRE_KEYS
    assert call.body["git_branch"] == _ASSIGNED_BRANCH
    assert call.body["commit_sha"] == tip
    assert call.body["session_id"] == "fixture-session-0001"
    assert call.body["lease_generation"] == 0
    assert "feature.py" in call.body["patch"]  # the full merge-base patch rides along
    assert call.body["changed_files"] == ["feature.py"]  # provisional claim
    assert call.body["diff_summary"]["files_changed"] == 1
    assert call.headers[IDEMPOTENCY_HEADER]  # ADR-012: one key per submission

    # Acknowledged → the spool entry is cleared (only acknowledgments complete).
    assert spool.entries() == []


def test_submit_resolution_carries_the_claimed_lease_generation(
    task_repo: Path, fake_backend: FakeBackend
) -> None:
    tip = _head(task_repo)
    fake_backend.route("POST", _RESOLUTON_PATH, 201, _resolution_wire(commit_sha=tip))
    runtime, _spool = _submit_env(task_repo, fake_backend)
    runtime.record_lease(_TASK_ID, 4)

    submit_task_resolution(
        runtime,
        task_id=_TASK_ID,
        git_branch=_ASSIGNED_BRANCH,
        commit_sha=tip,
        execution_summary="done",
    )

    (call,) = fake_backend.calls_to("POST", _RESOLUTON_PATH)
    assert call.body["lease_generation"] == 4


def test_submit_resolution_surfaces_in_human_review_with_its_reason(
    task_repo: Path, fake_backend: FakeBackend
) -> None:
    tip = _head(task_repo)
    fake_backend.route(
        "POST",
        _RESOLUTON_PATH,
        201,
        _resolution_wire(
            state="in_human_review",
            review_reason="self_flagged",
            trigger="submit_flagged",
            commit_sha=tip,
            requires_human_attention=True,
        ),
    )
    runtime, _spool = _submit_env(task_repo, fake_backend)

    result = submit_task_resolution(
        runtime,
        task_id=_TASK_ID,
        git_branch=_ASSIGNED_BRANCH,
        commit_sha=tip,
        execution_summary="done, but uncertain about the migration",
        requires_human_attention=True,
        risk_justification="schema change needs a human look",
    )

    # The risk note: escalations are never hidden behind a success shape.
    assert result["outcome"] == "in_human_review"
    assert result["review_reason"] == "self_flagged"
    assert result["trigger"] == "submit_flagged"
    assert "Human review required" in result["next_action"]
    assert "self_flagged" in result["next_action"]


def test_submit_resolution_lease_expired_stops_and_orients(
    task_repo: Path, fake_backend: FakeBackend
) -> None:
    tip = _head(task_repo)
    fake_backend.route(
        "POST",
        _RESOLUTON_PATH,
        409,
        json.loads(envelope_wire(409, "LEASE_EXPIRED", "stale lease").body),
    )
    runtime, spool = _submit_env(
        task_repo, fake_backend, settings=build_settings(retry_max_attempts=2)
    )

    with pytest.raises(ToolFailure) as excinfo:
        submit_task_resolution(
            runtime,
            task_id=_TASK_ID,
            git_branch=_ASSIGNED_BRANCH,
            commit_sha=tip,
            execution_summary="done",
        )

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.LEASE_EXPIRED
    assert translated.retryable is False  # stop-and-orient, never a blind retry
    assert "claim_task" in translated.next_action
    assert len(fake_backend.calls) == 1  # exactly one attempt even with retries enabled
    assert spool.entries() == []  # definitive rejection → the entry is resolved


def test_submit_resolution_persists_before_the_network_call(
    task_repo: Path, fake_backend: FakeBackend
) -> None:
    # MT-2.6-05's ordering, proven at the send seam: by the time the backend
    # sees the request, the payload is already durable on this host.
    tip = _head(task_repo)
    spool_dir = task_repo.parent / "spool"
    observed: dict[str, Any] = {}

    def _respond(_body: Any) -> tuple[int, Any]:
        observed["files_on_disk"] = sorted(p.name for p in spool_dir.glob("*.json"))
        return 201, _resolution_wire(commit_sha=tip)

    fake_backend.route_fn("POST", _RESOLUTON_PATH, _respond)
    runtime, _spool = _submit_env(task_repo, fake_backend)

    submit_task_resolution(
        runtime,
        task_id=_TASK_ID,
        git_branch=_ASSIGNED_BRANCH,
        commit_sha=tip,
        execution_summary="done",
    )

    assert len(observed["files_on_disk"]) == 1  # persisted before the send


def test_submit_resolution_keeps_the_payload_and_notes_retention_on_outage(
    task_repo: Path, fake_backend: FakeBackend
) -> None:
    tip = _head(task_repo)
    fake_backend.route(
        "POST",
        _RESOLUTON_PATH,
        500,
        json.loads(
            envelope_wire(500, "SERVER_ERROR", "database is restarting", retryable=True).body
        ),
    )
    runtime, spool = _submit_env(task_repo, fake_backend)

    with pytest.raises(ToolFailure) as excinfo:
        submit_task_resolution(
            runtime,
            task_id=_TASK_ID,
            git_branch=_ASSIGNED_BRANCH,
            commit_sha=tip,
            execution_summary="done",
        )

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.SERVER_ERROR
    assert translated.retryable is True
    assert "retained" in translated.next_action  # nothing was lost
    (entry,) = spool.entries()
    assert entry.task_id == _TASK_ID
    assert entry.attempts == 1
    assert entry.last_error == "SERVER_ERROR"


def test_submit_resolution_retried_call_replays_one_key_and_lands_once(
    task_repo: Path, fake_backend: FakeBackend
) -> None:
    tip = _head(task_repo)
    attempts = {"count": 0}

    def _flaky(_body: Any) -> tuple[int, Any]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return 500, {"error": {"code": "SERVER_ERROR", "message": "blip", "retryable": True}}
        return 201, _resolution_wire(commit_sha=tip)

    fake_backend.route_fn("POST", _RESOLUTON_PATH, _flaky)
    runtime, spool = _submit_env(
        task_repo, fake_backend, settings=build_settings(retry_max_attempts=2)
    )

    result = submit_task_resolution(
        runtime,
        task_id=_TASK_ID,
        git_branch=_ASSIGNED_BRANCH,
        commit_sha=tip,
        execution_summary="done",
    )

    assert result["outcome"] == "to_be_audited"
    first, second = fake_backend.calls_to("POST", _RESOLUTON_PATH)
    # ADR-012 key stability: both attempts replay the identical key AND body,
    # so the backend replays instead of transitioning twice.
    assert first.headers[IDEMPOTENCY_HEADER] == second.headers[IDEMPOTENCY_HEADER]
    assert first.body == second.body
    assert spool.entries() == []


def test_submit_resolution_rejects_a_malformed_success_body(
    task_repo: Path, fake_backend: FakeBackend
) -> None:
    tip = _head(task_repo)
    fake_backend.route("POST", _RESOLUTON_PATH, 201, {"resolution": {}, "task": "not-an-object"})
    runtime, _spool = _submit_env(task_repo, fake_backend)

    with pytest.raises(ToolFailure) as excinfo:
        submit_task_resolution(
            runtime,
            task_id=_TASK_ID,
            git_branch=_ASSIGNED_BRANCH,
            commit_sha=tip,
            execution_summary="done",
        )

    assert excinfo.value.translated.code is ErrorCode.SERVER_ERROR


def test_submit_resolution_without_a_spool_never_touches_the_network(
    task_repo: Path, fake_backend: FakeBackend
) -> None:
    tip = _head(task_repo)
    runtime, _spool = _submit_env(task_repo, fake_backend, with_spool=False)

    with pytest.raises(ToolFailure) as excinfo:
        submit_task_resolution(
            runtime,
            task_id=_TASK_ID,
            git_branch=_ASSIGNED_BRANCH,
            commit_sha=tip,
            execution_summary="done",
        )

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.SERVER_ERROR
    assert "spool" in translated.message
    assert fake_backend.calls == []  # the upload was NOT attempted


def test_submit_resolution_payload_carries_no_token(
    task_repo: Path, fake_backend: FakeBackend
) -> None:
    tip = _head(task_repo)
    captured: dict[str, Any] = {}

    def _respond(body: Any) -> tuple[int, Any]:
        captured["body"] = body
        return 201, _resolution_wire(commit_sha=tip)

    fake_backend.route_fn("POST", _RESOLUTON_PATH, _respond)
    runtime, spool = _submit_env(task_repo, fake_backend)

    submit_task_resolution(
        runtime,
        task_id=_TASK_ID,
        git_branch=_ASSIGNED_BRANCH,
        commit_sha=tip,
        execution_summary="done",
    )

    assert FIXTURE_TOKEN not in json.dumps(captured["body"])  # auth rides headers only
    assert spool.entries() == []  # acknowledged; nothing left to leak


def test_submit_resolution_verification_failure_never_reaches_the_backend(
    task_repo: Path, fake_backend: FakeBackend
) -> None:
    runtime, _spool = _submit_env(task_repo, fake_backend)

    with pytest.raises(ToolFailure) as excinfo:
        submit_task_resolution(
            runtime,
            task_id=_TASK_ID,
            git_branch=_ASSIGNED_BRANCH,
            commit_sha="deadbeef" * 5,
            execution_summary="done",
        )

    assert excinfo.value.translated.code is ErrorCode.VALIDATION_ERROR
    assert fake_backend.calls == []  # verify + capture run before any upload
