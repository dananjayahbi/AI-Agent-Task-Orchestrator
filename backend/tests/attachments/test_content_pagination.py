"""MT-1.14-03 — pagination metadata on retrieved content (Section 9.5).

Run with ``pytest backend/tests/attachments/test_content_pagination.py -v``.

Proves:

* paginated retrieval returns exactly the Section 9.5 triple —
  ``page_number``, ``total_pages`` and the page's token count;
* ``page`` defaults to 1; one-based numbering; ``total_pages = 1`` for
  single-page documents (the recorded convention);
* page-oriented documents (PDF) page by **document page**; token-bounded
  documents (Markdown/DOCX) serve one **chunk** per call;
* out-of-range, non-integer, sub-1 and unknown query parameters answer
  ``VALIDATION_ERROR`` (the closed catalog has no page code);
* non-paginated formats (``image_base64``, ``text_ocr``) never
  fabricate page metadata (MT-1.14-03 asymmetry).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from .helpers import (
    MARKDOWN_BYTES,
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

#: A Markdown document long enough to split into several token-bounded
#: chunks (the chunk bound is 512 tokens ≈ 2048 chars — the documented
#: default, so this stays above it under any smaller override too).
LONG_MARKDOWN = ("\n\n".join(f"Paragraph {index} " + "word " * 120 for index in range(12))).encode()


@pytest.fixture(autouse=True)
def media_root(tmp_path: Path) -> Any:
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture
def task() -> Any:
    return make_task(make_project())


@pytest.fixture
def owner() -> APIClient:
    return owner_client()


def _get(owner: APIClient, attachment_id: Any, query: str) -> Any:
    return owner.get(CONTENT_URL.format(attachment_id=attachment_id, query=query))


# --- the Section 9.5 triple --------------------------------------------------


def test_multi_page_document_walk(owner: APIClient, task: Any) -> None:
    """page=1 … total_pages visits every page exactly once, metadata per page."""
    attachment = process_ready(task, LONG_MARKDOWN, name="long.md")
    first = cast(dict[str, Any], _get(owner, attachment.pk, "format=markdown&page=1").json())
    total = first["total_pages"]
    assert total and total > 1  # this fixture really paginates

    seen: list[str] = []
    for page in range(1, total + 1):
        body = cast(
            dict[str, Any], _get(owner, attachment.pk, f"format=markdown&page={page}").json()
        )
        assert body["page_number"] == page
        assert body["total_pages"] == total
        assert isinstance(body["token_count"], int) and body["token_count"] > 0
        seen.append(body["content"])
    assert len(set(seen)) == total  # every chunk served exactly once


def test_token_count_matches_the_stored_chunk_estimate(owner: APIClient, task: Any) -> None:
    """Token counts are WP-1.12's stored numbers — never recomputed (risk note)."""
    from apps.attachments.models import AttachmentChunk

    attachment = process_ready(task, LONG_MARKDOWN, name="long.md")
    chunk = AttachmentChunk.objects.filter(attachment=attachment).order_by("sequence").first()
    assert chunk is not None
    body = cast(dict[str, Any], _get(owner, attachment.pk, "format=markdown&page=1").json())
    assert body["token_count"] == chunk.token_estimate


def test_token_bounded_document_pages_by_chunk(owner: APIClient, task: Any) -> None:
    """No page_number on chunks → each chunk *is* one page (9.5: page or chunk)."""
    attachment = process_ready(task, LONG_MARKDOWN, name="long.md")
    body = cast(dict[str, Any], _get(owner, attachment.pk, "format=markdown&page=2").json())
    assert body["page_number"] == 2
    assert body["total_pages"] == attachment.chunks.count()


def test_page_based_document_pages_by_document_page(owner: APIClient, task: Any) -> None:
    """A PDF's page numbers are its document pages (page_count, not chunks)."""
    attachment = process_ready(task, (FIXTURES / "text.pdf").read_bytes(), name="text.pdf")
    body = cast(dict[str, Any], _get(owner, attachment.pk, "format=markdown").json())
    assert body["total_pages"] == attachment.page_count
    assert body["page_number"] == 1


# --- defaults, single page, out-of-range -------------------------------------


def test_missing_page_defaults_to_one(owner: APIClient, task: Any) -> None:
    attachment = process_ready(task, LONG_MARKDOWN, name="long.md")
    default = cast(dict[str, Any], _get(owner, attachment.pk, "format=markdown").json())
    explicit = cast(dict[str, Any], _get(owner, attachment.pk, "format=markdown&page=1").json())
    assert default == explicit


def test_single_page_document_reports_total_pages_one(owner: APIClient, task: Any) -> None:
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    body = cast(dict[str, Any], _get(owner, attachment.pk, "format=markdown").json())
    assert body["page_number"] == 1
    assert body["total_pages"] == 1


def test_out_of_range_page_answers_validation_error(owner: APIClient, task: Any) -> None:
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    response = _get(owner, attachment.pk, "format=markdown&page=2")
    assert response.status_code == 400
    assert envelope_code(response) == "VALIDATION_ERROR"


@pytest.mark.parametrize("page", ["zero", "1.5", "0", "-1"])
def test_invalid_page_answers_validation_error(owner: APIClient, task: Any, page: str) -> None:
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    response = _get(owner, attachment.pk, f"format=markdown&page={page}")
    assert response.status_code == 400
    assert envelope_code(response) == "VALIDATION_ERROR"


def test_unknown_query_parameter_answers_validation_error(owner: APIClient, task: Any) -> None:
    """MT-0.5-04 discipline: unknown parameters are rejected, never ignored."""
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    response = _get(owner, attachment.pk, "format=markdown&cursor=abc")
    assert response.status_code == 400
    assert envelope_code(response) == "VALIDATION_ERROR"


# --- the documented asymmetry ------------------------------------------------


def test_non_paginated_formats_omit_page_metadata(owner: APIClient, task: Any) -> None:
    """No fabricated page fields on image_base64 / text_ocr (risk note)."""
    image = process_ready(task, png_bytes(), name="shot.png")
    body = cast(dict[str, Any], _get(owner, image.pk, "format=image_base64").json())
    assert body["page_number"] is None
    assert body["total_pages"] is None
    assert body["token_count"] is None

    text = cast(dict[str, Any], _get(owner, image.pk, "format=text_ocr").json())
    assert text["page_number"] is None
    assert text["total_pages"] is None
    assert text["token_count"] is None


def test_page_is_ignored_by_non_paginated_formats(owner: APIClient, task: Any) -> None:
    """A stray page value neither errors nor fabricates metadata (recorded)."""
    image = process_ready(task, png_bytes(), name="shot.png")
    body = cast(dict[str, Any], _get(owner, image.pk, "format=text_ocr&page=3").json())
    assert body["format"] == "text_ocr"
    assert body["page_number"] is None
