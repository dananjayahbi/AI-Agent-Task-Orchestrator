"""MT-1.14-02 — format-preference resolution (the Section 9.5 table).

Run with ``pytest backend/tests/attachments/test_content_formats.py -v``.

One case per retrieval-table row on processed fixtures (image, PDF,
DOCX, Markdown — the MT-1.12-08 corpus, processed hermetically):

* ``auto`` — text-safe by default (Section 10.4 step 4): documents
  resolve to paginated ``markdown``, images to ``text_ocr``;
* ``image_base64`` — the normalized image for images,
  ``ATTACHMENT_UNSUPPORTED_FORMAT`` (415) for non-images;
* ``text_ocr`` — transcript plus layout description, tolerating an
  absent description (MT-1.13-05's degraded case);
* ``markdown`` — the extracted markdown page; images answer 415;
* unknown ``format`` values answer ``VALIDATION_ERROR``; cross-project
  agent tokens answer ``AUTH_FORBIDDEN_PROJECT`` (Section 12.2).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.attachments.derived import NORMALIZED_IMAGE_NAME
from apps.attachments.storage import derived_key, get_storage

from .helpers import (
    MARKDOWN_BYTES,
    agent_client,
    envelope_code,
    make_project,
    make_task,
    owner_client,
    png_bytes,
    process_ready,
)

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "corpus"
CONTENT_URL = "/api/v1/attachments/{attachment_id}/content?{query}"

TRANSCRIPT = "hermetic ocr transcript"


@pytest.fixture(autouse=True)
def media_root(tmp_path: Path) -> Any:
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture
def project() -> Any:
    return make_project()


@pytest.fixture
def task(project: Any) -> Any:
    return make_task(project)


@pytest.fixture
def owner() -> APIClient:
    return owner_client()


def _get(owner: APIClient, attachment_id: Any, query: str = "format=auto") -> Any:
    return owner.get(CONTENT_URL.format(attachment_id=attachment_id, query=query))


# --- auto (Section 9.5 table row 1; Section 10.4 step 4) ---------------------


def test_auto_on_an_image_is_text_safe(owner: APIClient, task: Any) -> None:
    """Vision capability is unknown at REST → text_ocr (OCR + description)."""
    attachment = process_ready(task, png_bytes(), name="shot.png", transcript=TRANSCRIPT)
    body = cast(dict[str, Any], _get(owner, attachment.pk).json())
    assert body["format"] == "text_ocr"
    assert TRANSCRIPT in body["content"]
    assert body["image_base64"] is None


def test_auto_on_a_document_is_paginated_markdown(owner: APIClient, task: Any) -> None:
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    body = cast(dict[str, Any], _get(owner, attachment.pk).json())
    assert body["format"] == "markdown"
    assert body["page_number"] == 1 and body["total_pages"] == 1
    assert "**markdown**" in body["content"]
    assert body["image_base64"] is None


# --- image_base64 (table row 2) ----------------------------------------------


def test_image_base64_returns_the_normalized_image(owner: APIClient, task: Any) -> None:
    """The Section 9.5 stage-2 artifact — the derived PNG, not the original."""
    attachment = process_ready(task, png_bytes(300, 150), name="wide.png")
    body = cast(dict[str, Any], _get(owner, attachment.pk, "format=image_base64").json())

    assert body["format"] == "image_base64"
    assert body["media_type"] == "image/png"
    assert body["content"] is None  # binary path: no text field, no banner

    import base64

    derived = get_storage().get(derived_key(str(attachment.pk), NORMALIZED_IMAGE_NAME))
    assert base64.b64decode(body["image_base64"]) == derived


def test_image_base64_on_a_non_image_is_unsupported_format(owner: APIClient, task: Any) -> None:
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    response = _get(owner, attachment.pk, "format=image_base64")
    assert response.status_code == 415
    assert envelope_code(response) == "ATTACHMENT_UNSUPPORTED_FORMAT"


# --- text_ocr (table row 3) --------------------------------------------------


def test_text_ocr_returns_transcript_plus_layout_description(owner: APIClient, task: Any) -> None:
    attachment = process_ready(task, png_bytes(), name="shot.png", transcript=TRANSCRIPT)
    body = cast(dict[str, Any], _get(owner, attachment.pk, "format=text_ocr").json())
    assert body["format"] == "text_ocr"
    assert TRANSCRIPT in body["content"]
    assert body["description"] is not None  # the field exists even when empty


def test_text_ocr_tolerates_an_absent_description(owner: APIClient, task: Any) -> None:
    """MT-1.13-05 degraded case: transcript alone, no failure (Section 9.5)."""
    from apps.attachments.models import TaskAttachment

    attachment = process_ready(task, png_bytes(), name="shot.png", transcript=TRANSCRIPT)
    TaskAttachment.objects.filter(pk=attachment.pk).update(layout_caption="")
    body = cast(dict[str, Any], _get(owner, attachment.pk, "format=text_ocr").json())
    assert TRANSCRIPT in body["content"]
    assert body["description"] == ""  # absent, delivered as the empty string


def test_text_ocr_on_a_never_ocrd_document_is_unsupported_format(
    owner: APIClient, task: Any
) -> None:
    """DOCX/Markdown/plain have no OCR representation (table read literally)."""
    attachment = process_ready(task, (FIXTURES / "sample.docx").read_bytes(), name="plan.docx")
    response = _get(owner, attachment.pk, "format=text_ocr")
    assert response.status_code == 415
    assert envelope_code(response) == "ATTACHMENT_UNSUPPORTED_FORMAT"


# --- markdown (table row 4) --------------------------------------------------


@pytest.mark.parametrize(
    "label,filename",
    [("notes.md", "notes.md"), ("plan.docx", "sample.docx"), ("text.pdf", "text.pdf")],
)
def test_markdown_serves_every_document_type(
    owner: APIClient, task: Any, label: str, filename: str
) -> None:
    """Markdown resolves for Markdown, DOCX and PDF (Section 9.5 stage 3)."""
    if label.endswith(".md"):
        data = MARKDOWN_BYTES
    else:  # the corpus's genuinely-structured fixtures (processable)
        data = (FIXTURES / filename).read_bytes()
    attachment = process_ready(task, data, name=label)
    body = cast(dict[str, Any], _get(owner, attachment.pk, "format=markdown").json())
    assert body["format"] == "markdown"
    assert isinstance(body["content"], str)


def test_markdown_on_an_image_is_unsupported_format(owner: APIClient, task: Any) -> None:
    attachment = process_ready(task, png_bytes(), name="shot.png")
    response = _get(owner, attachment.pk, "format=markdown")
    assert response.status_code == 415
    assert envelope_code(response) == "ATTACHMENT_UNSUPPORTED_FORMAT"


def test_markdown_pages_a_pdf_by_document_page(owner: APIClient, task: Any) -> None:
    """The text-PDF fixture pages by its extracted pages (page-based path)."""
    attachment = process_ready(task, (FIXTURES / "text.pdf").read_bytes(), name="text.pdf")
    body = cast(dict[str, Any], _get(owner, attachment.pk, "format=markdown").json())
    assert body["page_number"] == 1
    assert body["total_pages"] == attachment.page_count


# --- parameters and authorization --------------------------------------------


def test_unknown_format_value_answers_validation_error(owner: APIClient, task: Any) -> None:
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    response = _get(owner, attachment.pk, "format=gif")
    assert response.status_code == 400
    assert envelope_code(response) == "VALIDATION_ERROR"


def test_cross_project_agent_token_is_forbidden(owner: APIClient, task: Any) -> None:
    """ADR-004 zero-bleed: a foreign agent token never reads content."""
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    other_project = make_project(pid="PID00002")
    foreign = agent_client(owner, other_project.pk)
    response = foreign.get(CONTENT_URL.format(attachment_id=attachment.pk, query="format=auto"))
    assert response.status_code == 403
    assert envelope_code(response) == "AUTH_FORBIDDEN_PROJECT"


def test_scoped_agent_token_may_read_content(owner: APIClient, task: Any, project: Any) -> None:
    """The Section 9.2 caller cell: Owner **or** the project's agent."""
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    agent = agent_client(owner, project.pk)
    response = agent.get(CONTENT_URL.format(attachment_id=attachment.pk, query="format=auto"))
    assert response.status_code == 200, response.content
