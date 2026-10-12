"""Tests for structured JSON logging, correlation propagation and scrubbing
(MT-1.1-02; parent plan Sections 17, 12.4, 9.2; MT-0.5-03 header conventions).

No infrastructure needed: request tests run through the Django test client
against the middleware chain, and the error-envelope tests call the exception
handler directly, so the suite is green without Postgres or Redis.
"""

from __future__ import annotations

import io
import json
import logging
import re
from collections.abc import Generator

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import Client, RequestFactory
from rest_framework.exceptions import ValidationError

from apps.core.correlation import reset_correlation_id, set_correlation_id
from apps.core.errors import SERVER_ERROR, VALIDATION_ERROR
from apps.core.exceptions import orchestrator_exception_handler
from apps.core.logging import JsonFormatter
from apps.core.middleware import CorrelationIdMiddleware, RequestLoggingMiddleware
from apps.core.scrub import MAX_SCRUBBED_CHARS

_GENERATED_ID_SHAPE = re.compile(r"\A[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}\Z")


@pytest.fixture
def json_log_stream() -> Generator[io.StringIO, None, None]:
    """Capture root-logger output through the production JsonFormatter."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    previous_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    try:
        yield stream
    finally:
        root.removeHandler(handler)
        root.setLevel(previous_level)


def _payloads(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line]


def _request_completed(stream: io.StringIO) -> dict[str, object]:
    matches = [item for item in _payloads(stream) if item.get("message") == "request completed"]
    assert matches, f"no request log line captured:\n{stream.getvalue()}"
    return matches[0]


def test_request_emits_one_json_line_with_correlation_id(json_log_stream: io.StringIO) -> None:
    """A request produces a JSON line carrying the id of its scope (Section 17)."""
    response = Client().get("/")

    # No routes exist in WP-1.1 — the request still completes (Django's
    # DEBUG page for an empty urlconf) and flows through both middlewares.
    record = _request_completed(json_log_stream)
    assert record["level"] == "INFO"
    assert record["method"] == "GET"
    assert record["path"] == "/"
    assert record["status"] == response.status_code
    assert isinstance(record["correlation_id"], str) and record["correlation_id"]
    assert response["X-Correlation-ID"] == record["correlation_id"]
    # The line is valid single-line JSON (already proven by parsing; assert
    # no raw newline leaked into the stream entry).
    assert "\n" not in json.dumps(record)


def test_incoming_correlation_header_is_honored(json_log_stream: io.StringIO) -> None:
    """headers.md: a present, well-formed header wins over generation."""
    response = Client().get("/", HTTP_X_CORRELATION_ID="client-supplied-id-001")

    assert response["X-Correlation-ID"] == "client-supplied-id-001"
    record = _request_completed(json_log_stream)
    assert record["correlation_id"] == "client-supplied-id-001"


def test_malformed_correlation_header_is_replaced(json_log_stream: io.StringIO) -> None:
    """An unusable incoming value is replaced (never echoed or logged verbatim)."""
    response = Client().get("/", HTTP_X_CORRELATION_ID="not a valid id!")

    echoed = response["X-Correlation-ID"]
    assert echoed != "not a valid id!"
    assert _GENERATED_ID_SHAPE.match(echoed) is not None
    record = _request_completed(json_log_stream)
    assert record["correlation_id"] == echoed


def test_generated_correlation_id_is_stable_across_the_request(
    json_log_stream: io.StringIO,
) -> None:
    """With no header, one generated id covers every line of the request scope."""
    probes = logging.getLogger("tests.probe")

    def view(request: HttpRequest) -> HttpResponse:
        probes.info("first probe line")
        probes.info("second probe line")
        return HttpResponse("ok")

    request = RequestFactory().get("/")
    handler = CorrelationIdMiddleware(RequestLoggingMiddleware(view))
    response = handler(request)

    lines = _payloads(json_log_stream)
    assert len(lines) >= 3  # two probe lines + the request-completed line
    ids = {item.get("correlation_id") for item in lines}
    assert len(ids) == 1, f"ids drifted within one request: {ids}"
    generated = ids.pop()
    assert isinstance(generated, str)
    assert _GENERATED_ID_SHAPE.match(generated) is not None
    assert response["X-Correlation-ID"] == generated


def test_tokens_and_secrets_are_scrubbed_from_log_output(json_log_stream: io.StringIO) -> None:
    """Sections 17/12.4: credential-shaped values never reach log output."""
    logging.getLogger("tests.scrub").warning(
        "auth failed password=%s token=%s Authorization: Bearer %s",
        "hunter2",  # pragma: allowlist secret
        "eyJ.payload.signature",  # pragma: allowlist secret
        "abc123.def456",  # pragma: allowlist secret
        extra={"api_key": "sk-live-98765"},  # pragma: allowlist secret
    )

    output = json_log_stream.getvalue()
    for leaked in ("hunter2", "eyJ.payload.signature", "abc123.def456", "sk-live-98765"):
        assert leaked not in output, f"secret leaked into logs: {leaked}"

    records = [item for item in _payloads(json_log_stream) if "auth failed" in str(item["message"])]
    assert records
    message = str(records[0]["message"])
    assert message.count("[REDACTED]") >= 3
    assert records[0]["api_key"] == "[REDACTED]"


def test_attachment_text_is_truncated(json_log_stream: io.StringIO) -> None:
    """Section 12.4: attachment-derived text is capped in log output."""
    logging.getLogger("tests.truncate").info(
        "attachment excerpt: %s",
        "A" * (MAX_SCRUBBED_CHARS * 2),
    )

    records = [
        item for item in _payloads(json_log_stream) if "attachment excerpt" in str(item["message"])
    ]
    assert records
    message = str(records[0]["message"])
    assert message.endswith("…[truncated]")
    assert len(message) <= MAX_SCRUBBED_CHARS + len("…[truncated]")


def test_error_envelope_carries_correlation_id_and_scrubs_details() -> None:
    """The envelope's correlation_id is the request's; details cannot leak (9.2)."""
    token = set_correlation_id("c0a8-4f2e-91d7")
    try:
        response = orchestrator_exception_handler(
            ValidationError({"password": ["hunter2-token-value"]}),  # pragma: allowlist secret
            {},
        )
    finally:
        reset_correlation_id(token)

    assert response is not None
    assert response.status_code == 400
    envelope = json.loads(json.dumps(response.data))
    error = envelope["error"]
    assert error["code"] == VALIDATION_ERROR
    assert error["retryable"] is False
    assert error["correlation_id"] == "c0a8-4f2e-91d7"
    assert set(error) == {"code", "message", "retryable", "details", "correlation_id"}
    assert "hunter2-token-value" not in json.dumps(envelope)  # pragma: allowlist secret
    assert error["details"]["password"] == "[REDACTED]"


def test_unhandled_exception_becomes_a_safe_server_error_envelope() -> None:
    """Non-DRF exceptions still answer with the envelope, never the raw error."""
    response = orchestrator_exception_handler(ValueError("internal detail worth hiding"), {})

    assert response is not None
    assert response.status_code == 500
    envelope = json.loads(json.dumps(response.data))
    error = envelope["error"]
    assert error["code"] == SERVER_ERROR
    assert error["retryable"] is True
    assert "internal detail worth hiding" not in json.dumps(envelope)
    assert set(error) == {"code", "message", "retryable", "details", "correlation_id"}
