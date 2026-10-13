"""MT-2.5-06 — cross-path capability matrix (Sections 9.5, 10.4, 10.9).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.5-attachment-tool/
MT-2.5-06-capability-tests.md: every format × capability × resolver-step
combination green in the targeted bridge suite, with the banner present on
every delivered text shape and pagination asserted (ADR-006 honesty).
"""

from __future__ import annotations

import pytest
from mcp.types import ImageContent

from orchestrator_bridge.capabilities import (
    IMAGE_REQUEST_NOTE,
    ResolutionStep,
    resolve_capability,
)
from orchestrator_bridge.capability_table import load_capability_table
from orchestrator_bridge.endpoints import endpoint
from orchestrator_bridge.tools.attachment import read_task_attachment
from tests.conftest import FakeBackend, build_runtime

_TASK_ID = "PID00007-T004"
_ATTACHMENT_ID = "att-matrix"
_DESCRIPTOR_PATH = endpoint("attachment_get").path.format(id=_ATTACHMENT_ID)
_CONTENT_PATH = endpoint("attachment_content").path.format(id=_ATTACHMENT_ID)

_BANNER = "[UNTRUSTED CONTENT]"


def _backend(*, is_image: bool, content_format: str | None = None) -> FakeBackend:
    echoed = content_format or ("image_base64" if is_image else "markdown")
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
    fake.route(
        "GET",
        _CONTENT_PATH,
        200,
        {
            "attachment_id": _ATTACHMENT_ID,
            "format": echoed,
            "content": f"{_BANNER} extracted body.",
            "description": f"{_BANNER} a described image.",
            "image_base64": "aW1n" if is_image else None,
            "media_type": "image/png" if is_image else None,
            "page_number": 1 if not is_image else None,
            "total_pages": 2 if not is_image else None,
            "token_count": 100 if not is_image else None,
        },
    )
    return fake


@pytest.mark.parametrize(
    ("capability", "expected_format", "expected_step"),
    [
        ("vision", "image_base64", ResolutionStep.SESSION_CONFIG),
        ("text_only", "text_ocr", ResolutionStep.SESSION_CONFIG),
        (None, "text_ocr", ResolutionStep.DEFAULT_TEXT_SAFE),
    ],
)
def test_auto_image_matrix(
    capability: str | None, expected_format: str, expected_step: ResolutionStep
) -> None:
    fake = _backend(is_image=True, content_format=expected_format)
    runtime = build_runtime(fake, session_capability=capability)
    result = read_task_attachment(
        runtime, task_id=_TASK_ID, attachment_id=_ATTACHMENT_ID, client=(None, None)
    )
    query = fake.calls_to("GET", _CONTENT_PATH)[0].query
    assert query == f"format={expected_format}"
    if expected_format == "image_base64":
        assert isinstance(result, list) and isinstance(result[0], ImageContent)
    else:
        assert isinstance(result, dict)
        assert result["format"] == expected_format
        assert result["resolution"]["step"] == expected_step.value
        # Every delivered text shape carries the banner (WP-5 exit criteria).
        assert result["content"].startswith(_BANNER)
        assert result["description"].startswith(_BANNER)


def test_auto_document_matrix_is_markdown_with_pagination() -> None:
    fake = _backend(is_image=False)
    runtime = build_runtime(fake, session_capability="vision")  # vision is irrelevant here
    result = read_task_attachment(
        runtime, task_id=_TASK_ID, attachment_id=_ATTACHMENT_ID, client=(None, None)
    )
    assert isinstance(result, dict)
    assert result["format"] == "markdown"
    assert fake.calls_to("GET", _CONTENT_PATH)[0].query == "format=markdown&page=1"
    assert result["content"].startswith(_BANNER)
    assert result["page_number"] == 1 and result["total_pages"] == 2


@pytest.mark.parametrize("explicit", ["text_ocr", "markdown"])
def test_explicit_formats_win_over_every_capability(explicit: str) -> None:
    for capability in ("vision", "text_only", None):
        fake = _backend(is_image=True)
        runtime = build_runtime(fake, session_capability=capability)
        result = read_task_attachment(
            runtime,
            task_id=_TASK_ID,
            attachment_id=_ATTACHMENT_ID,
            format_preference=explicit,
            client=(None, None),
        )
        assert isinstance(result, dict)
        expected_query = (
            f"format={explicit}&page=1" if explicit == "markdown" else f"format={explicit}"
        )
        assert fake.calls_to("GET", _CONTENT_PATH)[0].query == expected_query
        assert result["resolution"]["step"] == "explicit_format"
        assert result["resolution"]["capability"] == (capability or "unknown")
        assert result["content"].startswith(_BANNER)


def test_shipped_table_entries_resolve_to_the_text_safe_default() -> None:
    """The seeded table records every Section 10.9 client as unknown."""
    table = load_capability_table()
    for client in ("claude-code", "vscode-copilot-ide", "opencode", "aider"):
        resolution = resolve_capability(client_name=client, table=table)
        assert resolution.capability == "unknown"
        assert resolution.note == IMAGE_REQUEST_NOTE


def test_resolver_step_matrix_is_complete_across_all_four_steps() -> None:
    table = load_capability_table()
    steps = {
        resolve_capability("image_base64").step,
        resolve_capability(session_capability="vision").step,
        resolve_capability(client_name="claude-code", table=table).step,
        resolve_capability().step,
    }
    assert steps == set(ResolutionStep)
