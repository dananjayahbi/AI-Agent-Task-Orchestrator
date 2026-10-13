"""MT-2.5-03 — image content blocks and the text-only gate (Section 9.5/10.4).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.5-attachment-tool/
MT-2.5-03-image-content-blocks.md (Sections 9.5, 10.4; ADR-006; P10).
"""

from __future__ import annotations

from typing import Any

import pytest
from mcp.types import ImageContent, TextContent

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.endpoints import endpoint
from orchestrator_bridge.tools.attachment import read_task_attachment
from orchestrator_bridge.tools.errors import ToolFailure
from tests.conftest import FakeBackend, build_runtime

_TASK_ID = "PID00007-T004"
_ATTACHMENT_ID = "att-0001"
_DESCRIPTOR_PATH = endpoint("attachment_get").path.format(id=_ATTACHMENT_ID)
_CONTENT_PATH = endpoint("attachment_content").path.format(id=_ATTACHMENT_ID)

_IMAGE_PAYLOAD: dict[str, Any] = {
    "attachment_id": _ATTACHMENT_ID,
    "format": "image_base64",
    "content": None,
    "description": None,
    "image_base64": "aGVsbG8taW1hZ2U=",
    "media_type": "image/png",
    "page_number": None,
    "total_pages": None,
    "token_count": None,
}


def _image_backend(
    *, descriptor_status: str = "ready", content_format: str = "image_base64"
) -> FakeBackend:
    fake = FakeBackend()
    fake.route(
        "GET",
        _DESCRIPTOR_PATH,
        200,
        {
            "id": _ATTACHMENT_ID,
            "task_id": _TASK_ID,
            "is_image": True,
            "processing_status": descriptor_status,
        },
    )
    fake.route("GET", _CONTENT_PATH, 200, {**_IMAGE_PAYLOAD, "format": content_format})
    return fake


def test_vision_auto_delivers_an_mcp_image_block_and_provenance() -> None:
    fake = _image_backend()
    runtime = build_runtime(fake, session_capability="vision")
    result = read_task_attachment(
        runtime, task_id=_TASK_ID, attachment_id=_ATTACHMENT_ID, client=(None, None)
    )
    assert isinstance(result, list)
    image, meta = result
    assert isinstance(image, ImageContent)
    assert image.data == "aGVsbG8taW1hZ2U="
    assert image.mime_type == "image/png"
    assert isinstance(meta, TextContent)
    assert '"capability": "vision"' in meta.text
    assert '"step": "session_config"' in meta.text
    # Vision sessions must ask for the image explicitly (backend auto is
    # text-safe — WP-1.14 forward note), so the wire carried format=image_base64.
    assert fake.calls_to("GET", _CONTENT_PATH)[0].query == "format=image_base64"


def test_unknown_capability_auto_never_requests_the_image() -> None:
    fake = _image_backend(content_format="text_ocr")
    runtime = build_runtime(fake)  # no session capability, no table identity
    result = read_task_attachment(
        runtime, task_id=_TASK_ID, attachment_id=_ATTACHMENT_ID, client=(None, None)
    )
    assert isinstance(result, dict)
    assert result["format"] == "text_ocr"
    assert fake.calls_to("GET", _CONTENT_PATH)[0].query == "format=text_ocr"
    assert fake.calls_to("GET", _CONTENT_PATH)[0].path == _CONTENT_PATH


def test_text_only_session_explicit_image_is_rejected_with_guidance() -> None:
    fake = _image_backend()
    runtime = build_runtime(fake, session_capability="text_only")
    with pytest.raises(ToolFailure) as excinfo:
        read_task_attachment(
            runtime,
            task_id=_TASK_ID,
            attachment_id=_ATTACHMENT_ID,
            format_preference="image_base64",
            client=(None, None),
        )
    translated = excinfo.value.translated
    assert translated.code is ErrorCode.ATTACHMENT_UNSUPPORTED_FORMAT
    assert "text-only" in translated.message
    assert "auto" in translated.next_action and "text_ocr" in translated.next_action
    assert translated.details is not None
    assert translated.details["capability"] == "text_only"
    # Rejected before any content call — the wire was never hit for the image.
    assert fake.calls_to("GET", _CONTENT_PATH) == []


def test_forced_image_request_is_honored_for_a_text_only_session() -> None:
    fake = _image_backend()
    runtime = build_runtime(fake, session_capability="text_only")
    result = read_task_attachment(
        runtime,
        task_id=_TASK_ID,
        attachment_id=_ATTACHMENT_ID,
        format_preference="image_base64",
        force=True,
        client=(None, None),
    )
    assert isinstance(result, list)
    assert isinstance(result[0], ImageContent)
    assert fake.calls_to("GET", _CONTENT_PATH)[0].query == "format=image_base64"


def test_non_image_under_image_base64_surfaces_the_backend_415() -> None:
    fake = _image_backend()
    fake.route(
        "GET",
        _CONTENT_PATH,
        415,
        {
            "error": {
                "code": "ATTACHMENT_UNSUPPORTED_FORMAT",
                "message": "Attachment att-0001 is not an image.",
                "retryable": False,
                "details": None,
                "correlation_id": "corr-1",
            }
        },
    )
    runtime = build_runtime(fake, session_capability="vision")
    with pytest.raises(ToolFailure) as excinfo:
        read_task_attachment(
            runtime,
            task_id=_TASK_ID,
            attachment_id=_ATTACHMENT_ID,
            format_preference="image_base64",
            client=(None, None),
        )
    assert excinfo.value.translated.code is ErrorCode.ATTACHMENT_UNSUPPORTED_FORMAT
    assert excinfo.value.translated.message == "Attachment att-0001 is not an image."


def test_not_ready_descriptor_short_circuits_with_the_status() -> None:
    fake = _image_backend(descriptor_status="processing")
    runtime = build_runtime(fake, session_capability="vision")
    with pytest.raises(ToolFailure) as excinfo:
        read_task_attachment(
            runtime, task_id=_TASK_ID, attachment_id=_ATTACHMENT_ID, client=(None, None)
        )
    translated = excinfo.value.translated
    assert translated.code is ErrorCode.ATTACHMENT_NOT_READY
    assert translated.details is not None
    assert translated.details["processing_status"] == "processing"
    assert fake.calls_to("GET", _CONTENT_PATH) == []


def test_not_ready_envelope_from_the_content_endpoint_passes_through() -> None:
    fake = FakeBackend()
    fake.route(
        "GET",
        _CONTENT_PATH,
        409,
        {
            "error": {
                "code": "ATTACHMENT_NOT_READY",
                "message": "Attachment att-0001 is still being processed.",
                "retryable": False,
                "details": {"processing_status": "processing"},
                "correlation_id": "corr-1",
            }
        },
    )
    runtime = build_runtime(fake)
    with pytest.raises(ToolFailure) as excinfo:
        read_task_attachment(
            runtime,
            task_id=_TASK_ID,
            attachment_id=_ATTACHMENT_ID,
            format_preference="text_ocr",
            client=(None, None),
        )
    assert excinfo.value.translated.code is ErrorCode.ATTACHMENT_NOT_READY
    assert excinfo.value.translated.correlation_id == "corr-1"


def test_image_result_rejects_a_payload_without_image_data() -> None:
    fake = _image_backend()
    fake.routes[("GET", _CONTENT_PATH)] = (
        200,
        {**_IMAGE_PAYLOAD, "image_base64": None},
    )
    runtime = build_runtime(fake, session_capability="vision")
    with pytest.raises(ToolFailure) as excinfo:
        read_task_attachment(
            runtime, task_id=_TASK_ID, attachment_id=_ATTACHMENT_ID, client=(None, None)
        )
    assert excinfo.value.translated.code is ErrorCode.SERVER_ERROR
