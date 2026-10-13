"""MT-1.12-05 — page/chunk splitting and token estimation.

Run with ``pytest backend/tests/attachments/test_chunking.py -v``.

Proves the Section 9.5 splitting rules and the WP-1.12 chunk-model
deliverable:

* large PDF → contiguous ``page_number`` 1..N with correct
  ``page_count`` (the Section 19 acceptance's data side);
* every chunk's estimated token count ≤ the configured bound;
* attachment roll-up == the sum of its chunks (FR-ATT-03's field);
* re-running the stage reproduces identical derived data (9.5
  "re-creatable");
* no text is ever dropped (the coverage invariant — MT-1.12-05 risk
  note);
* estimator and bound follow configuration with documented defaults
  (Section 20.4 item 3).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from apps.attachments.chunking import (
    ExtractionResult,
    chars_div_4,
    estimate_tokens,
    get_token_estimator,
    persist_chunks,
    split_text,
)
from apps.attachments.ocr import set_ocr_engine
from apps.attachments.pipeline import run_pipeline

from .helpers import StubOcrEngine, make_attachment, make_project, make_task

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "corpus"
LARGE_PDF = FIXTURES / "large.pdf"
SCREENSHOT = FIXTURES / "screenshot.png"

LONG_DOCUMENT = "\n\n".join(
    f"Paragraph {index} of the corpus wraps several ordinary words "
    "together so the splitter must cut it into token-bounded pieces "
    "without ever dropping a single word from the extracted text."
    for index in range(8)
)


@pytest.fixture(autouse=True)
def media_root(tmp_path: Any) -> Any:
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture(autouse=True)
def default_engine() -> Any:
    set_ocr_engine(None)
    yield
    set_ocr_engine(None)


@pytest.fixture
def task() -> Any:
    return make_task(make_project())


def _deadline() -> float:
    return time.monotonic() + 60


# --- token estimation (documented default method) ---------------------------


def test_default_estimator_is_chars_div_4() -> None:
    """``ceil(chars/4)``: the documented default, zero for empty text."""
    assert chars_div_4("") == 0
    assert chars_div_4("abcd") == 1
    assert chars_div_4("abcde") == 2
    assert get_token_estimator() is chars_div_4


def test_unknown_estimator_fails_fast() -> None:
    """Section 9.10: an unknown setting never silently degrades."""
    with override_settings(ATTACHMENT_TOKEN_ESTIMATOR="model-accurate"):
        with pytest.raises(ImproperlyConfigured) as caught:
            estimate_tokens("hello")
    assert "chars_div_4" in str(caught.value)


# --- splitting rules ---------------------------------------------------------


def test_split_respects_the_configured_bound() -> None:
    """Every chunk's estimate ≤ bound, including the hard-split edge."""
    with override_settings(ATTACHMENT_CHUNK_MAX_TOKENS=40):
        chunks = split_text(LONG_DOCUMENT)
        assert len(chunks) > 1  # actually split, not one blob
        assert all(estimate_tokens(chunk) <= 40 for chunk in chunks)


def test_long_single_token_is_hard_split_within_bounds() -> None:
    """A pathological 500-char token cannot escape the bound."""
    monster = "x" * 500
    with override_settings(ATTACHMENT_CHUNK_MAX_TOKENS=16):
        chunks = split_text(monster)
        assert all(estimate_tokens(chunk) <= 16 for chunk in chunks)
        assert "".join(chunks) == monster  # coverage survives the split


def test_split_never_drops_text_coverage_invariant() -> None:
    """The risk-note coverage assertion: joined chunk text equals the
    extracted text modulo whitespace separators."""
    with override_settings(ATTACHMENT_CHUNK_MAX_TOKENS=25):
        chunks = split_text(LONG_DOCUMENT)
    assert " ".join(" ".join(chunks).split()) == " ".join(LONG_DOCUMENT.split())


def test_empty_text_yields_no_chunks() -> None:
    """Nothing to split → nothing stored (and a zero roll-up below)."""
    assert split_text("   \n\n  ") == []


# --- persistence: pages, roll-up, determinism (acceptance items 1-4) ---------

PAGE_COUNT = 12


def test_large_pdf_yields_contiguous_numbered_pages_with_total(task: Any) -> None:
    """12-page PDF → chunks page_number 1..N contiguous, page_count = N."""
    set_ocr_engine(StubOcrEngine())
    attachment = make_attachment(task, LARGE_PDF.read_bytes(), name="large.pdf")

    assert run_pipeline(str(attachment.pk)) == "ready"

    row = type(attachment).objects.get(pk=attachment.pk)
    pages = sorted(
        value
        for value in row.chunks.values_list("page_number", flat=True).distinct()
        if value is not None
    )
    assert pages == list(range(1, PAGE_COUNT + 1))
    assert row.page_count == PAGE_COUNT
    sequences = list(row.chunks.values_list("sequence", flat=True))
    assert sorted(sequences) == list(range(len(sequences)))  # dense, no gaps


def test_roll_up_equals_sum_of_chunk_tokens(task: Any) -> None:
    """FR-ATT-03: ``token_estimate`` is exactly the chunks' sum."""
    attachment = make_attachment(task, LONG_DOCUMENT.encode(), name="long.md", mime="text/markdown")

    assert run_pipeline(str(attachment.pk)) == "ready"

    row = type(attachment).objects.get(pk=attachment.pk)
    chunk_sum = sum(row.chunks.values_list("token_estimate", flat=True))
    assert row.token_estimate == chunk_sum
    assert row.token_estimate > 0


def test_rerun_replaces_derived_chunks_deterministically(task: Any) -> None:
    """Derived data is re-creatable: same input → identical rows."""
    attachment = make_attachment(task, LONG_DOCUMENT.encode(), name="long.md", mime="text/markdown")
    assert run_pipeline(str(attachment.pk)) == "ready"
    row = type(attachment).objects.get(pk=attachment.pk)
    first = list(row.chunks.values_list("sequence", "page_number", "text", "token_estimate"))

    # Re-run the persistence stage directly (the entry guard's CAS is
    # MT-1.12-07's; derived writes themselves are plain replace).
    persist_chunks(row, ExtractionResult(text=LONG_DOCUMENT))

    second = list(row.chunks.values_list("sequence", "page_number", "text", "token_estimate"))
    assert second == first


def test_documents_take_the_token_bounded_path_and_images_the_page_path(
    task: Any,
) -> None:
    """DOCX/Markdown/plain → page_number null, page_count null; image
    OCR → single page (Section 9.5's two splitting shapes)."""
    doc = make_attachment(task, b"plain words here\n", name="a.txt", mime="text/plain")
    assert run_pipeline(str(doc.pk)) == "ready"
    doc_row = type(doc).objects.get(pk=doc.pk)
    assert doc_row.page_count is None
    assert set(doc_row.chunks.values_list("page_number", flat=True)) == {None}

    set_ocr_engine(StubOcrEngine("single page transcript"))
    shot = make_attachment(task, SCREENSHOT.read_bytes(), name="shot.png")
    assert run_pipeline(str(shot.pk)) == "ready"
    shot_row = type(shot).objects.get(pk=shot.pk)
    assert shot_row.page_count == 1
    assert set(shot_row.chunks.values_list("page_number", flat=True)) == {1}


def test_bound_override_is_honoured_persistently(task: Any) -> None:
    """The configured bound flows into persistence, not just the helper."""
    attachment = make_attachment(task, LONG_DOCUMENT.encode(), name="long.md", mime="text/markdown")
    with override_settings(ATTACHMENT_CHUNK_MAX_TOKENS=30):
        assert run_pipeline(str(attachment.pk)) == "ready"
    row = type(attachment).objects.get(pk=attachment.pk)
    assert row.chunks.count() > 1
    assert all(chunk.token_estimate <= 30 for chunk in row.chunks.all())
