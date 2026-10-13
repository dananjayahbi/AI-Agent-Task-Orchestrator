"""``read_task_attachment`` (Sections 9.5, 10.4, 10.9; MT-2.5-01…06).

The capability-negotiated attachment reader. Flow per read:

1. **resolve** — :func:`~orchestrator_bridge.capabilities.resolve_capability`
   applies Section 10.4's order (explicit format → session capability →
   client table → text-safe default) and its provenance rides every result.
2. **decide the REST format** — an explicit ``format_preference`` goes to
   the wire as asked (the caller overriding the capability default is the
   Section 9.5 "forced" path, gated by ``force`` for text-only sessions);
   ``auto`` reads the attachment descriptor once and picks:
   image + vision session → ``image_base64``; image otherwise →
   ``text_ocr`` (text-safe); document → ``markdown`` with the page param.
3. **fetch** — GET ``/attachments/{id}/content`` with ``format`` and, for
   paginated ``markdown``, one-based ``page`` (WP-1.14 semantics mirrored
   from WP-1.14; page out of range surfaces ``VALIDATION_ERROR`` with
   page_number guidance). Errors pass through the translator verbatim
   (``ATTACHMENT_NOT_READY``/``ATTACHMENT_UNSUPPORTED_FORMAT`` keep the
   backend's code, message and details).
4. **package** — images become MCP content blocks (vision only); text
   arrives with the untrusted banner exactly once (the backend annotates at
   delivery; the bridge guard is idempotent — P10, wp-1.13 note).

Never claims vision it was not told (ADR-006): without a session value or
a verified table entry, everything is text-safe OCR plus a description and
the explicit-request note.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

from mcp.server.mcpserver.context import Context

from ..api_errors import ApiError, ErrorCode, ErrorKind
from ..capabilities import (
    FORMAT_AUTO,
    FORMAT_IMAGE_BASE64,
    FORMAT_MARKDOWN,
    FORMAT_TEXT_OCR,
    CapabilityResolution,
    client_identity,
    resolve_capability,
)
from ..capability_table import load_capability_table
from ..endpoints import endpoint
from ..error_translation import TranslatedError, translate_error
from .attachment_packaging import content_payload, image_result, text_result
from .errors import ToolFailure
from .runtime import ToolRuntime

__all__ = ["make_handler", "read_task_attachment"]


def _failure(error: ApiError) -> ToolFailure:
    """Translate a backend error into the structured tool failure."""
    return ToolFailure(translate_error(error))


def _descriptor(runtime: ToolRuntime, attachment_id: str) -> dict[str, Any]:
    """GET the attachment descriptor (is_image + processing_status)."""
    try:
        payload = runtime.client.request(
            "GET", endpoint("attachment_get").path.format(id=attachment_id)
        )
    except ApiError as exc:
        raise _failure(exc) from None
    if not isinstance(payload, dict):
        raise _failure(
            ApiError(
                code=ErrorCode.SERVER_ERROR,
                message="attachment descriptor is not the documented object",
                retryable=False,
                kind=ErrorKind.MALFORMED_RESPONSE,
                details={"endpoint": "attachment_get"},
            )
        )
    return payload


def _ensure_ready(descriptor: dict[str, Any], attachment_id: str) -> None:
    """Short-circuit a not-ready attachment (Section 9.5 passthrough)."""
    status = descriptor.get("processing_status")
    if status == "ready":
        return
    details: dict[str, Any] = {
        "attachment_id": attachment_id,
        "processing_status": status,
    }
    failure_reason = descriptor.get("failure_reason")
    if isinstance(failure_reason, str) and failure_reason:
        details["failure_reason"] = failure_reason
    raise ToolFailure(
        translate_error(
            ApiError(
                code=ErrorCode.ATTACHMENT_NOT_READY,
                message=f"attachment {attachment_id} is not ready (status: {status})",
                retryable=False,
                kind=ErrorKind.ENVELOPE,
                details=details,
            )
        )
    )


def _choose_format(
    runtime: ToolRuntime,
    *,
    attachment_id: str,
    resolution: CapabilityResolution,
    force: bool,
) -> str:
    """Pick the concrete REST format for this read (Section 10.4/9.5)."""
    requested = resolution.format_preference
    if requested != FORMAT_AUTO:
        # Section 9.5: a text-only session gets no image unless forced.
        if requested == FORMAT_IMAGE_BASE64 and resolution.text_only and not force:
            _reject_text_only_image(attachment_id, resolution)
        return requested
    descriptor = _descriptor(runtime, attachment_id)
    _ensure_ready(descriptor, attachment_id)
    if descriptor.get("is_image") is True:
        # Backend ``auto`` is text-safe (images → text_ocr; WP-1.14), so a
        # vision session must ask for the image explicitly (WP-1.14 note).
        return FORMAT_IMAGE_BASE64 if resolution.vision else FORMAT_TEXT_OCR
    return FORMAT_MARKDOWN


def _reject_text_only_image(attachment_id: str, resolution: CapabilityResolution) -> None:
    """Raise the structured text-only rejection (guidance: auto/text_ocr)."""
    raise ToolFailure(
        TranslatedError(
            code=ErrorCode.ATTACHMENT_UNSUPPORTED_FORMAT,
            message=(
                f"attachment {attachment_id} was requested as image_base64, but this "
                "session is text-only"
            ),
            hint=(
                "The session capability is text_only (startup config or capability "
                "table), so images are delivered as OCR text and a description."
            ),
            next_action=(
                'Call read_task_attachment with format_preference="auto" or "text_ocr" '
                "— or pass force=true if you know the client renders image blocks."
            ),
            retryable=False,
            details={
                "attachment_id": attachment_id,
                "capability": resolution.capability,
                "step": str(resolution.step.value),
            },
            correlation_id=None,
        )
    )


def _fetch_content(
    runtime: ToolRuntime,
    *,
    attachment_id: str,
    rest_format: str,
    page_number: int,
) -> dict[str, Any]:
    """GET the attachment content; surface the page triple (WP-1.14)."""
    query: dict[str, str] = {"format": rest_format}
    if rest_format == FORMAT_MARKDOWN:
        query["page"] = str(page_number)
    path = f"{endpoint('attachment_content').path.format(id=attachment_id)}?{urlencode(query)}"
    try:
        payload = runtime.client.request("GET", path)
    except ApiError as exc:
        raise _with_page_guidance(exc, page_number=page_number, rest_format=rest_format) from None
    if not isinstance(payload, dict):
        raise _failure(
            ApiError(
                code=ErrorCode.SERVER_ERROR,
                message="attachment content response is not the documented object",
                retryable=False,
                kind=ErrorKind.MALFORMED_RESPONSE,
                details={"endpoint": "attachment_content"},
            )
        )
    return dict(content_payload(payload))


def _with_page_guidance(error: ApiError, *, page_number: int, rest_format: str) -> ToolFailure:
    """Pagination-specific recovery guidance on a VALIDATION_ERROR (MT-2.5-05)."""
    translated = translate_error(error)
    if (
        error.code != ErrorCode.VALIDATION_ERROR
        or rest_format != FORMAT_MARKDOWN
        or page_number <= 1
    ):
        return ToolFailure(translated)
    return ToolFailure(
        TranslatedError(
            code=translated.code,
            message=translated.message,
            hint=(
                f"page_number {page_number} is outside the pages this paginated attachment "
                "offers (one-based)."
            ),
            next_action=(
                "Retry with page_number in 1..total_pages; a successful read reports "
                "total_pages, and page_number 1 returns the first page."
            ),
            retryable=translated.retryable,
            details=translated.details,
            correlation_id=translated.correlation_id,
        )
    )


def read_task_attachment(
    runtime: ToolRuntime,
    *,
    task_id: str,
    attachment_id: str,
    format_preference: str = FORMAT_AUTO,
    page_number: int = 1,
    force: bool = False,
    client: tuple[str | None, str | None] = (None, None),
) -> dict[str, Any] | list[Any]:
    """One attachment read: resolve capability, fetch, package (Section 10.4).

    ``client`` is the handshake ``(name, version)`` the handler read off the
    MCP context (step 3's lookup identity); ``force`` is the Section 9.5
    override letting a known text-only session still request
    ``image_base64`` explicitly. ``page_number`` is accepted on every
    format (a documented no-op for the non-paginated image/OCR paths) and
    forwarded as the one-based ``page`` param for ``markdown``.
    """
    client_name, client_version = client
    resolution = resolve_capability(
        format_preference,
        session_capability=runtime.session_capability,
        client_name=client_name,
        client_version=client_version,
        table=load_capability_table(),
    )
    rest_format = _choose_format(
        runtime, attachment_id=attachment_id, resolution=resolution, force=force
    )
    payload = _fetch_content(
        runtime, attachment_id=attachment_id, rest_format=rest_format, page_number=page_number
    )
    if rest_format == FORMAT_IMAGE_BASE64:
        return image_result(payload, resolution=resolution, task_id=task_id)
    return text_result(payload, resolution=resolution, task_id=task_id)


def make_handler(runtime: ToolRuntime) -> Callable[..., Any]:
    """The registered MCP handler: schema-typed arguments, bound session.

    The SDK injects the request ``Context`` (``context_kwarg`` detection
    covers ``Context | None``); from it the handler reads the client's
    handshake identity for capability-table step 3. Every optional layer is
    None-safe, so unit tests call the inner function without a context.
    """

    def read_task_attachment_tool(
        task_id: str,
        attachment_id: str,
        format_preference: str = FORMAT_AUTO,
        page_number: int = 1,
        force: bool = False,
        context: Context | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Read one attachment with capability negotiation (Section 10.4)."""
        return read_task_attachment(
            runtime,
            task_id=task_id,
            attachment_id=attachment_id,
            format_preference=format_preference,
            page_number=page_number,
            force=force,
            client=client_identity(context),
        )

    return read_task_attachment_tool
