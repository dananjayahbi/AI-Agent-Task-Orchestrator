"""MT-1.12-03 — PDF text extraction with OCR fallback for scanned pages.

Run with ``pytest backend/tests/attachments/test_pdf_pipeline.py -v``.

Proves the Section 9.5 documents-stage order:

* text-layer PDF → embedded text, OCR **never invoked** (spy engine);
* image-only ("scanned") PDF → OCR fallback used — and the fixture
  property is validated in setup (empty text layer), so the assertion
  can't pass vacuously (MT-1.12-03 risk note);
* mixed PDF → only the scanned page is OCRed;
* malformed/hostile PDF → human-readable permanent failure, worker
  (task) survives;
* page boundaries preserved: 12 pages → a contiguous 12-element tuple
  (the data MT-1.12-05 numbers).

Real-Tesseract variant runs only where the binary exists (skip-marked);
the spy/fallback assertions use the hermetic stub engine, so ordering
logic is engine-independent.
"""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from pypdf import PdfReader

from apps.attachments.errors import PermanentPipelineError, TransientPipelineError
from apps.attachments.ocr import set_ocr_engine, tesseract_available
from apps.attachments.pipeline import run_pipeline
from apps.attachments.pipeline_pdf import (
    MAX_PDF_PAGES,
    PAGE_SEPARATOR,
    process_pdf,
)

from .helpers import StubOcrEngine, make_attachment, make_project, make_task

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "corpus"
TEXT_PDF = FIXTURES / "text.pdf"
SCANNED_PDF = FIXTURES / "scanned.pdf"
MIXED_PDF = FIXTURES.parent / "mixed.pdf"  # sibling fixture (MT-1.12-03 only)
LARGE_PDF = FIXTURES / "large.pdf"

#: What real Tesseract reliably recovers from SCANNED_PDF (substring).
SCANNED_NEEDLE = "hello orchestrator pipeline"

#: Deliberately broken PDF: magic bytes present, structure garbage.
MALFORMED_PDF = b"%PDF-1.4\n1 0 obj\n<< /Kids (not an array)\ntrailer\n%%EOF\n"


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


def _layer_empty(pdf: bytes) -> bool:
    """Fixture-property check: every page has an empty text layer."""
    reader = PdfReader(io.BytesIO(pdf))
    return all(not (page.extract_text() or "").strip() for page in reader.pages)


# --- text layer first (Section 9.5; acceptance item 1) ----------------------


def test_text_pdf_extracts_without_invoking_ocr(task: Any) -> None:
    """Spy engine records nothing: the embedded layer serves every page."""
    spy = StubOcrEngine("MUST NOT APPEAR")
    set_ocr_engine(spy)
    attachment = make_attachment(task, TEXT_PDF.read_bytes(), name="text.pdf")

    assert run_pipeline(str(attachment.pk)) == "ready"

    assert spy.calls == []
    row = type(attachment).objects.get(pk=attachment.pk)
    assert "Text page number 1 of 12" in row.extracted_markdown
    assert PAGE_SEPARATOR.join(row.extracted_markdown.split(PAGE_SEPARATOR)) == (
        row.extracted_markdown
    )


# --- OCR fallback for scanned pages (acceptance item 2) ----------------------


def test_scanned_fixture_is_genuinely_image_only() -> None:
    """Validate the fixture property itself — a text-layered 'scan' would
    make every fallback assertion pass vacuously (risk note)."""
    assert _layer_empty(SCANNED_PDF.read_bytes())
    reader = PdfReader(io.BytesIO(MIXED_PDF.read_bytes()))
    assert (reader.pages[0].extract_text() or "").strip()  # page 1 has text
    assert not (reader.pages[1].extract_text() or "").strip()  # page 2 does not


def test_scanned_pdf_falls_back_to_ocr(task: Any) -> None:
    """Image-only page → engine invoked, transcript becomes the page text."""
    stub = StubOcrEngine("OCR recovered the scan body")
    set_ocr_engine(stub)
    attachment = make_attachment(task, SCANNED_PDF.read_bytes(), name="scan.pdf")

    assert run_pipeline(str(attachment.pk)) == "ready"

    assert stub.calls == ["image/png"]
    row = type(attachment).objects.get(pk=attachment.pk)
    assert row.extracted_markdown == "OCR recovered the scan body"
    assert row.ocr_text == ""  # image OCR pages feed extraction, not ocr_text


def test_mixed_pdf_ocrs_only_the_scanned_pages(task: Any) -> None:
    """Page 1 from its layer (no OCR), page 2 from OCR — exactly one call."""
    stub = StubOcrEngine("page two via fallback")
    set_ocr_engine(stub)
    attachment = make_attachment(task, MIXED_PDF.read_bytes(), name="mixed.pdf")

    assert run_pipeline(str(attachment.pk)) == "ready"

    assert stub.calls == ["image/png"]  # only the image-only page
    row = type(attachment).objects.get(pk=attachment.pk)
    pages = row.extracted_markdown.split(PAGE_SEPARATOR)
    assert pages[0].strip() == "Mixed page one: plain text layer, no OCR needed."
    assert pages[1].strip() == "page two via fallback"


@pytest.mark.skipif(not tesseract_available(), reason="tesseract binary not on PATH")
def test_real_ocr_on_the_scanned_fixture(task: Any) -> None:
    """The Section 6.6 engine against the committed scanned PDF —
    skip-marked honesty, substring-only assertion (engine-fragile)."""
    attachment = make_attachment(task, SCANNED_PDF.read_bytes(), name="scan.pdf")

    assert run_pipeline(str(attachment.pk)) == "ready"

    row = type(attachment).objects.get(pk=attachment.pk)
    assert SCANNED_NEEDLE in row.extracted_markdown.lower()


# --- page structure (Section 19 acceptance: numbered pages data) ------------


def test_page_boundaries_are_preserved_for_numbering(task: Any, monkeypatch: Any) -> None:
    """12-page PDF → 12 contiguous pages, each holding its own label —
    exactly the data MT-1.12-05 turns into ``page_number``/``total_pages``."""
    set_ocr_engine(StubOcrEngine())
    attachment = make_attachment(task, LARGE_PDF.read_bytes(), name="large.pdf")

    assert run_pipeline(str(attachment.pk)) == "ready"

    row = type(attachment).objects.get(pk=attachment.pk)
    pages = row.extracted_markdown.split(PAGE_SEPARATOR)
    assert len(pages) == 12
    for index, page in enumerate(pages, start=1):
        assert f"Text page number {index} of 12" in page
    assert row.page_count == 12


def test_page_ceiling_rejects_oversize_pdfs(task: Any, monkeypatch: Any) -> None:
    """Section 12.1 in-process limit: above MAX_PDF_PAGES → permanent."""
    monkeypatch.setattr("apps.attachments.pipeline_pdf.MAX_PDF_PAGES", 2)
    attachment = make_attachment(task, LARGE_PDF.read_bytes(), name="large.pdf")
    assert run_pipeline(str(attachment.pk)) == "failed"
    row = type(attachment).objects.get(pk=attachment.pk)
    assert "ceiling" in row.failure_detail
    assert MAX_PDF_PAGES == 2000  # documented default unchanged elsewhere


# --- hostile input (Section 12.1; acceptance item 4) ------------------------


def test_malformed_pdf_fails_with_a_human_readable_reason(task: Any) -> None:
    """Magic-byte-valid garbage → ``failed`` with a parse reason; the task
    returns normally (worker survives — the stage converts every parser
    exception, the pipeline never crashes)."""
    attachment = make_attachment(task, MALFORMED_PDF, name="evil.pdf", mime="application/pdf")

    assert run_pipeline(str(attachment.pk)) == "failed"

    row = type(attachment).objects.get(pk=attachment.pk)
    assert row.processing_status == "failed"
    assert "PDF" in row.failure_detail
    assert row.failure_detail.strip()  # non-empty, human-readable


def test_empty_pdf_object_fails_the_stage_with_a_clear_reason() -> None:
    """Zero-byte input to the stage → ``empty`` in the reason (the entry
    path would stop earlier at type re-detection — covered in
    ``test_pipeline_entry`` — so this pins the stage's own guard)."""
    from apps.attachments.models import TaskAttachment

    with pytest.raises(PermanentPipelineError) as caught:
        process_pdf(TaskAttachment(), b"", deadline=_deadline())
    assert "empty" in caught.value.reason


def test_deadline_expiry_is_transient(task: Any) -> None:
    """An expired parse budget is a transient failure (retry-eligible)."""
    attachment = make_attachment(task, TEXT_PDF.read_bytes(), name="text.pdf")
    with pytest.raises(TransientPipelineError):
        process_pdf(attachment, TEXT_PDF.read_bytes(), deadline=time.monotonic() - 1)


def test_stage_converts_parser_exceptions_to_permanent_errors() -> None:
    """Direct stage call on garbage: the conversion happens *inside* the
    stage — callers only ever see PipelineErrors (worker-survival rule)."""
    from apps.attachments.models import TaskAttachment

    with pytest.raises(PermanentPipelineError) as caught:
        process_pdf(TaskAttachment(), MALFORMED_PDF, deadline=_deadline())
    assert "parsed" in caught.value.reason
