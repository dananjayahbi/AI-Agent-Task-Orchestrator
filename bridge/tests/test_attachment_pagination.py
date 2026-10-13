"""MT-2.5-05 — pagination mirrors WP-1.14's one-based page semantics.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.5-attachment-tool/
MT-2.5-05-pagination.md (Section 9.5; docs/plan/conventions/pagination.md).
"""

from __future__ import annotations

from typing import Any

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.endpoints import endpoint
from orchestrator_bridge.tools.attachment import read_task_attachment
from orchestrator_bridge.tools.errors import ToolFailure
from tests.conftest import FakeBackend, build_runtime

_TASK_ID = "PID00007-T004"
_ATTACHMENT_ID = "att-0003"
_CONTENT_PATH = endpoint("attachment_content").path.format(id=_ATTACHMENT_ID)

_PAGE_PAYLOAD: dict[str, Any] = {
    "attachment_id": _ATTACHMENT_ID,
    "format": "markdown",
    "content": "[UNTRUSTED CONTENT] Page body.",
    "description": None,
    "image_base64": None,
    "media_type": None,
    "page_number": 2,
    "total_pages": 5,
    "token_count": 800,
}


def _backend(payload: Any = None) -> FakeBackend:
    fake = FakeBackend()
    fake.route("GET", _CONTENT_PATH, 200, _PAGE_PAYLOAD if payload is None else payload)
    return fake


def test_page_number_is_forwarded_as_the_one_based_page_param() -> None:
    fake = _backend()
    runtime = build_runtime(fake)
    result = read_task_attachment(
        runtime,
        task_id=_TASK_ID,
        attachment_id=_ATTACHMENT_ID,
        format_preference="markdown",
        page_number=2,
        client=(None, None),
    )
    assert fake.calls_to("GET", _CONTENT_PATH)[0].query == "format=markdown&page=2"
    assert isinstance(result, dict)
    assert result["page_number"] == 2
    assert result["total_pages"] == 5
    assert result["token_count"] == 800  # documented as a backend estimate


def test_default_page_is_one() -> None:
    fake = _backend()
    runtime = build_runtime(fake)
    read_task_attachment(
        runtime,
        task_id=_TASK_ID,
        attachment_id=_ATTACHMENT_ID,
        format_preference="markdown",
        client=(None, None),
    )
    assert fake.calls_to("GET", _CONTENT_PATH)[0].query == "format=markdown&page=1"


def test_out_of_range_page_surfaces_page_number_guidance() -> None:
    fake = _backend()
    fake.route(
        "GET",
        _CONTENT_PATH,
        400,
        {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "page must be between 1 and 5",
                "retryable": False,
                "details": {"page": 9, "total_pages": 5},
                "correlation_id": "corr-page",
            }
        },
    )
    runtime = build_runtime(fake)
    with pytest.raises(ToolFailure) as excinfo:
        read_task_attachment(
            runtime,
            task_id=_TASK_ID,
            attachment_id=_ATTACHMENT_ID,
            format_preference="markdown",
            page_number=9,
            client=(None, None),
        )
    translated = excinfo.value.translated
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert "page_number 9" in translated.hint
    assert "total_pages" in translated.next_action
    assert translated.details == {"page": 9, "total_pages": 5}  # passthrough verbatim


def test_page_is_a_documented_no_op_on_the_ocr_path() -> None:
    payload = {
        "attachment_id": _ATTACHMENT_ID,
        "format": "text_ocr",
        "content": "[UNTRUSTED CONTENT] OCR text.",
        "description": None,
        "image_base64": None,
        "media_type": "image/png",
        "page_number": None,
        "total_pages": None,
        "token_count": None,
    }
    fake = _backend(payload)
    runtime = build_runtime(fake)
    result = read_task_attachment(
        runtime,
        task_id=_TASK_ID,
        attachment_id=_ATTACHMENT_ID,
        format_preference="text_ocr",
        page_number=3,
        client=(None, None),
    )
    # Accepted (schema) but never forwarded — the non-paginated path ignores it.
    assert fake.calls_to("GET", _CONTENT_PATH)[0].query == "format=text_ocr"
    assert isinstance(result, dict)
    assert "page_number" not in result


def test_page_triple_is_dropped_when_the_backend_omits_it() -> None:
    payload = {k: v for k, v in _PAGE_PAYLOAD.items() if k not in ("page_number", "total_pages")}
    payload["page_number"] = None
    payload["total_pages"] = None
    fake = _backend(payload)
    runtime = build_runtime(fake)
    result = read_task_attachment(
        runtime,
        task_id=_TASK_ID,
        attachment_id=_ATTACHMENT_ID,
        format_preference="markdown",
        client=(None, None),
    )
    assert isinstance(result, dict)
    assert "page_number" not in result and "total_pages" not in result
    assert result["token_count"] == 800
