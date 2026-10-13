"""MT-1.13-04 — permanent per-attachment description caching (G-14).

Run with ``pytest backend/tests/attachments/test_description_cache.py -v``.

Proves:

* generate-once: a second processing run makes **zero** additional
  provider calls and returns byte-identical stored text — WP-1.13's
  acceptance ("descriptions are produced once per attachment");
* the cache is permanent: no TTL/eviction path exists (G-14);
* a failed generation stores nothing, so the retry path still calls
  the provider;
* "no description" (disabled provider / empty caption) is not cached —
  disabled-then-enabled generates normally (G-14 caches descriptions,
  not absence);
* the write-once CAS: a concurrent winner's stored value is adopted
  (documented residual race — both callers may call the provider once,
  MT risk note — but the store holds exactly one value).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import override_settings

from apps.attachments.caption import generate_caption
from apps.attachments.description import (
    DescriptionProviderError,
    set_description_provider,
)
from apps.attachments.ocr import set_ocr_engine
from apps.attachments.pipeline import run_pipeline

from .helpers import (
    RecordingDescriptionProvider,
    StubOcrEngine,
    make_attachment,
    make_project,
    make_task,
    png_bytes,
)

pytestmark = pytest.mark.django_db

CAPTION = "A recorded layout caption."


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
    set_ocr_engine(StubOcrEngine())
    return make_attachment(make_task(make_project()), png_bytes(), name="cached.png")


def _run(attachment: Any) -> str:
    """One full pipeline run; returns the stored caption afterwards.

    A repeat run on a terminal attachment is de-duplicated (``skipped``,
    MT-1.12-01) — that is exactly the "reprocessing changes nothing"
    half of the generate-once contract.
    """
    from apps.attachments.models import TaskAttachment

    outcome = run_pipeline(str(attachment.pk))
    assert outcome in ("ready", "skipped")
    return str(TaskAttachment.objects.get(pk=attachment.pk).layout_caption)


# --- generate-once (WP-1.13 acceptance) --------------------------------------


def test_second_processing_run_makes_zero_provider_calls(attachment: Any) -> None:
    """Re-running the caption step short-circuits on the stored caption."""
    from apps.attachments.caption import generate_caption

    provider = RecordingDescriptionProvider(CAPTION)
    set_description_provider(provider)

    first = _run(attachment)
    row = type(attachment).objects.get(pk=attachment.pk)
    second = generate_caption(row, image_png=b"x", ocr_text="")  # a retry's caption step

    assert first == CAPTION
    assert second == first  # byte-identical stored text
    assert provider.calls == [str(attachment.pk)]  # exactly one call, ever
    assert _run(attachment) == CAPTION  # a full repeat run changes nothing


def test_cache_is_permanent_no_eviction_path() -> None:
    """G-14 "permanently": the module exposes no TTL or eviction API."""
    from apps.attachments import caption

    public = [name for name in dir(caption) if not name.startswith("_")]
    assert "generate_caption" in public
    forbidden = ("evict", "expire", "ttl", "invalidat", "purge", "drop")
    assert not [name for name in public if any(token in name.lower() for token in forbidden)]


# --- failure and disabled semantics -----------------------------------------


def test_failed_generation_is_not_cached_so_a_retry_regenerates(attachment: Any) -> None:
    """Failure stores nothing; the next healthy caption step generates."""
    from apps.attachments.caption import generate_caption

    failing = RecordingDescriptionProvider(fail_with=DescriptionProviderError("timed out"))
    set_description_provider(failing)
    try:
        assert run_pipeline(str(attachment.pk)) == "ready"  # degrades (MT-1.13-05)
    finally:
        set_description_provider(None)
    assert failing.calls == [str(attachment.pk)]
    assert type(attachment).objects.get(pk=attachment.pk).layout_caption == ""

    row = type(attachment).objects.get(pk=attachment.pk)
    healthy = RecordingDescriptionProvider(CAPTION)
    set_description_provider(healthy)
    try:
        assert generate_caption(row, image_png=b"x", ocr_text="") == CAPTION
    finally:
        set_description_provider(None)
    assert healthy.calls == [str(attachment.pk)]


def test_disabled_then_enabled_generates_normally(attachment: Any) -> None:
    """G-14 caches descriptions, not absence: "" is never a cached value."""
    from apps.attachments.caption import generate_caption

    assert _run(attachment) == ""  # OQ-07 default: disabled, nothing stored

    row = type(attachment).objects.get(pk=attachment.pk)
    provider = RecordingDescriptionProvider(CAPTION)
    set_description_provider(provider)
    try:
        assert generate_caption(row, image_png=b"x", ocr_text="") == CAPTION
    finally:
        set_description_provider(None)
    assert provider.calls == [str(attachment.pk)]


def test_empty_caption_is_not_cached(attachment: Any) -> None:
    """An empty model caption stores nothing (same "absence" reading)."""
    empty = RecordingDescriptionProvider("")
    set_description_provider(empty)
    try:
        assert generate_caption(attachment, image_png=b"x", ocr_text="") == ""
    finally:
        set_description_provider(None)
    assert empty.calls == [str(attachment.pk)]

    provider = RecordingDescriptionProvider(CAPTION)
    set_description_provider(provider)
    try:
        assert generate_caption(attachment, image_png=b"x", ocr_text="") == CAPTION
    finally:
        set_description_provider(None)


# --- write-once CAS ----------------------------------------------------------


def test_concurrent_winner_value_is_adopted_not_overwritten(attachment: Any) -> None:
    """Two attempts: the store keeps exactly the CAS winner's value."""
    from apps.attachments.models import TaskAttachment

    provider = RecordingDescriptionProvider(CAPTION)
    set_description_provider(provider)
    try:
        # Simulate the concurrent winner committing between our miss and
        # our write: seed the column, then generate on the stale instance.
        TaskAttachment.objects.filter(pk=attachment.pk).update(layout_caption="winner")
        attachment.layout_caption = ""  # the stale in-memory view
        returned = generate_caption(attachment, image_png=b"x", ocr_text="")
    finally:
        set_description_provider(None)

    assert returned == "winner"  # loser adopts, never overwrites
    assert TaskAttachment.objects.get(pk=attachment.pk).layout_caption == "winner"
    # The residual race is documented: the provider may be called once
    # more than stored (single-flight would need a lock — MT risk note).
    assert provider.calls == [str(attachment.pk)]
