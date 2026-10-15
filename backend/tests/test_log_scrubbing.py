"""MT-6.1-04 — log scrubbing audit: no tokens/secrets, truncated attachment text.

Sections 12.4/17 ("logs scrub tokens and truncate attachment text"), FR-SEC-04
and RISK-14 made executable: the sensitive fixture flows (login, token
issuance, device registration, agent request, attachment upload, the
exception path) are driven through the real middleware/views while the root
logger is captured through the **production** ``JsonFormatter`` — the same
sink a deployed backend writes.

Risk-note compliance: assertions build their probes from the runtime
redactor's own registered key names (``apps.core.scrub``), never from a
hardcoded copy that could drift; debug level is captured (the dev profile's
most verbose setting); correlation ids must survive scrubbing (NFR-10).

Repository half of the slice (Section 18 secret scans, FR-SEC-04) runs the
CI gate itself — ``.github/workflows/security.yaml`` /
``.pre-commit-config.yaml`` detect-secrets over every tracked file; fixture
secrets here carry ``# pragma: allowlist secret``.

Bridge counterpart: ``bridge/tests/test_logging.py`` redaction cases
(``-k redaction``).

Run with ``pytest backend/tests/ -k log_scrubbing -v`` (MT test command).
"""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.authentication import TokenBearerAuthentication
from apps.accounts.models import User
from apps.accounts.views import TokenListView
from apps.core.logging import JsonFormatter
from apps.core.scrub import (
    _SECRET_EXTRA_KEY_NAMES,
    _SECRET_EXTRA_KEY_SUFFIXES,
    MAX_SCRUBBED_CHARS,
    is_secret_extra_key,
    scrub_text,
)
from tests.attachments.helpers import PNG_BYTES, make_project, make_task, upload

PASSWORD = "wp61-log-scrubbing-1!"  # pragma: allowlist secret
ISSUED_SECRET = "sk-live-wp61-issued-token"  # pragma: allowlist secret


@pytest.fixture
def log_stream() -> Generator[io.StringIO, None, None]:
    """Capture the root logger through the production formatter at DEBUG."""
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


def _payloads(stream: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line]


@pytest.fixture
def owner_client(db: None) -> APIClient:
    """A fresh owner account (login happens inside the flows under test)."""
    User.objects.create_user("owner", None, PASSWORD)
    return APIClient()


def _assert_no_secret(raw: str, secret: str, note: str) -> None:
    assert secret not in raw, f"{note}: secret leaked into logs"


# --- sensitive flows (Sections 12.4, 17; RISK-14) ---------------------------


def test_login_success_and_failure_never_log_the_password(
    owner_client: APIClient, log_stream: io.StringIO
) -> None:
    """Both halves of the login flow keep the password out of every line."""
    assert (
        owner_client.post(
            "/api/v1/auth/login", {"username": "owner", "password": PASSWORD}
        ).status_code
        == 200
    )
    wrong = "wp61-wrong-password-attempt"  # pragma: allowlist secret
    assert (
        owner_client.post(
            "/api/v1/auth/login", {"username": "owner", "password": wrong}
        ).status_code
        == 401
    )

    raw = log_stream.getvalue()
    _assert_no_secret(raw, PASSWORD, "login success")
    _assert_no_secret(raw, wrong, "login failure")


def test_token_issuance_never_logs_the_plaintext_credential(
    owner_client: APIClient, log_stream: io.StringIO
) -> None:
    """The one-time plaintext from POST /tokens/agent stays out of the logs."""
    assert (
        owner_client.post(
            "/api/v1/auth/login", {"username": "owner", "password": PASSWORD}
        ).status_code
        == 200
    )
    response = owner_client.post(
        "/api/v1/tokens/agent", {"project_id": "PID00001", "scopes": ["coder"]}
    )
    assert response.status_code == 201, response.content
    plaintext = response.json()["token"]
    assert plaintext

    _assert_no_secret(log_stream.getvalue(), plaintext, "token issuance")


def test_device_registration_never_logs_the_released_token_or_push_token(
    owner_client: APIClient, log_stream: io.StringIO
) -> None:
    """Device onboarding: the released credential and the push token stay dark."""
    assert (
        owner_client.post(
            "/api/v1/auth/login", {"username": "owner", "password": PASSWORD}
        ).status_code
        == 200
    )
    response = owner_client.post(
        "/api/v1/devices", {"platform": "android", "push_token": "wp61-scrub-push-token"}
    )
    assert response.status_code == 201, response.content

    raw = log_stream.getvalue()
    _assert_no_secret(raw, response.json()["token"], "device token")
    _assert_no_secret(raw, "wp61-scrub-push-token", "device push token")


def test_agent_request_credential_is_never_logged_and_correlation_survives(
    owner_client: APIClient, log_stream: io.StringIO
) -> None:
    """An agent bearer on /work: token absent, correlation id intact (NFR-10)."""
    assert (
        owner_client.post(
            "/api/v1/auth/login", {"username": "owner", "password": PASSWORD}
        ).status_code
        == 200
    )
    issued = owner_client.post(
        "/api/v1/tokens/agent", {"project_id": "PID00001", "scopes": ["coder"]}
    ).json()

    headers = {
        "Authorization": f"{TokenBearerAuthentication.keyword} {issued['token']}",
        "X-Correlation-ID": "wp61-scrub-corr-01",
    }
    response = APIClient().get("/api/v1/projects/PID00001/work", headers=headers)
    assert response.status_code in (200, 400, 404), response.content  # empty/absent project alike

    raw = log_stream.getvalue()
    _assert_no_secret(raw, issued["token"], "agent request")
    request_lines = [p for p in _payloads(log_stream) if p.get("path", "").endswith("/work")]
    assert request_lines, "the request completed line exists"
    assert all(line.get("correlation_id") == "wp61-scrub-corr-01" for line in request_lines), (
        "scrubbing must never remove the correlation join key"
    )


def test_attachment_upload_logs_carry_no_bytes_and_truncate_excerpts(
    owner_client: APIClient, log_stream: io.StringIO, tmp_path: Path
) -> None:
    """Upload request lines never echo the body; long text truncates at DEBUG."""
    project = make_project()
    task = make_task(project)
    assert (
        owner_client.post(
            "/api/v1/auth/login", {"username": "owner", "password": PASSWORD}
        ).status_code
        == 200
    )

    marker = PNG_BYTES + b"\x00wp61-bytes-marker"
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        response = owner_client.post(
            f"/api/v1/tasks/{task.pk}/attachments",
            {"file": upload(marker, name="wp61-secret-design.png", content_type="image/png")},
            format="multipart",
        )
    # The synthetic tail breaks the PNG magic: the upload is refused — the
    # point here is the *log lines*, not the intake outcome.
    assert response.status_code in (201, 400, 415), response.content

    logging.getLogger("tests.wp61.truncate").debug(
        "attachment excerpt: %s", "ATTACHMENT-TEXT " * (MAX_SCRUBBED_CHARS // 2)
    )

    raw = log_stream.getvalue()
    _assert_no_secret(raw, "wp61-bytes-marker", "upload body")
    _assert_no_secret(raw, "wp61-secret-design.png", "upload filename")
    excerpts = [
        str(p["message"])
        for p in _payloads(log_stream)
        if "attachment excerpt" in str(p["message"])
    ]
    assert excerpts, "the debug line was captured"
    for message in excerpts:
        assert message.endswith("…[truncated]"), "Section 12.4 truncation, even at DEBUG"
        assert len(message) <= MAX_SCRUBBED_CHARS + len("…[truncated]")


# --- exception / error paths (MT risk note: stack traces leak) --------------


def test_exception_tracebacks_are_scrubbed_on_the_error_path(
    owner_client: APIClient, log_stream: io.StringIO, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A crashing view logs a scrubbed traceback — never the raw secret."""
    hidden = "wp61-exception-secret"  # pragma: allowlist secret

    def boom(self: Any, request: Any, *args: Any, **kwargs: Any) -> Any:
        raise ValueError(f"probe exploded with token={hidden}")

    monkeypatch.setattr(TokenListView, "get", boom)
    assert (
        owner_client.post(
            "/api/v1/auth/login", {"username": "owner", "password": PASSWORD}
        ).status_code
        == 200
    )
    response = owner_client.get("/api/v1/tokens", raise_request_exception=False)
    assert response.status_code == 500

    raw = log_stream.getvalue()
    _assert_no_secret(raw, hidden, "exception traceback")
    error_lines = [p for p in _payloads(log_stream) if p.get("exception")]
    assert error_lines, "the error path logged with exc_info"
    assert any("[REDACTED]" in str(p["exception"]) for p in error_lines)
    assert all(p.get("correlation_id") for p in error_lines), "the join key survives (NFR-10)"


# --- assertions tied to the redactor's own registry (MT risk note) ----------


def test_every_registered_secret_key_name_is_redacted() -> None:
    """Probes come from the runtime registry — no drifting pattern copy."""
    for key in sorted(_SECRET_EXTRA_KEY_NAMES):
        assert is_secret_extra_key(key)
        # The structured pass redacts by key before any content check.
        from apps.core.scrub import scrub_value

        assert scrub_value(key, ISSUED_SECRET) == "[REDACTED]"
    for suffix in _SECRET_EXTRA_KEY_SUFFIXES:
        assert is_secret_extra_key(f"agent{suffix}")


def test_bearer_shaped_header_text_is_scrubbed_at_every_level() -> None:
    """The header pattern survives at the dev profile's most verbose level."""
    secret_value = "wp61-level-sweep-token"  # pragma: allowlist secret
    header_line = f"{TokenBearerAuthentication.keyword} {secret_value}"
    for level in (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR):
        scrubbed = scrub_text(f"level={level} header={header_line}")
        assert secret_value not in scrubbed
        assert "[REDACTED]" in scrubbed


def test_request_logging_carries_no_headers_or_body_fields() -> None:
    """The request-completed line's shape cannot hold a credential (12.4)."""
    from django.http import HttpResponse
    from django.test import RequestFactory

    from apps.core.middleware import RequestLoggingMiddleware

    class _Recorder:
        def __init__(self) -> None:
            self.lines: list[str] = []

        def write(self, text: str) -> None:
            self.lines.append(text)

        def flush(self) -> None:
            return None

    recorder = _Recorder()
    handler = logging.StreamHandler(recorder)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.addHandler(handler)
    previous = root.level
    root.setLevel(logging.DEBUG)
    try:
        request = RequestFactory().post(
            "/api/v1/auth/login",
            {"username": "owner", "password": PASSWORD},  # pragma: allowlist secret
            HTTP_AUTHORIZATION=f"{TokenBearerAuthentication.keyword} header-probe",
        )
        RequestLoggingMiddleware(lambda r: HttpResponse()).__call__(request)
    finally:
        root.removeHandler(handler)
        root.setLevel(previous)

    # Nothing about the body or the Authorization header reached any line.
    stream_value = "".join(recorder.lines)
    _assert_no_secret(stream_value, PASSWORD, "request middleware")
    _assert_no_secret(stream_value, "header-probe", "request middleware header")
