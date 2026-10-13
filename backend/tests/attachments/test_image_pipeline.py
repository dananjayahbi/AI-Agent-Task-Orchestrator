"""MT-1.12-02 — image normalization and OCR stage.

Run with ``pytest backend/tests/attachments/test_image_pipeline.py -v``.

Proves the Section 9.5 image rules:

* long edge capped at the configured limit, aspect ratio preserved;
* metadata (EXIF etc.) stripped from the **derived** copy while the
  stored original stays byte-identical;
* a transcript is produced by the *configured* engine — the real
  Tesseract path runs wherever the binary exists (skip-marked
  otherwise) and the hermetic stub path proves the wiring everywhere;
* with the description provider disabled (OQ-07 default) the stage
  completes OCR-only — no WP-1.13 dependency.

Real-OCR invocation (the host default, ``ORCHESTRATOR_OCR_ENGINE`` =
``tesseract``): nothing special — the stage shells out. Hermetic runs:
``set_ocr_engine(StubOcrEngine(...))`` (auto-selected here when
``tesseract_available()`` is false).
"""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from PIL import Image

from apps.attachments.derived import NORMALIZED_IMAGE_NAME
from apps.attachments.description import (
    DescriptionProvider,
    DisabledDescriptionProvider,
    get_description_provider,
)
from apps.attachments.errors import PermanentPipelineError
from apps.attachments.ocr import (
    OcrEngine,
    TesseractOcrEngine,
    get_ocr_engine,
    set_ocr_engine,
    tesseract_available,
)
from apps.attachments.pipeline import run_pipeline
from apps.attachments.pipeline_images import normalize_image, process_image
from apps.attachments.storage import derived_key, get_storage

from .helpers import PNG_BYTES, StubOcrEngine, make_attachment, make_project, make_task

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "corpus"
SCREENSHOT = FIXTURES / "screenshot.png"

#: What real Tesseract reliably recovers from SCREENSHOT (substring
#: assertion only — MT-1.12-08 risk note: never exact full text).
SCREENSHOT_NEEDLE = "form saved successfully"


@pytest.fixture(autouse=True)
def media_root(tmp_path: Any) -> Any:
    """Uploads and derived artifacts land in an isolated media root."""
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture(autouse=True)
def default_engine() -> Any:
    """Every test starts from the configured-engine path (no stale override)."""
    set_ocr_engine(None)
    yield
    set_ocr_engine(None)


@pytest.fixture
def task() -> Any:
    return make_task(make_project())


def _deadline() -> float:
    return time.monotonic() + 60


def _png_bytes(width: int, height: int, *, exif: bytes | None = None) -> bytes:
    image = Image.new("RGB", (width, height), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", exif=exif or b"")
    return buffer.getvalue()


# --- normalization (Section 9.5 stage 2; acceptance items 1-2) ---------------


def test_long_edge_is_capped_with_aspect_ratio_preserved() -> None:
    """3000×1500 → 1024×512 under a 1024 cap: long edge bound, ratio 2:1."""
    out = normalize_image(_png_bytes(3000, 1500), max_edge=1024)
    with Image.open(io.BytesIO(out)) as image:
        assert image.format == "PNG"
        assert max(image.size) == 1024
        assert image.size == (1024, 512)  # 2:1 preserved exactly


def test_small_image_is_not_upscaled() -> None:
    """Normalization never enlarges (cap only): 100×400 stays 100×400."""
    out = normalize_image(_png_bytes(100, 400), max_edge=1024)
    with Image.open(io.BytesIO(out)) as image:
        assert image.size == (100, 400)


def test_metadata_is_stripped_from_the_derived_copy() -> None:
    """EXIF survives into the derived PNG nowhere: no ``exif`` info, no
    marker bytes — while the source carried it."""
    exif = Image.Exif()
    exif[271] = "TestCamMake"  # Make
    exif[272] = "TestCamModel"  # Model
    source = _png_bytes(64, 64, exif=exif.tobytes())
    assert b"TestCamMake" in source  # the fixture really carries metadata

    out = normalize_image(source, max_edge=1024)
    assert b"TestCamMake" not in out
    assert b"TestCamModel" not in out
    with Image.open(io.BytesIO(out)) as image:
        assert "exif" not in image.info
        assert dict(image.getexif()) == {}


def test_image_over_the_pixel_ceiling_fails_with_a_reason(monkeypatch: Any) -> None:
    """A header declaring more pixels than the Section 12.1 ceiling →
    permanent failure, no decode attempted (ceiling injected small)."""
    monkeypatch.setattr("apps.attachments.pipeline_images.MAX_IMAGE_PIXELS", 100)
    with pytest.raises(PermanentPipelineError) as caught:
        normalize_image(_png_bytes(64, 64), max_edge=1024)
    assert "ceiling" in caught.value.reason


# --- OCR (FR-ATT-02; configured engine; acceptance items 3-4) ----------------


def test_engine_selection_follows_configuration() -> None:
    """Section 9.10: the setting picks the engine; unknown names fail fast."""
    with override_settings(OCR_ENGINE="tesseract"):
        assert isinstance(get_ocr_engine(), TesseractOcrEngine)
    with override_settings(OCR_ENGINE="paddleocr"):
        from django.core.exceptions import ImproperlyConfigured

        with pytest.raises(ImproperlyConfigured):
            get_ocr_engine()
    stub = StubOcrEngine()
    set_ocr_engine(stub)
    assert get_ocr_engine() is stub


def test_stub_engine_path_persists_the_transcript(task: Any) -> None:
    """Hermetic path (no binary needed): transcript stored, stage ready."""
    stub = StubOcrEngine("engine output for the screenshot")
    set_ocr_engine(stub)
    attachment = make_attachment(task, SCREENSHOT.read_bytes(), name="shot.png")

    assert run_pipeline(str(attachment.pk)) == "ready"

    row = type(attachment).objects.get(pk=attachment.pk)
    assert row.ocr_text == stub.text
    assert stub.calls == ["image/png"]
    assert row.chunks.get().page_number == 1  # page-oriented OCR output


@pytest.mark.skipif(not tesseract_available(), reason="tesseract binary not on PATH")
def test_real_tesseract_recovers_the_screenshot_text(task: Any) -> None:
    """The Section 6.6 default engine on the committed screenshot —
    skip-marked, never stubbed, so the real path is proven where it can
    run (MT-1.12-02 honest-marking rule)."""
    attachment = make_attachment(task, SCREENSHOT.read_bytes(), name="shot.png")

    assert run_pipeline(str(attachment.pk)) == "ready"

    row = type(attachment).objects.get(pk=attachment.pk)
    assert SCREENSHOT_NEEDLE in row.ocr_text.lower()


def test_description_provider_disabled_completes_ocr_only(task: Any) -> None:
    """OQ-07 default: provider ``disabled`` → empty caption, stage and
    pipeline complete with no WP-1.13 code (Section 9.5 degradation)."""
    set_ocr_engine(StubOcrEngine())
    assert isinstance(get_description_provider(), DisabledDescriptionProvider)
    attachment = make_attachment(task, SCREENSHOT.read_bytes(), name="shot.png")

    assert run_pipeline(str(attachment.pk)) == "ready"

    row = type(attachment).objects.get(pk=attachment.pk)
    assert row.layout_caption == ""
    assert row.ocr_text != ""  # OCR-only is a complete state, not a gap


def test_unimplemented_description_provider_fails_fast() -> None:
    """A configured-but-undelivered provider is a config error (9.10).

    WP-1.13 delivered ``disabled`` and ``anthropic-vision``; the
    Section 9.5 ``local model`` stays undelivered (no OQ asks for it),
    so it is the fail-fast example now.
    """
    from django.core.exceptions import ImproperlyConfigured

    with override_settings(DESCRIPTION_PROVIDER="local-model"):
        with pytest.raises(ImproperlyConfigured) as caught:
            get_description_provider()
    assert "local-model" in str(caught.value)
    assert "anthropic-vision" in str(caught.value)  # names the supported set


# --- derived data, originals, idempotence (Section 9.5; risk notes) ---------


def test_original_is_untouched_and_normalized_lives_under_a_derived_key(
    task: Any, media_root: Path
) -> None:
    """Stripping happens on the derived copy only; the stored original
    stays byte-identical and the derived artifact uses its own key."""
    set_ocr_engine(StubOcrEngine())
    original = _png_bytes(64, 64)
    attachment = make_attachment(task, original, name="tiny.png")

    assert run_pipeline(str(attachment.pk)) == "ready"

    storage = get_storage()
    assert storage.get(attachment.storage_key) == original  # untouched
    derived = derived_key(str(attachment.pk), NORMALIZED_IMAGE_NAME)
    assert derived != attachment.storage_key
    assert storage.exists(derived)
    with Image.open(io.BytesIO(storage.get(derived))) as image:
        assert max(image.size) == 64


def test_reprocessing_replaces_derived_data_instead_of_duplicating(
    task: Any, media_root: Path
) -> None:
    """Repeat runs overwrite the one derived artifact (re-creatable)."""
    set_ocr_engine(StubOcrEngine())
    attachment = make_attachment(task, SCREENSHOT.read_bytes(), name="shot.png")

    first = process_image(attachment, SCREENSHOT.read_bytes(), deadline=_deadline())
    second = process_image(attachment, SCREENSHOT.read_bytes(), deadline=_deadline())
    assert first == second  # deterministic derived data

    derived = derived_key(str(attachment.pk), NORMALIZED_IMAGE_NAME)
    assert get_storage().exists(derived)
    # Exactly one artifact file for this attachment under the media root.
    derived_dir = (media_root / "derived").rglob("*")
    files = [path for path in derived_dir if path.is_file()]
    assert len(files) == 1


def test_undecodable_image_fails_permanently_with_a_reason(task: Any) -> None:
    """Magic-byte-valid but undecodable content (the WP-1.11 junk PNG)
    reaches the stage and fails it — human-readable, no crash."""
    attachment = make_attachment(task, PNG_BYTES, name="fake.png")

    assert run_pipeline(str(attachment.pk)) == "failed"

    row = type(attachment).objects.get(pk=attachment.pk)
    assert "decodable" in row.failure_detail


def test_process_image_runs_end_to_end_on_the_screenshot(task: Any) -> None:
    """Stage-level happy path with the stub engine: transcript + caption
    persisted, page-shaped result for MT-1.12-05."""
    stub = StubOcrEngine("captured text")
    set_ocr_engine(stub)
    attachment = make_attachment(task, SCREENSHOT.read_bytes(), name="shot.png")

    result = process_image(attachment, SCREENSHOT.read_bytes(), deadline=_deadline())
    assert result.pages == (stub.text,)
    assert attachment.ocr_text == stub.text
    assert attachment.layout_caption == ""


def test_stub_engine_type_conformance_and_reset() -> None:
    """The stub satisfies the pluggable interface (runtime-checkable)."""
    stub = StubOcrEngine()
    set_ocr_engine(stub)
    engine: OcrEngine = get_ocr_engine()
    assert isinstance(engine, OcrEngine)
    assert isinstance(get_description_provider(), DescriptionProvider)
    set_ocr_engine(None)
