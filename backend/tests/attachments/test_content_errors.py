"""MT-1.14-05 — the retrieval error matrix (catalog codes only; 20.4 item 5).

Run with ``pytest backend/tests/attachments/test_content_errors.py -v``.

Proves:

* ``ATTACHMENT_NOT_READY`` (HTTP 409 per Section 9.5's pin) for every
  format while the attachment is not ``ready`` — ``uploaded``,
  ``processing`` and ``failed`` (``failed`` carries the stored
  human-readable reason; the recorded reading for a status the catalog
  names no code for);
* ``ATTACHMENT_UNSUPPORTED_FORMAT`` (415) for every unsupported
  format/type combination of the Section 9.5 table;
* ``VALIDATION_ERROR`` (400) for bad parameters — unknown format,
  invalid page, unknown query parameters, malformed/unknown id;
* ``AUTH_FORBIDDEN_PROJECT`` (403) for cross-project access;
* every code in the retrieval path exists in the closed Section 9.2
  catalog (a source-level sweep — no ad-hoc code can hide here).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.attachments.models import ProcessingStatus, TaskAttachment
from apps.core.errors import CANONICAL_ERROR_CODES

from .helpers import (
    MARKDOWN_BYTES,
    agent_client,
    envelope_code,
    make_attachment,
    make_project,
    make_task,
    owner_client,
    png_bytes,
    process_ready,
)

pytestmark = pytest.mark.django_db

CONTENT_URL = "/api/v1/attachments/{attachment_id}/content?{query}"
ALL_FORMATS = ["format=auto", "format=image_base64", "format=text_ocr", "format=markdown"]


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


# --- not-ready (Section 9.5: "409 ATTACHMENT_NOT_READY") ---------------------


@pytest.mark.parametrize("query", ALL_FORMATS)
@pytest.mark.parametrize("status", ["uploaded", "processing"])
def test_not_ready_statuses_answer_409_for_every_format(
    owner: APIClient, task: Any, query: str, status: str
) -> None:
    """Uploaded and processing are both "not ready" (FR-ATT-07 statuses)."""
    attachment = make_attachment(task, MARKDOWN_BYTES, name="pending.md")
    TaskAttachment.objects.filter(pk=attachment.pk).update(processing_status=status)

    response = owner.get(CONTENT_URL.format(attachment_id=attachment.pk, query=query))
    assert response.status_code == 409
    assert envelope_code(response) == "ATTACHMENT_NOT_READY"
    assert response.json()["error"]["retryable"] is False


@pytest.mark.parametrize("query", ALL_FORMATS)
def test_failed_status_answers_409_with_the_stored_reason(
    owner: APIClient, task: Any, query: str
) -> None:
    """The recorded reading: ``failed`` shares the 409 code, reason visible.

    The closed catalog has no attachment-failure code (20.4 item 5
    forbids inventing one); the human-readable reason rides the message
    so FR-ATT-07 visibility holds on the read path.
    """
    attachment = make_attachment(task, MARKDOWN_BYTES, name="broken.md")
    TaskAttachment.objects.filter(pk=attachment.pk).update(
        processing_status=ProcessingStatus.FAILED,
        failure_detail="stored content no longer matches any allowlisted type",
    )

    response = owner.get(CONTENT_URL.format(attachment_id=attachment.pk, query=query))
    assert response.status_code == 409
    assert envelope_code(response) == "ATTACHMENT_NOT_READY"
    assert "no longer matches" in response.json()["error"]["message"]


# --- unsupported combinations (the Section 9.5 table) -----------------------


def test_unsupported_format_matrix(owner: APIClient, task: Any) -> None:
    """Every 415 cell of the retrieval table, code and status asserted."""
    from pathlib import Path as _Path

    fixtures = _Path(__file__).resolve().parent / "fixtures" / "corpus"
    image = process_ready(task, png_bytes(), name="shot.png")
    document = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    docx = process_ready(task, (fixtures / "sample.docx").read_bytes(), name="plan.docx")

    cases = [
        (image.pk, "format=image_base64", False),  # image, allowed
        (image.pk, "format=markdown", True),  # image, unsupported
        (document.pk, "format=image_base64", True),  # non-image, unsupported
        (docx.pk, "format=text_ocr", True),  # never OCR'd, unsupported
    ]
    for attachment_id, query, expect_error in cases:
        response = owner.get(CONTENT_URL.format(attachment_id=attachment_id, query=query))
        if expect_error:
            assert response.status_code == 415, (query, response.content)
            assert envelope_code(response) == "ATTACHMENT_UNSUPPORTED_FORMAT", query
        else:
            assert response.status_code == 200, (query, response.content)


# --- validation and authorization --------------------------------------------


def test_bad_parameter_matrix_answers_validation_error(owner: APIClient, task: Any) -> None:
    """Unknown format, bad page, unknown parameter, malformed id — all 400."""
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    bad_queries = [
        "format=heic",
        "format=markdown&page=0",
        "format=markdown&page=lots",
        "format=markdown&offset=5",
        "format=markdown&PAGE=2",
    ]
    for query in bad_queries:
        response = owner.get(CONTENT_URL.format(attachment_id=attachment.pk, query=query))
        assert response.status_code == 400, (query, response.content)
        assert envelope_code(response) == "VALIDATION_ERROR", query

    malformed = owner.get(CONTENT_URL.format(attachment_id="not-a-uuid", query="format=auto"))
    assert malformed.status_code == 400
    unknown = owner.get(CONTENT_URL.format(attachment_id="0" * 32, query="format=auto"))
    assert unknown.status_code == 400
    assert envelope_code(unknown) == "VALIDATION_ERROR"


def test_cross_project_denial_and_anonymous_auth_required(owner: APIClient, task: Any) -> None:
    """Section 12.2 cells: foreign agent 403 AUTH_FORBIDDEN_PROJECT; anon 401."""
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    other = make_project(pid="PID00002")

    foreign = agent_client(owner, other.pk)
    denied = foreign.get(CONTENT_URL.format(attachment_id=attachment.pk, query="format=auto"))
    assert denied.status_code == 403
    assert envelope_code(denied) == "AUTH_FORBIDDEN_PROJECT"

    anonymous = APIClient()
    response = anonymous.get(CONTENT_URL.format(attachment_id=attachment.pk, query="format=auto"))
    assert response.status_code == 401
    assert envelope_code(response) == "AUTH_REQUIRED"

    owner_ok = owner.get(CONTENT_URL.format(attachment_id=attachment.pk, query="format=auto"))
    assert owner_ok.status_code == 200  # owner cell sanity: admitted


def test_envelope_shape_is_the_five_fields(owner: APIClient, task: Any) -> None:
    attachment = make_attachment(task, MARKDOWN_BYTES, name="pending.md")
    error = owner.get(CONTENT_URL.format(attachment_id=attachment.pk, query="format=auto")).json()[
        "error"
    ]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}


# --- catalog-only sweep (20.4 item 5) ----------------------------------------


def test_retrieval_path_uses_only_catalog_codes() -> None:
    """Source-level sweep: no ad-hoc *wire* error code hides in the path.

    Module-level constants (``FORMAT_AUTO`` & co.) are code identifiers,
    not wire codes — the AST collects them so the sweep flags only
    ALL-CAPS string literals that could reach a response envelope.
    """
    import ast

    from apps.attachments import exceptions as domain_exceptions
    from apps.attachments import retrieval, views_content

    assert domain_exceptions.AttachmentNotReady.default_code in CANONICAL_ERROR_CODES
    assert domain_exceptions.AttachmentUnsupportedFormat.default_code in CANONICAL_ERROR_CODES

    catalog = set(CANONICAL_ERROR_CODES)
    pattern = re.compile(r'"([A-Z][A-Z0-9_]{3,})"')
    for module in (retrieval, views_content):
        module_file = module.__file__
        assert module_file is not None  # importable module, always filed
        source = Path(module_file).read_text(encoding="utf-8")
        tree = ast.parse(source)
        constants = {
            target.id
            for node in ast.walk(tree)
            for target in (
                [node.target]
                if isinstance(node, ast.AnnAssign)
                else [t for t in node.targets if isinstance(t, ast.Name)]
                if isinstance(node, ast.Assign)
                else []
            )
            if isinstance(target, ast.Name)
        }
        for candidate in pattern.findall(source):
            if candidate in constants:
                continue  # an identifier, not a wire code
            assert candidate in catalog, f"{module.__name__}: {candidate} not in catalog"
