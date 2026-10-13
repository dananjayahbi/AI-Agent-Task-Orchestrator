"""MT-1.12-04 — DOCX and Markdown extraction.

Run with ``pytest backend/tests/attachments/test_document_extraction.py -v``.

Proves the Section 9.5 documents-stage extraction rules:

* DOCX → markdown-flavoured text in document order (headings, bullets,
  tables represented — FR-ATT-02 "parse");
* Markdown → normalised (line endings/BOM) with **content unchanged**;
* ``text/plain`` → pass-through (the Section 9.5 allowlist's trivial
  path);
* malformed/hostile containers (missing part, broken XML, zip-bomb
  declaration, non-UTF-8) → human-readable permanent failures, worker
  survives (Section 12.1).
"""

from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings

from apps.attachments.errors import PermanentPipelineError
from apps.attachments.models import TaskAttachment
from apps.attachments.pipeline import run_pipeline
from apps.attachments.pipeline_documents import (
    DOCX_MAX_UNCOMPRESSED_BYTES,
    docx_to_markdown,
    process_document,
)
from apps.attachments.storage import get_storage, hash_bytes
from apps.attachments.validation import DOCX_MIME

from .helpers import PLAINTEXT_BYTES, make_attachment, make_project, make_task

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "corpus"
SAMPLE_DOCX = FIXTURES / "sample.docx"
SAMPLE_MD = FIXTURES / "sample.md"


@pytest.fixture(autouse=True)
def media_root(tmp_path: Any) -> Any:
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture
def task() -> Any:
    return make_task(make_project())


def _deadline() -> float:
    return time.monotonic() + 60


def _attachment(task: Any, data: bytes, name: str, mime: str | None) -> Any:
    return make_attachment(task, data, name=name, mime=mime)


# --- DOCX (acceptance item 1) ------------------------------------------------


def test_docx_extracts_structure_in_document_order(task: Any) -> None:
    """Heading → ``#``, bullets → ``-``, table → pipe rows, in order."""
    attachment = _attachment(task, SAMPLE_DOCX.read_bytes(), "plan.docx", DOCX_MIME)

    assert run_pipeline(str(attachment.pk)) == "ready"

    text = type(attachment).objects.get(pk=attachment.pk).extracted_markdown
    assert text.startswith("# Project Alpha Plan")
    assert "This DOCX carries structure for extraction." in text
    assert "- First deliverable" in text
    assert "- Second deliverable" in text
    assert "| Key | Value |" in text
    assert "| Owner | QA |" in text
    # Document order: heading before list before table.
    positions = [
        text.index("# Project Alpha Plan"),
        text.index("- First deliverable"),
        text.index("| Key | Value |"),
    ]
    assert positions == sorted(positions)


def test_docx_extraction_is_deterministic() -> None:
    """Same bytes → identical markdown (pure function of the XML)."""
    with zipfile.ZipFile(io.BytesIO(SAMPLE_DOCX.read_bytes())) as archive:
        xml = archive.read("word/document.xml")
    assert docx_to_markdown(xml) == docx_to_markdown(xml)


# --- Markdown and plain text (acceptance items 2-3) -------------------------


def test_markdown_passes_through_with_normalised_line_endings(task: Any) -> None:
    """CRLF input → LF output; content otherwise byte-for-byte the same."""
    raw = SAMPLE_MD.read_bytes().replace(b"\n", b"\r\n")
    attachment = _attachment(task, raw, "notes.md", "text/markdown")

    assert run_pipeline(str(attachment.pk)) == "ready"

    out = type(attachment).objects.get(pk=attachment.pk).extracted_markdown
    assert "\r" not in out
    assert out == SAMPLE_MD.read_bytes().decode("utf-8")  # unchanged content


def test_markdown_leading_bom_is_stripped(task: Any) -> None:
    """Encoding normalisation includes the BOM; nothing else changes."""
    raw = "﻿# Title\n\nBody\n".encode()
    attachment = _attachment(task, raw, "bom.md", "text/markdown")
    assert run_pipeline(str(attachment.pk)) == "ready"
    out = type(attachment).objects.get(pk=attachment.pk).extracted_markdown
    assert out.startswith("# Title")
    assert out.endswith("Body\n")


def test_plain_text_passes_through(task: Any) -> None:
    """The allowlist's trivial path behaves exactly like Markdown."""
    attachment = _attachment(task, PLAINTEXT_BYTES, "notes.txt", "text/plain")
    assert run_pipeline(str(attachment.pk)) == "ready"
    out = type(attachment).objects.get(pk=attachment.pk).extracted_markdown
    assert out == "Just plain text.\n"


# --- hostile input (acceptance item 4; Section 12.1) ------------------------


def test_zip_without_document_part_fails_with_a_reason() -> None:
    """A zip that passes a container sniff but holds no document body →
    the stage's structural guard, called directly (the upload sniffer
    would already have refused this input at the wire)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("readme.txt", "not a word document")
    junk = buffer.getvalue()

    with pytest.raises(PermanentPipelineError) as caught:
        process_document(TaskAttachment(mime_type=DOCX_MIME), junk, deadline=_deadline())
    assert "word/document.xml" in caught.value.reason


def test_malformed_document_xml_fails_with_a_reason(task: Any) -> None:
    """Broken XML inside a container that passes sniffing → the whole
    pipeline fails permanent with a human-readable reason (Section 12.1)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", "<w:document><unclosed>")
    broken = buffer.getvalue()

    attachment = make_attachment(task, SAMPLE_DOCX.read_bytes(), name="ok.docx", mime=DOCX_MIME)
    get_storage().delete(attachment.storage_key)
    get_storage().put(attachment.storage_key, broken)
    TaskAttachment.objects.filter(pk=attachment.pk).update(sha256=hash_bytes(broken))

    assert run_pipeline(str(attachment.pk)) == "failed"
    row = TaskAttachment.objects.get(pk=attachment.pk)
    assert "XML" in row.failure_detail or "xml" in row.failure_detail


def test_zip_bomb_ceiling_trips_on_declared_uncompressed_size(task: Any, monkeypatch: Any) -> None:
    """The declared-uncompressed-size ceiling fires before any read."""
    monkeypatch.setattr("apps.attachments.pipeline_documents.DOCX_MAX_UNCOMPRESSED_BYTES", 16)
    attachment = make_attachment(task, SAMPLE_DOCX.read_bytes(), name="bomb.docx", mime=DOCX_MIME)

    assert run_pipeline(str(attachment.pk)) == "failed"
    row = type(attachment).objects.get(pk=attachment.pk)
    assert "ceiling" in row.failure_detail
    assert DOCX_MAX_UNCOMPRESSED_BYTES == 64 * 1024 * 1024  # documented default


def test_non_utf8_text_fails_permanently() -> None:
    """The stage's decode guard, called directly with invalid bytes."""
    attachment = TaskAttachment(mime_type="text/plain")
    with pytest.raises(PermanentPipelineError) as caught:
        process_document(attachment, b"\xff\xfe\x00not utf8", deadline=_deadline())
    assert "UTF-8" in caught.value.reason
