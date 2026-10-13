"""MT-2.6-05 — local submission spool: persistence, restart recovery, hygiene.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.6-checkpoint-submit-tools/
MT-2.6-05-local-retention-retry.md (parent plan Sections 10.10, 18 chaos row;
NFR-04, ADR-012, NFR-12). The centerpiece test kills a submission mid-flight
(no acknowledgment arrives), restarts over the same directory, and proves the
retry completes **once** with the **original** idempotency key and body —
the ADR-012 pairing a "fresh key per retry" bug would break.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from orchestrator_bridge.config import Settings
from orchestrator_bridge.idempotency import IDEMPOTENCY_HEADER
from orchestrator_bridge.submission_spool import (
    DEFAULT_MAX_AGE_DAYS,
    SpoolEntry,
    SubmissionSpool,
    default_spool_dir,
)
from orchestrator_bridge.transport import ApiClient
from tests.conftest import (
    FIXTURE_TOKEN,
    FakeBackend,
    build_binding,
    build_settings,
    envelope_wire,
)

_TASK_ID = "PID00007-T004"
_PATH = f"/api/v1/tasks/{_TASK_ID}/resolution"
_KEY = "fixture-key-0001-POST-api-v1-tasks-resolution"
_BODY: dict[str, Any] = {
    "session_id": "fixture-session-0001",
    "lease_generation": 2,
    "git_branch": "feat/PID00007-T004",
    "commit_sha": "a" * 40,
    "execution_summary": "did the work",
    "requires_human_attention": False,
    "risk_justification": "",
    "patch": "diff --git a/feature.py b/feature.py\n+print('feature')\n",
    "changed_files": ["feature.py"],
    "diff_summary": {"insertions": 1, "deletions": 0, "files_changed": 1},
}


def _hold(spool: SubmissionSpool, **overrides: Any) -> SpoolEntry:
    fields: dict[str, Any] = {
        "project_id": "PID00007",
        "task_id": _TASK_ID,
        "path": _PATH,
        "body": dict(_BODY),
        "idempotency_key": _KEY,
    }
    fields.update(overrides)
    return spool.hold(**fields)


def _client(fake: FakeBackend | None = None, *, settings: Settings | None = None) -> ApiClient:
    backend = fake if fake is not None else FakeBackend()
    return ApiClient.for_binding(build_binding(), settings or build_settings(), send=backend.send)


def _outage_client(attempts: list[int] | None = None) -> ApiClient:
    """A client whose wire always fails like an unreachable backend."""

    def _send(_method: str, _url: str, _headers: Any, _body: bytes | None, _timeout: float) -> Any:
        if attempts is not None:
            attempts.append(1)
        raise OSError("connection refused (simulated outage)")

    return ApiClient.for_binding(build_binding(), build_settings(), send=_send)


def test_submission_spool_hold_persists_before_returning(tmp_path: Path) -> None:
    spool = SubmissionSpool(tmp_path / "spool")

    entry = _hold(spool)

    on_disk = spool.directory / f"{entry.id}.json"
    assert on_disk.is_file()  # durable before any network attempt could happen
    document = json.loads(on_disk.read_text(encoding="utf-8"))
    assert document["body"] == _BODY
    assert document["idempotency_key"] == _KEY
    assert document["attempts"] == 0
    # Round-trip through the reader the resume sweep uses.
    assert SpoolEntry.from_file(document) == entry


def test_submission_spool_ack_clears_the_entry(tmp_path: Path) -> None:
    spool = SubmissionSpool(tmp_path / "spool")
    entry = _hold(spool)

    spool.resolve(entry.id)

    assert spool.entries() == []
    assert not (spool.directory / f"{entry.id}.json").exists()


def test_submission_spool_survives_a_kill_mid_submission_and_replays_once(
    tmp_path: Path,
) -> None:
    # Section 18 chaos row: kill the bridge mid-submission. The upload goes
    # out, the backend never acknowledges, the process dies — the payload and
    # its key must survive on disk and complete after restart, exactly once.
    directory = tmp_path / "spool"
    spool = SubmissionSpool(directory)
    entry = _hold(spool)

    outage_report = spool.resume(_outage_client(), project_id="PID00007")
    assert outage_report.retained == 1  # no ack → the entry stays held
    kept = directory / f"{entry.id}.json"
    assert kept.is_file()
    assert json.loads(kept.read_text(encoding="utf-8"))["attempts"] == 1

    # "Restart": a fresh process rebuilds the spool over the same directory.
    restarted = SubmissionSpool(directory)
    fake = FakeBackend()
    fake.route("POST", _PATH, 201, {"resolution": {"id": "r1"}, "task": {"id": _TASK_ID}})
    report = restarted.resume(_client(fake), project_id="PID00007")

    assert report.replayed == 1
    (call,) = fake.calls_to("POST", _PATH)
    # ADR-012: the ORIGINAL key and the ORIGINAL body — the backend replays
    # instead of storing a second resolution or firing a second transition.
    assert call.headers[IDEMPOTENCY_HEADER] == _KEY
    assert call.body == _BODY
    assert restarted.entries() == []  # the acknowledgment cleared it


def _client_settings_with_retries() -> Settings:
    return build_settings(retry_max_attempts=2, retry_base_delay_seconds=0.0)


def _failing_send(attempts: list[int]) -> Any:
    def _send(_method: str, _url: str, _headers: Any, _body: bytes | None, _timeout: float) -> Any:
        attempts.append(1)
        raise OSError("still down")

    return _send


def test_submission_spool_backs_off_within_one_sweep(tmp_path: Path) -> None:
    spool = SubmissionSpool(tmp_path / "spool")
    entry = _hold(spool)
    attempts: list[int] = []
    client = ApiClient.for_binding(
        build_binding(), _client_settings_with_retries(), send=_failing_send(attempts)
    )

    report = spool.resume(client, project_id="PID00007")

    assert report.retained == 1  # one resume-level failure after the client's own backoff
    assert len(attempts) == 2  # the WP-2.3 transport retried with backoff
    document = json.loads((spool.directory / f"{entry.id}.json").read_text(encoding="utf-8"))
    assert document["attempts"] == 1


def test_submission_spool_discards_definitive_rejections(tmp_path: Path) -> None:
    # Retryable vs non-retryable classification: a state conflict can never
    # succeed as-is — keeping it would loop on a dead outcome.
    spool = SubmissionSpool(tmp_path / "spool")
    _hold(spool)
    fake = FakeBackend()
    fake.route(
        "POST",
        _PATH,
        409,
        json.loads(envelope_wire(409, "TASK_STATE_CONFLICT", "already submitted").body),
    )

    report = spool.resume(_client(fake), project_id="PID00007")

    assert report.discarded == 1
    assert spool.entries() == []


def test_submission_spool_keeps_other_projects_entries(tmp_path: Path) -> None:
    # A project's token never replays another project's work: foreign entries
    # wait for their own session (and bounded retention covers the abandoned).
    spool = SubmissionSpool(tmp_path / "spool")
    foreign = _hold(spool, project_id="PID00099")
    fake = FakeBackend()

    report = spool.resume(_client(fake), project_id="PID00007")

    assert report.foreign == 1
    assert [entry.id for entry in spool.entries()] == [foreign.id]
    assert fake.calls == []


def test_submission_spool_payloads_contain_no_secrets(tmp_path: Path) -> None:
    # Spooled patches are sensitive by nature, but the payload contract puts
    # auth in headers only — no token, no environment values on disk.
    spool = SubmissionSpool(tmp_path / "spool")
    entry = _hold(spool)

    text = (spool.directory / f"{entry.id}.json").read_text(encoding="utf-8")

    assert FIXTURE_TOKEN not in text
    assert "Authorization" not in text
    assert str(tmp_path) not in text  # no absolute host paths in the payload


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits")
def test_submission_spool_files_are_owner_only(tmp_path: Path) -> None:
    spool = SubmissionSpool(tmp_path / "spool")
    entry = _hold(spool)

    mode = (spool.directory / f"{entry.id}.json").stat().st_mode

    assert mode & 0o077 == 0  # owner read/write only (MT-2.6-05 hygiene)


def test_submission_spool_prunes_stuck_entries_with_an_operator_message(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    directory = tmp_path / "spool"
    long_ago = datetime.now(tz=UTC) - timedelta(days=DEFAULT_MAX_AGE_DAYS + 3)
    SubmissionSpool(directory, now=lambda: long_ago).hold(
        project_id="PID00007",
        task_id=_TASK_ID,
        path=_PATH,
        body=dict(_BODY),
        idempotency_key=_KEY,
    )
    spool = SubmissionSpool(directory)  # bounded retention (Section 20.4 item 3)
    with caplog.at_level(logging.WARNING, logger="bridge.submission_spool"):
        entries = spool.entries()

    assert entries == []
    assert list(directory.glob("*.json")) == []
    (record,) = [r for r in caplog.records if getattr(r, "event", None) == "spool_pruned"]
    assert record.__dict__["count"] == 1  # the extra= field the spool logged
    assert "stuck submission spool entries" in record.getMessage()  # operator message


def test_submission_spool_skips_unreadable_files_without_crashing(tmp_path: Path) -> None:
    spool = SubmissionSpool(tmp_path / "spool")
    entry = _hold(spool)
    (spool.directory / "bogus.json").write_text("{not json", encoding="utf-8")

    assert [item.id for item in spool.entries()] == [entry.id]  # skipped, not fatal


def test_submission_spool_hold_failure_surfaces_as_an_oserror(tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_text("a file where a directory belongs", encoding="utf-8")
    spool = SubmissionSpool(blocked / "spool")

    with pytest.raises(OSError):
        _hold(spool)


def test_submission_spool_resume_never_raises_on_an_unreachable_backend(
    tmp_path: Path,
) -> None:
    spool = SubmissionSpool(tmp_path / "spool")
    _hold(spool)

    report = spool.resume(_outage_client(), project_id="PID00007")

    assert report.replayed == 0 and report.retained == 1  # startup never dies


def test_default_spool_dir_honors_the_operator_override(monkeypatch: pytest.MonkeyPatch) -> None:
    override = Path("D:/somewhere/else/spool")
    monkeypatch.setenv("ORCHESTRATOR_SPOOL_DIR", str(override))

    assert default_spool_dir() == override


def test_default_spool_dir_lives_outside_any_repository() -> None:
    from orchestrator_bridge.config import default_user_config_path

    candidate = default_user_config_path().parent / "submission-spool"

    # The hermetic fixture strips ORCHESTRATOR_* — the default path is the
    # user config area, which lives outside every Git repository.
    assert default_spool_dir() == candidate
    assert candidate.name == "submission-spool"
