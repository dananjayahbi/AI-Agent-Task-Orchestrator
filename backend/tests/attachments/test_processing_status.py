"""MT-1.12-07 — processing status transitions with retry/backoff.

Run with ``pytest backend/tests/attachments/test_processing_status.py -v``.

Proves Sections 9.5/9.6/9.9 against the state machine and the retry
seam in ``apps.attachments.pipeline``:

* only the four FR-ATT-07 statuses exist; only the linear transitions
  ``uploaded→processing→ready|failed`` are legal (every illegal pair
  rejected — Section 20.3's per-transition rule);
* exactly one ``attachment.processing`` on entry and exactly one
  terminal event per attachment — including the CAS guard against
  stale completions and the resume path;
* transient failures retry with exponential backoff up to the
  configured attempt cap, then land ``failed`` with the reason;
  permanent failures fail immediately;
* the human-readable reason is exposed on the descriptor (FR-ATT-07).

Retry drills run the **task body** synchronously through a stub task
(``_execute(stub, id)``) — the documented no-broker invocation; the
stub exposes exactly the Celery surface the seam uses
(``request.retries`` and ``retry(exc=..., countdown=...)``).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import override_settings

from apps.attachments import pipeline
from apps.attachments.errors import PermanentPipelineError, TransientPipelineError
from apps.attachments.models import ProcessingStatus, TaskAttachment
from apps.attachments.pipeline import _execute, run_pipeline
from apps.attachments.serializers import attachment_descriptor
from apps.attachments.status import (
    LEGAL_TRANSITIONS,
    IllegalTransition,
    assert_legal,
    begin_processing,
    mark_failed,
    mark_ready,
)
from apps.events.models import Event

from .helpers import MARKDOWN_BYTES, make_attachment, make_project, make_task

pytestmark = pytest.mark.django_db

ALL_STATUSES = set(ProcessingStatus.values)

_TRANSITIONS = [
    (ProcessingStatus.UPLOADED, ProcessingStatus.PROCESSING, True),
    (ProcessingStatus.PROCESSING, ProcessingStatus.READY, True),
    (ProcessingStatus.PROCESSING, ProcessingStatus.FAILED, True),
    (ProcessingStatus.UPLOADED, ProcessingStatus.READY, False),
    (ProcessingStatus.UPLOADED, ProcessingStatus.FAILED, False),
    (ProcessingStatus.READY, ProcessingStatus.PROCESSING, False),
    (ProcessingStatus.READY, ProcessingStatus.FAILED, False),
    (ProcessingStatus.READY, ProcessingStatus.UPLOADED, False),
    (ProcessingStatus.FAILED, ProcessingStatus.PROCESSING, False),
    (ProcessingStatus.FAILED, ProcessingStatus.READY, False),
    (ProcessingStatus.FAILED, ProcessingStatus.UPLOADED, False),
    (ProcessingStatus.PROCESSING, ProcessingStatus.UPLOADED, False),
]


class RetryCalled(Exception):
    """Marker: the stub task's ``retry()`` was invoked (Celery raises)."""

    def __init__(self, countdown: int) -> None:
        super().__init__(f"retry at {countdown}s")
        self.countdown = countdown


class FakeTask:
    """The Celery surface ``_execute`` touches — nothing more."""

    def __init__(self, retries: int = 0) -> None:
        from types import SimpleNamespace

        self.request = SimpleNamespace(retries=retries)
        self.countdowns: list[int] = []

    def retry(self, *, exc: BaseException | None = None, countdown: int = 0) -> None:
        self.countdowns.append(countdown)
        raise RetryCalled(countdown)


@pytest.fixture(autouse=True)
def media_root(tmp_path: Any) -> Any:
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture
def task() -> Any:
    return make_task(make_project())


def _events(event_type: str, task: Any) -> list[Event]:
    return list(Event.objects.filter(type=event_type, task_id=task.pk))


def _attachment(task: Any) -> TaskAttachment:
    return make_attachment(task, MARKDOWN_BYTES, name="notes.md", mime="text/markdown")


# --- the transition matrix (Section 20.3: one rule, one test) ----------------


@pytest.mark.parametrize(("source", "target", "legal"), _TRANSITIONS)
def test_transition_matrix(source: str, target: str, legal: bool) -> None:
    """Legal transitions pass the guard; every other pair raises."""
    if legal:
        assert_legal(source, target)
        assert target in LEGAL_TRANSITIONS[source]
    else:
        with pytest.raises(IllegalTransition):
            assert_legal(source, target)


def test_only_the_four_fr_att_07_statuses_exist() -> None:
    """The enum is exactly Section 9.5/FR-ATT-07's set — none added."""
    assert ALL_STATUSES == {"uploaded", "processing", "ready", "failed"}
    assert set(LEGAL_TRANSITIONS) == ALL_STATUSES
    assert LEGAL_TRANSITIONS[ProcessingStatus.READY] == frozenset()  # absorbing
    assert LEGAL_TRANSITIONS[ProcessingStatus.FAILED] == frozenset()


# --- exactly-once events (Sections 9.6, 20.4 item 6) ------------------------


def test_begin_processing_emits_exactly_one_event_and_resumes_silently(
    task: Any,
) -> None:
    """First entry writes the event; re-entry resumes without a second."""
    attachment = _attachment(task)
    assert begin_processing(str(attachment.pk)) == "started"
    assert len(_events("attachment.processing", task)) == 1

    assert begin_processing(str(attachment.pk)) == "resumed"
    assert len(_events("attachment.processing", task)) == 1  # unchanged

    assert mark_ready(str(attachment.pk)) is True
    assert len(_events("attachment.ready", task)) == 1
    # Terminal is absorbing: every later attempt loses the CAS, silently.
    assert begin_processing(str(attachment.pk)) == "gone"
    assert mark_ready(str(attachment.pk)) is False
    assert mark_failed(str(attachment.pk), reason="late failure") is False
    assert len(_events("attachment.ready", task)) == 1
    assert _events("attachment.failed", task) == []


def test_stale_completion_cannot_overwrite_a_terminal_status(task: Any) -> None:
    """Two workers finish one attachment: the loser writes no event and
    no row change (the MT-1.12-07 race risk note)."""
    attachment = _attachment(task)
    begin_processing(str(attachment.pk))
    assert mark_ready(str(attachment.pk)) is True
    # A second, later stage result arrives:
    assert mark_ready(str(attachment.pk)) is False
    assert mark_failed(str(attachment.pk), reason="stale error") is False
    row = TaskAttachment.objects.get(pk=attachment.pk)
    assert row.processing_status == ProcessingStatus.READY
    assert row.failure_detail == ""
    assert len(_events("attachment.ready", task)) == 1
    assert _events("attachment.failed", task) == []


def test_soft_deleted_rows_never_emit(task: Any) -> None:
    """The CAS filters deleted rows: deletion wins, silence follows."""
    from apps.attachments.retention import delete_attachment

    attachment = _attachment(task)
    begin_processing(str(attachment.pk))
    delete_attachment(attachment)
    assert mark_ready(str(attachment.pk)) is False
    assert mark_failed(str(attachment.pk), reason="gone") is False
    assert begin_processing(str(attachment.pk)) == "gone"
    assert _events("attachment.ready", task) == []
    assert _events("attachment.failed", task) == []


def test_full_run_emits_the_exact_event_pair(task: Any) -> None:
    """One processing + one ready, ids in the payloads, no extras."""
    attachment = _attachment(task)
    assert run_pipeline(str(attachment.pk)) == "ready"
    assert len(_events("attachment.processing", task)) == 1
    assert len(_events("attachment.ready", task)) == 1
    ready = _events("attachment.ready", task)[0]
    assert ready.data["attachment_id"] == str(attachment.pk)
    assert ready.data["token_count"] == TaskAttachment.objects.get(pk=attachment.pk).token_estimate


# --- retry classification (Section 9.9) -------------------------------------


def test_transient_failure_retries_with_backoff_then_reaches_ready(
    task: Any, monkeypatch: Any
) -> None:
    """Attempt 1 fails transiently (after entering processing), attempt 2
    fails again under an overridden backoff, attempt 3 resumes — the
    same single processing event throughout — and lands ready."""
    attachment = _attachment(task)

    real_run = pipeline.run_pipeline
    state = {"calls": 0}

    def flaky(attachment_id: str) -> str:
        state["calls"] += 1
        if state["calls"] <= 2:
            begin_processing(attachment_id)  # stages started, then the blip
            raise TransientPipelineError("OCR engine timed out after 30s on one page")
        return real_run(attachment_id)

    monkeypatch.setattr(pipeline, "run_pipeline", flaky)

    first = FakeTask()
    with pytest.raises(RetryCalled) as caught:
        _execute(first, str(attachment.pk))
    assert caught.value.countdown == 60  # documented base backoff (seconds)
    assert TaskAttachment.objects.get(pk=attachment.pk).processing_status == (
        ProcessingStatus.PROCESSING
    )

    with override_settings(ATTACHMENT_RETRY_BACKOFF_SECONDS=5):
        second = FakeTask(retries=1)
        with pytest.raises(RetryCalled) as caught:
            _execute(second, str(attachment.pk))
        assert caught.value.countdown == 10  # base × 2^attempt

    third = FakeTask(retries=2)
    assert _execute(third, str(attachment.pk)) == "ready"

    row = TaskAttachment.objects.get(pk=attachment.pk)
    assert row.processing_status == ProcessingStatus.READY
    assert len(_events("attachment.processing", task)) == 1  # resume ≠ new entry
    assert len(_events("attachment.ready", task)) == 1


def test_retry_exhaustion_lands_failed_with_the_reason(task: Any, monkeypatch: Any) -> None:
    """Transient forever → the configured cap stops the retries and the
    record exposes a human-readable reason (Section 9.5 stage 5)."""
    attachment = _attachment(task)

    def always_transient(attachment_id: str) -> str:
        begin_processing(attachment_id)
        raise TransientPipelineError("storage read failed (transient I/O)")

    monkeypatch.setattr(pipeline, "run_pipeline", always_transient)

    # Attempts 1 and 2 retry (60s, 120s); attempt 3 hits the cap of 3.
    with pytest.raises(RetryCalled):
        _execute(FakeTask(retries=0), str(attachment.pk))
    with pytest.raises(RetryCalled):
        _execute(FakeTask(retries=1), str(attachment.pk))
    assert _execute(FakeTask(retries=2), str(attachment.pk)) == "failed"

    row = TaskAttachment.objects.get(pk=attachment.pk)
    assert row.processing_status == ProcessingStatus.FAILED
    assert "storage read failed" in row.failure_detail
    assert "3 attempts exhausted" in row.failure_detail
    assert len(_events("attachment.processing", task)) == 1
    assert len(_events("attachment.failed", task)) == 1
    assert _events("attachment.ready", task) == []


def test_backoff_and_attempt_cap_follow_configuration(monkeypatch: Any) -> None:
    """Settings drive countdown and cap (documented defaults 60 s / 3)."""

    def transient(attachment_id: str) -> str:
        raise TransientPipelineError("blip")

    monkeypatch.setattr(pipeline, "run_pipeline", transient)

    with override_settings(ATTACHMENT_RETRY_MAX_ATTEMPTS=4, ATTACHMENT_RETRY_BACKOFF_SECONDS=2):
        with pytest.raises(RetryCalled) as caught:
            _execute(FakeTask(), "00000000-0000-0000-0000-000000000000")
        assert caught.value.countdown == 2  # first retry: base × 2^0
    with override_settings(ATTACHMENT_RETRY_MAX_ATTEMPTS=1, ATTACHMENT_RETRY_BACKOFF_SECONDS=60):
        # A single attempt means: fail at once, no retry call.
        assert _execute(FakeTask(), "00000000-0000-0000-0000-000000000000") == "failed"


def test_permanent_failure_never_retries(task: Any) -> None:
    """Checksum corruption: one attempt, immediate ``failed``, no
    ``retry()`` call — permanent is not transient (Section 9.5)."""
    from apps.attachments.storage import get_storage

    attachment = _attachment(task)
    get_storage().delete(attachment.storage_key)
    get_storage().put(attachment.storage_key, MARKDOWN_BYTES + b" corrupt")

    stub = FakeTask()
    assert _execute(stub, str(attachment.pk)) == "failed"
    assert stub.countdowns == []  # never retried

    row = TaskAttachment.objects.get(pk=attachment.pk)
    assert row.processing_status == ProcessingStatus.FAILED
    assert "checksum" in row.failure_detail
    assert len(_events("attachment.processing", task)) == 1
    assert len(_events("attachment.failed", task)) == 1


def test_unexpected_exceptions_are_treated_as_transient(task: Any, monkeypatch: Any) -> None:
    """A bug that escapes the stages is retried, and its stored reason
    carries the exception *type* only — never a message that could
    quote content (Section 12.4)."""
    attachment = _attachment(task)

    def exploding(attachment_id: str) -> str:
        begin_processing(attachment_id)
        raise ValueError("text of the sensitive attachment leaked here")

    monkeypatch.setattr(pipeline, "run_pipeline", exploding)

    with pytest.raises(RetryCalled):
        _execute(FakeTask(retries=0), str(attachment.pk))
    with override_settings(ATTACHMENT_RETRY_MAX_ATTEMPTS=1):
        assert _execute(FakeTask(retries=0), str(attachment.pk)) == "failed"

    row = TaskAttachment.objects.get(pk=attachment.pk)
    assert "ValueError" in row.failure_detail
    assert "sensitive attachment" not in row.failure_detail


# --- reason visibility (FR-ATT-07 "visible") --------------------------------


def test_failure_reason_is_exposed_on_the_descriptor(task: Any) -> None:
    """The descriptor carries ``failure_reason`` == the stored reason."""
    attachment = _attachment(task)
    from apps.attachments.storage import get_storage

    get_storage().delete(attachment.storage_key)
    get_storage().put(attachment.storage_key, b"tampered bytes that break the hash")

    assert run_pipeline(str(attachment.pk)) == "failed"
    row = TaskAttachment.objects.get(pk=attachment.pk)
    descriptor = attachment_descriptor(row)
    assert descriptor["failure_reason"] == row.failure_detail
    assert descriptor["failure_reason"].strip()
    assert descriptor["processing_status"] == ProcessingStatus.FAILED


def test_failure_reason_is_null_while_not_failed(task: Any) -> None:
    """Descriptor stability: null reason on uploaded/ready rows."""
    attachment = _attachment(task)
    descriptor = attachment_descriptor(attachment)
    assert descriptor["failure_reason"] is None
    assert run_pipeline(str(attachment.pk)) == "ready"
    descriptor = attachment_descriptor(TaskAttachment.objects.get(pk=attachment.pk))
    assert descriptor["failure_reason"] is None


def test_permanent_stage_failure_is_recorded_without_retry(task: Any, monkeypatch: Any) -> None:
    """A stage's PermanentPipelineError is caught by the pipeline itself:
    one attempt, immediate ``failed`` with the stage's own reason, no
    retry — classification lives in exactly one place (MT-1.12-07)."""
    attachment = _attachment(task)

    def boom(mime: str) -> Any:
        raise PermanentPipelineError("unsupported document type 'application/x'")

    monkeypatch.setattr(pipeline, "stage_for", boom)

    stub = FakeTask()
    assert _execute(stub, str(attachment.pk)) == "failed"
    assert stub.countdowns == []  # never retried

    row = TaskAttachment.objects.get(pk=attachment.pk)
    assert row.processing_status == ProcessingStatus.FAILED
    assert "unsupported document type" in row.failure_detail
    assert len(_events("attachment.processing", task)) == 1
    assert len(_events("attachment.failed", task)) == 1
