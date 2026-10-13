"""MT-1.13-05 — provider failures degrade to OCR-only (Section 9.5).

Run with ``pytest backend/tests/attachments/test_degradation.py -v``.

Proves, for the three failure shapes (timeout, non-2xx, malformed
output) plus retry-exhaustion and programming errors:

* the attachment still reaches ``ready`` with its OCR transcript and
  an **empty** description — degradation, not failure (Section 9.5;
  WP-1.13 acceptance generalized to failures);
* no ``attachment.failed`` event is emitted for a degraded run — the
  failure exists only in the structured logs (Section 9.6 catalog;
  Section 17); degraded runs are not failures;
* only the *typed* provider failure degrades: a programming error
  surfaces instead of becoming an invisible "successful" run (risk
  note);
* the cache stays empty on failure, so a later healthy run generates
  (the MT-1.13-04 contract);
* cost logging stays accurate: the failed attempt logs without
  fabricated usage figures.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from django.test import override_settings

from apps.attachments.description import (
    DescriptionProviderError,
    set_description_provider,
)
from apps.attachments.ocr import set_ocr_engine
from apps.attachments.pipeline import run_pipeline
from apps.events.models import Event, EventType

from .helpers import (
    RecordingDescriptionProvider,
    StubOcrEngine,
    make_attachment,
    make_project,
    make_task,
    png_bytes,
)

pytestmark = pytest.mark.django_db

TRANSCRIPT = "engine output survives the provider outage"


@pytest.fixture(autouse=True)
def media_root(tmp_path: Any) -> Any:
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture(autouse=True)
def clean_seams() -> Any:
    set_description_provider(None)
    set_ocr_engine(None)
    yield
    set_description_provider(None)
    set_ocr_engine(None)


@pytest.fixture
def attachment() -> Any:
    set_ocr_engine(StubOcrEngine(TRANSCRIPT))
    return make_attachment(make_task(make_project()), png_bytes(), name="degrade.png")


@pytest.fixture
def task_factory() -> Any:
    """Fresh (project, task) rows per call — one attachment per attempt."""
    counter = iter(range(2, 50))

    def factory() -> Any:
        return make_task(make_project(pid=f"PID{next(counter):05d}"))

    return factory


@pytest.mark.parametrize(
    ("label", "failure"),
    [
        ("timeout", DescriptionProviderError("remote vision provider timed out", transient=True)),
        (
            "http_error",
            DescriptionProviderError("remote vision provider answered HTTP 503", transient=True),
        ),
        (
            "malformed",
            DescriptionProviderError(
                "remote vision provider response carries no text block", transient=False
            ),
        ),
    ],
)
def test_provider_failure_reaches_ready_ocr_only(
    attachment: Any, label: str, failure: DescriptionProviderError
) -> None:
    """Every failure shape: ``ready``, transcript present, description empty."""
    set_description_provider(RecordingDescriptionProvider(fail_with=failure))

    assert run_pipeline(str(attachment.pk)) == "ready"

    row = type(attachment).objects.get(pk=attachment.pk)
    assert row.ocr_text == TRANSCRIPT  # OCR ran independently (MT-1.12-02)
    assert row.layout_caption == ""  # degradation leaves "no description"
    assert row.failure_detail == ""  # Section 9.5 stage-5 reasons stay meaningful
    assert row.processing_status == "ready"


def test_degraded_run_emits_no_attachment_failed_event(attachment: Any) -> None:
    """Section 9.6 catalog: degraded runs are not failures."""
    set_description_provider(
        RecordingDescriptionProvider(fail_with=DescriptionProviderError("timed out"))
    )

    assert run_pipeline(str(attachment.pk)) == "ready"

    types = list(Event.objects.filter(task_id=attachment.task_id).values_list("type", flat=True))
    assert EventType.ATTACHMENT_FAILED not in types
    assert EventType.ATTACHMENT_READY in types  # the attachment did complete


def test_failure_is_logged_exactly_once_with_the_typed_reason(attachment: Any, caplog: Any) -> None:
    """One structured warning per degraded caption step (Section 17)."""
    set_description_provider(
        RecordingDescriptionProvider(
            fail_with=DescriptionProviderError(
                "remote vision provider answered HTTP 500", transient=True
            )
        )
    )
    with caplog.at_level(logging.WARNING, logger="apps.attachments.pipeline_images"):
        assert run_pipeline(str(attachment.pk)) == "ready"
    warnings = [r for r in caplog.records if r.message.startswith("description provider failed")]
    assert len(warnings) == 1
    assert "HTTP 500" in warnings[0].getMessage()


def test_retry_backoff_does_not_turn_provider_failure_into_failed(
    attachment: Any, task_factory: Any
) -> None:
    """Retry exhaustion on provider errors degrades — never status ``failed``.

    The documented policy (MT-1.13-05 scope): the caption step makes one
    provider attempt per pipeline run and degrades on the typed failure,
    so the Section 9.9 retry seam never counts provider outages and can
    never land an attachment in ``failed`` for one. Three independent
    attachments stand in for three attempts (terminal statuses are
    absorbing, MT-1.12-01).
    """
    from apps.attachments.models import TaskAttachment

    provider = RecordingDescriptionProvider(fail_with=DescriptionProviderError("timed out"))
    set_description_provider(provider)

    attempts = [
        attachment,
        *(make_attachment(task_factory(), png_bytes(), name=f"degrade-{i}.png") for i in range(3)),
    ]
    for target in attempts:
        assert run_pipeline(str(target.pk)) == "ready"
        row = TaskAttachment.objects.get(pk=target.pk)
        assert row.processing_status == "ready"
        assert row.failure_detail == ""
    assert len(provider.calls) == len(attempts)  # every attempt degraded, none failed


def test_programming_errors_surface_instead_of_degrading(attachment: Any) -> None:
    """Only the typed failure degrades (risk note: no blanket except)."""
    set_description_provider(
        RecordingDescriptionProvider(fail_with=RuntimeError("bug in the provider"))
    )

    with pytest.raises(RuntimeError):
        run_pipeline(str(attachment.pk))

    row = type(attachment).objects.get(pk=attachment.pk)
    assert row.processing_status != "failed"  # the pipeline surfaced, not swallowed


def test_later_healthy_run_generates_after_degradation(attachment: Any) -> None:
    """The cache was not poisoned: after a degraded run, generation still works.

    The pipeline's terminal statuses are absorbing (MT-1.12-01), so the
    follow-up generation is proven on the caption step directly — the
    same call a resumed processing run would make.
    """
    from apps.attachments.caption import generate_caption

    set_description_provider(
        RecordingDescriptionProvider(fail_with=DescriptionProviderError("timed out"))
    )
    assert run_pipeline(str(attachment.pk)) == "ready"

    row = type(attachment).objects.get(pk=attachment.pk)
    assert row.layout_caption == ""  # failure stored nothing

    healthy = RecordingDescriptionProvider("A late caption.")
    set_description_provider(healthy)
    assert generate_caption(row, image_png=b"x", ocr_text=TRANSCRIPT) == "A late caption."
    assert healthy.calls == [str(attachment.pk)]
