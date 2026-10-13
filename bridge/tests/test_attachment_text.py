"""MT-2.5-04 — text/OCR packaging with the untrusted banner (Section 9.5; P10).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.5-attachment-tool/
MT-2.5-04-text-ocr-packaging.md (Sections 9.5, 10.4; WP-5 exit criteria;
the wp-1.13 banner note: server-annotated REST text is never double-bannered).
"""

from __future__ import annotations

from typing import Any

from orchestrator_bridge.endpoints import endpoint
from orchestrator_bridge.tools.attachment import read_task_attachment
from orchestrator_bridge.tools.attachment_packaging import (
    UNTRUSTED_BANNER,
    ensure_untrusted_banner,
)
from tests.conftest import FakeBackend, build_runtime

_TASK_ID = "PID00007-T004"
_ATTACHMENT_ID = "att-0002"
_DESCRIPTOR_PATH = endpoint("attachment_get").path.format(id=_ATTACHMENT_ID)
_CONTENT_PATH = endpoint("attachment_content").path.format(id=_ATTACHMENT_ID)

_BANNERED_OCR = f"{UNTRUSTED_BANNER}\nExtracted transcript line."
_BANNERED_PAGE = f"{UNTRUSTED_BANNER}\n# Spec\nPage body text."


def _backend(payload: dict[str, Any], *, is_image: bool = False) -> FakeBackend:
    fake = FakeBackend()
    fake.route(
        "GET",
        _DESCRIPTOR_PATH,
        200,
        {
            "id": _ATTACHMENT_ID,
            "task_id": _TASK_ID,
            "is_image": is_image,
            "processing_status": "ready",
        },
    )
    fake.route("GET", _CONTENT_PATH, 200, payload)
    return fake


def test_text_ocr_surfaces_content_and_description_bannered_once() -> None:
    payload = {
        "attachment_id": _ATTACHMENT_ID,
        "format": "text_ocr",
        "content": _BANNERED_OCR,
        "description": f"{UNTRUSTED_BANNER}\nScreenshot of a table.",
        "image_base64": None,
        "media_type": "image/png",
        "page_number": None,
        "total_pages": None,
        "token_count": None,
    }
    runtime = build_runtime(_backend(payload))
    result = read_task_attachment(
        runtime,
        task_id=_TASK_ID,
        attachment_id=_ATTACHMENT_ID,
        format_preference="text_ocr",
        client=(None, None),
    )
    assert isinstance(result, dict)
    # Server-annotated text passes through unchanged — exactly one banner.
    assert result["content"] == _BANNERED_OCR
    assert result["content"].count("[UNTRUSTED CONTENT]") == 1
    assert result["description"].count("[UNTRUSTED CONTENT]") == 1
    assert result["resolution"]["capability"] == "unknown"
    assert result["resolution"]["step"] == "explicit_format"


def test_unbannered_text_is_marked_exactly_once_by_the_bridge() -> None:
    text = ensure_untrusted_banner("bare extracted text")
    assert text.startswith(UNTRUSTED_BANNER)
    assert text.count("[UNTRUSTED CONTENT]") == 1
    # Idempotent on the default and on a reworded banner that keeps the marker.
    assert ensure_untrusted_banner(text) == text
    assert ensure_untrusted_banner("[UNTRUSTED CONTENT] reworded server banner\nbody") == (
        "[UNTRUSTED CONTENT] reworded server banner\nbody"
    )
    assert ensure_untrusted_banner("") == ""


def test_markdown_auto_document_path_is_bannered_and_notes_the_default_step() -> None:
    payload = {
        "attachment_id": _ATTACHMENT_ID,
        "format": "markdown",
        "content": _BANNERED_PAGE,
        "description": None,
        "image_base64": None,
        "media_type": None,
        "page_number": 1,
        "total_pages": 3,
        "token_count": 900,
    }
    runtime = build_runtime(_backend(payload))
    result = read_task_attachment(
        runtime, task_id=_TASK_ID, attachment_id=_ATTACHMENT_ID, client=(None, None)
    )
    assert isinstance(result, dict)
    assert result["content"].count("[UNTRUSTED CONTENT]") == 1
    # The step-4 explicit-request note travels with the response.
    assert result["resolution"]["note"] is not None
    assert "image_base64" in result["resolution"]["note"]
    assert result["resolution"]["step"] == "default_text_safe"


def test_ocr_only_degradation_is_a_usable_empty_state() -> None:
    payload = {
        "attachment_id": _ATTACHMENT_ID,
        "format": "text_ocr",
        "content": None,
        "description": None,
        "image_base64": None,
        "media_type": "image/png",
        "page_number": None,
        "total_pages": None,
        "token_count": None,
    }
    runtime = build_runtime(_backend(payload, is_image=True))
    result = read_task_attachment(
        runtime, task_id=_TASK_ID, attachment_id=_ATTACHMENT_ID, client=(None, None)
    )
    assert isinstance(result, dict)
    assert result["attachment_id"] == _ATTACHMENT_ID
    assert result["format"] == "text_ocr"
    assert "content" not in result and "description" not in result
    assert result["resolution"]["capability"] == "unknown"


def test_description_alone_still_delivers() -> None:
    payload = {
        "attachment_id": _ATTACHMENT_ID,
        "format": "text_ocr",
        "content": "   ",
        "description": f"{UNTRUSTED_BANNER}\nA diagram of the pipeline.",
        "image_base64": None,
        "media_type": "image/png",
        "page_number": None,
        "total_pages": None,
        "token_count": None,
    }
    runtime = build_runtime(_backend(payload, is_image=True))
    result = read_task_attachment(
        runtime, task_id=_TASK_ID, attachment_id=_ATTACHMENT_ID, client=(None, None)
    )
    assert isinstance(result, dict)
    assert "content" not in result  # blank content drops out; description carries
    assert "pipeline" in result["description"]
