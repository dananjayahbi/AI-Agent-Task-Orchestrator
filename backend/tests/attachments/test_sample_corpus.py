"""MT-1.12-08 — sample-corpus tests: screenshot, scanned PDF, text PDF,
DOCX, Markdown (plus the large PDF for page numbering).

Run with ``pytest backend/tests/attachments/test_sample_corpus.py -v``
— the single command that demonstrates the WP-1.12 acceptance
(Section 20.4 item 1).

**Invocation shape (documented for the WP):** uploads go through the
real multipart endpoint (MT-1.11-03's path), and the worker task runs
**synchronously in-process** by installing the enqueue seam as
``process_attachment_task.apply`` — eager Celery execution, no broker,
no daemon. A second, Compose-level run exercises the *real* worker
(the seam defaults to ``delay`` under dev settings once
``DJANGO_SETTINGS_MODULE`` is not the unit layer) — recorded in the WP
changelog with this host's result.

**OCR honesty** (MT-1.12-02/08 rule): the engine fixture delegates to
real Tesseract when the binary is present and to a stub otherwise;
transcript assertions assert fixture needles only on the real path and
non-emptiness everywhere — never weakened, always marked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from django.test import override_settings
from pypdf import PdfReader

from apps.attachments.derived import NORMALIZED_IMAGE_NAME
from apps.attachments.models import ProcessingStatus, TaskAttachment
from apps.attachments.ocr import (
    OcrEngine,
    TesseractOcrEngine,
    set_ocr_engine,
    tesseract_available,
)
from apps.attachments.pipeline import process_attachment_task
from apps.attachments.services import set_enqueue_seam
from apps.attachments.storage import derived_key, get_storage
from apps.attachments.validation import DOCX_MIME
from apps.events.models import Event

from .helpers import StubOcrEngine, make_project, make_task, owner_client, upload

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CORPUS_DIR = FIXTURES / "corpus"

#: The Section 19 sample set — exactly these five — plus the large PDF.
CORPUS = {
    "screenshot.png": "image",
    "scanned.pdf": "scanned",
    "text.pdf": "text",
    "sample.docx": "docx",
    "sample.md": "markdown",
    "large.pdf": "large",
}

#: Engine needles — asserted only where the real engine ran.
SCREENSHOT_NEEDLE = "form saved successfully"
SCANNED_NEEDLE = "hello orchestrator pipeline"

UPLOAD_URL = "/api/v1/tasks/{task_id}/attachments"
DETAIL_URL = "/api/v1/attachments/{attachment_id}"

#: A deliberately broken member (magic bytes, no structure): must end
#: ``failed`` with a non-empty human-readable reason (acceptance).
BROKEN_PDF = b"%PDF-1.4\nthis is not a real pdf structure at all\n%%EOF\n"


class RecordingEngine:
    """Delegating engine: records calls, forwards to the real/stub inner."""

    name = "recording"

    def __init__(self, inner: OcrEngine) -> None:
        self.inner = inner
        self.calls: list[str] = []

    def recognize(self, image: bytes, *, mime_type: str) -> str:
        self.calls.append(mime_type)
        return self.inner.recognize(image, mime_type=mime_type)


@pytest.fixture(autouse=True)
def media_root(tmp_path: Any) -> Any:
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture
def engine() -> Any:
    """Real Tesseract when available, honest stub otherwise (marked)."""
    inner: OcrEngine = (
        TesseractOcrEngine() if tesseract_available() else StubOcrEngine("stub corpus transcript")
    )
    recording = RecordingEngine(inner)
    set_ocr_engine(recording)
    yield recording
    set_ocr_engine(None)


@pytest.fixture
def sync_pipeline() -> Any:
    """The documented eager invocation: upload → task.apply in-process."""

    def run_now(attachment_id: str) -> None:
        result = process_attachment_task.apply(args=[attachment_id])
        if not result.successful():
            raise result.result

    set_enqueue_seam(run_now)
    yield
    set_enqueue_seam(None)


@pytest.fixture
def owner() -> Any:
    return owner_client()


@pytest.fixture
def task() -> Any:
    return make_task(make_project())


def _upload(owner: Any, task: Any, filename: str) -> dict[str, Any]:
    """POST one corpus member like a real client; return the descriptor.

    The upload response is a snapshot at enqueue time (``uploaded`` —
    the MT-1.11 contract, unchanged by eager execution), so tests read
    the **post-pipeline** state through the detail endpoint.
    """
    data = (CORPUS_DIR / filename).read_bytes()
    content_type = DOCX_MIME if filename.endswith(".docx") else None
    response = owner.post(
        UPLOAD_URL.format(task_id=task.pk),
        {"file": upload(data, name=filename, content_type=content_type)},
        format="multipart",
    )
    assert response.status_code in (200, 201), response.content
    return cast(dict[str, Any], response.json())


def _final(owner: Any, attachment_id: str) -> dict[str, Any]:
    """The descriptor as the API serves it *after* the pipeline ran."""
    response = owner.get(DETAIL_URL.format(attachment_id=attachment_id))
    assert response.status_code == 200, response.content
    return cast(dict[str, Any], response.json())


def _row(attachment_id: str) -> TaskAttachment:
    return TaskAttachment.objects.get(pk=attachment_id)


# --- corpus integrity (acceptance item 1; risk note: provenance) ------------


def test_corpus_is_exactly_the_section_19_sample_set_plus_large() -> None:
    """Exactly six files, all present, all small (committed, license-clean,
    generated by build_fixtures.py — provenance in the WP changelog)."""
    present = {path.name for path in CORPUS_DIR.iterdir() if path.is_file()}
    assert present == set(CORPUS)
    for name in present:
        size = (CORPUS_DIR / name).stat().st_size
        assert 0 < size < 500_000, f"{name} is {size} bytes — keep fixtures small"


def test_scanned_member_is_genuinely_image_only() -> None:
    """Re-validate the fixture property inside this suite — a text-layer
    'scan' would make the corpus OCR assertions pass vacuously."""
    reader = PdfReader(CORPUS_DIR / "scanned.pdf")
    assert all(not (page.extract_text() or "").strip() for page in reader.pages)


# --- the matrix: every member reaches ready with its derived data ------------


def test_every_corpus_member_reaches_ready(
    task: Any, owner: Any, sync_pipeline: Any, engine: RecordingEngine
) -> None:
    """One task, all six members uploaded through the endpoint: every
    descriptor reports ``ready`` with token count and summary (Section
    19 WP-1.12 acceptance; FR-ATT-03/07)."""
    uploaded = [_upload(owner, task, name) for name in CORPUS]
    descriptors = [_final(owner, d["id"]) for d in uploaded]
    statuses = {d["processing_status"] for d in descriptors}
    assert statuses == {ProcessingStatus.READY}
    for descriptor in descriptors:
        assert descriptor["failure_reason"] is None
        assert isinstance(descriptor["token_count"], int)
        assert descriptor["token_count"] > 0
        assert descriptor["short_description"]
    # Exactly one processing + one ready event per attachment (9.6).
    assert Event.objects.filter(type="attachment.processing", task_id=task.pk).count() == len(
        CORPUS
    )
    assert Event.objects.filter(type="attachment.ready", task_id=task.pk).count() == len(CORPUS)
    assert Event.objects.filter(type="attachment.failed", task_id=task.pk).count() == 0


def test_screenshot_derived_data(
    task: Any, owner: Any, sync_pipeline: Any, engine: RecordingEngine
) -> None:
    """Screenshot: normalized image artifact + OCR transcript + summary."""
    descriptor = _upload(owner, task, "screenshot.png")
    row = _row(descriptor["id"])
    assert row.ocr_text.strip()
    if tesseract_available():
        assert SCREENSHOT_NEEDLE in row.ocr_text.lower()
    storage = get_storage()
    assert storage.exists(derived_key(str(row.pk), NORMALIZED_IMAGE_NAME))
    assert row.description
    assert row.layout_caption == ""  # provider disabled (OQ-07 default)


def test_text_pdf_never_touches_ocr(
    task: Any, owner: Any, sync_pipeline: Any, engine: RecordingEngine
) -> None:
    """Text PDF: embedded text extracted, engine not invoked once."""
    descriptor = _upload(owner, task, "text.pdf")
    row = _row(descriptor["id"])
    assert "Text page number 1 of 12" in row.extracted_markdown
    assert engine.calls == []
    assert row.page_count == 1


def test_scanned_pdf_used_the_ocr_fallback(
    task: Any, owner: Any, sync_pipeline: Any, engine: RecordingEngine
) -> None:
    """Scanned PDF: fallback invoked, transcript became the page text."""
    descriptor = _upload(owner, task, "scanned.pdf")
    row = _row(descriptor["id"])
    assert engine.calls  # OCR ran for the image-only page
    assert row.extracted_markdown.strip()
    if tesseract_available():
        assert SCANNED_NEEDLE in row.extracted_markdown.lower()


def test_docx_and_markdown_extraction(
    task: Any, owner: Any, sync_pipeline: Any, engine: RecordingEngine
) -> None:
    """DOCX structure and Markdown pass-through reach ready."""
    docx = _row(_upload(owner, task, "sample.docx")["id"])
    assert docx.extracted_markdown.startswith("# Project Alpha Plan")
    assert "| Key | Value |" in docx.extracted_markdown

    markdown = _row(_upload(owner, task, "sample.md")["id"])
    assert markdown.extracted_markdown.startswith("# Sample Notes")
    assert "\r" not in markdown.extracted_markdown

    for row in (docx, markdown):
        assert row.chunks.exists()
        assert row.token_estimate == sum(row.chunks.values_list("token_estimate", flat=True))
        assert row.description


def test_large_pdf_yields_contiguous_numbered_pages(
    task: Any, owner: Any, sync_pipeline: Any, engine: RecordingEngine
) -> None:
    """Large PDF: chunk page numbers 1..N contiguous, page_count = N."""
    row = _row(_upload(owner, task, "large.pdf")["id"])
    pages = sorted(
        value
        for value in row.chunks.values_list("page_number", flat=True).distinct()
        if value is not None
    )
    assert pages == list(range(1, 13))
    assert row.page_count == 12
    sequences = sorted(row.chunks.values_list("sequence", flat=True))
    assert sequences == list(range(len(sequences)))


def test_broken_member_fails_with_a_human_readable_reason(
    task: Any, owner: Any, sync_pipeline: Any, engine: RecordingEngine
) -> None:
    """The acceptance's other branch: deliberately broken input →
    ``failed`` with a non-empty reason, worker intact."""
    response = owner.post(
        UPLOAD_URL.format(task_id=task.pk),
        {"file": upload(BROKEN_PDF, name="broken.pdf", content_type=None)},
        format="multipart",
    )
    assert response.status_code in (200, 201), response.content
    descriptor = _final(owner, response.json()["id"])
    assert descriptor["processing_status"] == ProcessingStatus.FAILED
    assert descriptor["failure_reason"]  # non-empty, human-readable
    assert Event.objects.filter(type="attachment.failed", task_id=task.pk).count() == 1
    # A successful upload answers a descriptor, never an error envelope.
    assert "error" not in descriptor


# --- the full-matrix status summary (single-command acceptance) -------------


def test_corpus_outcomes_are_ready_or_clear_failure(
    task: Any, owner: Any, sync_pipeline: Any, engine: RecordingEngine
) -> None:
    """Literal reading of Section 19's acceptance: every corpus member
    ends ``ready``; a broken sibling ends ``failed`` with a reason —
    both observed through the public descriptor API in one run."""
    outcomes: dict[str, tuple[str, str | None]] = {}
    for name in CORPUS:
        uploaded = _upload(owner, task, name)
        descriptor = _final(owner, uploaded["id"])
        outcomes[name] = (descriptor["processing_status"], descriptor["failure_reason"])

    broken_response = owner.post(
        UPLOAD_URL.format(task_id=task.pk),
        {"file": upload(BROKEN_PDF, name="also-broken.pdf", content_type=None)},
        format="multipart",
    )
    broken = _final(owner, broken_response.json()["id"])
    outcomes["broken.pdf"] = (
        broken["processing_status"],
        broken["failure_reason"],
    )

    for name, (status, reason) in outcomes.items():
        assert status in (ProcessingStatus.READY, ProcessingStatus.FAILED), name
        if status == ProcessingStatus.FAILED:
            assert reason, f"{name} failed without a human-readable reason"
        else:
            assert reason is None, name
