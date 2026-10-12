"""MT-2.3-01 — transport and authentication: headers, envelope parsing, version gate.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.3-api-client/
MT-2.3-01-transport-auth.md (parent plan Sections 9.2, 10.1, 10.3, 10.10,
10.11, 12.2; NFR-04; ADR-005).

The transport is exercised at its HTTP boundary (the injectable ``send`` seam —
the preferred mock point: deterministic, no live backend, no Docker). Everything
above the seam is real: header assembly, token resolution, envelope parsing,
error mapping.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from orchestrator_bridge import transport
from orchestrator_bridge.api_errors import ApiError, ErrorCode, ErrorKind
from orchestrator_bridge.config import ConfigError, Settings, load_settings
from orchestrator_bridge.correlation import (
    CORRELATION_HEADER,
    reset_correlation_id,
    set_correlation_id,
)
from orchestrator_bridge.errors import ApiVersionError, TokenError
from orchestrator_bridge.logging import configure_logging
from orchestrator_bridge.manifest import StartupBinding
from orchestrator_bridge.transport import (
    API_VERSION_HEADER,
    EXPECTED_API_VERSION,
    HEALTH_PATH,
    ApiClient,
    WireResponse,
    verify_api_version,
)

ABSENT_CONFIG = Path("no-such-bridge-config.toml")
TOKEN = "fixture-token-not-a-real-secret"


@dataclass
class SentRequest:
    """One captured request at the HTTP boundary."""

    method: str
    url: str
    headers: dict[str, str]
    body: bytes | None
    timeout: float


@dataclass
class FakeSend:
    """Deterministic boundary fake: queued WireResponses or exceptions to raise."""

    queue: list[WireResponse | BaseException] = field(default_factory=list)
    sent: list[SentRequest] = field(default_factory=list)

    def __call__(
        self,
        method: str,
        url: str,
        headers: Any,
        body: bytes | None,
        timeout: float,
    ) -> WireResponse:
        self.sent.append(
            SentRequest(
                method=method,
                url=url,
                headers=dict(headers),
                body=body,
                timeout=timeout,
            )
        )
        if not self.queue:
            raise AssertionError("FakeSend queue is empty")
        next_item = self.queue.pop(0)
        if isinstance(next_item, BaseException):
            raise next_item
        return next_item


def _settings(extra_env: dict[str, str] | None = None) -> Settings:
    # retry_max_attempts=1: this suite exercises MT-2.3-01 parsing paths, not
    # MT-2.3-02 retries (test_retry.py covers those) — one attempt per call.
    env = {
        "ORCHESTRATOR_AGENT_TOKEN": TOKEN,
        "ORCHESTRATOR_BRIDGE_RETRY_MAX_ATTEMPTS": "1",
    }
    env.update(extra_env or {})
    return load_settings(env=env, config_path=ABSENT_CONFIG)


def _client(
    *responses: WireResponse | BaseException,
    settings: Settings | None = None,
) -> tuple[ApiClient, FakeSend]:
    fake = FakeSend(list(responses))
    return ApiClient(settings or _settings(), send=fake), fake


def _envelope_body(
    code: str = "AUTH_REQUIRED",
    *,
    message: str = "Authentication credentials were not provided.",
    retryable: bool = False,
    details: dict[str, Any] | None = None,
    correlation_id: str = "c0a8-4f2e-91d7",
) -> bytes:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "retryable": retryable,
        "correlation_id": correlation_id,
    }
    if details is not None:
        error["details"] = details
    return json.dumps({"error": error}).encode("utf-8")


def _binding(manifest: dict[str, Any] | None = None) -> StartupBinding:
    document: dict[str, Any] = {"project_id": "PID00007"}
    if manifest is not None:
        document = manifest
    return StartupBinding(manifest_path=Path("orchestrator.json"), manifest=document)


# --- success path: headers on every request ----------------------------------


def test_success_parses_json_body() -> None:
    client, fake = _client(WireResponse(200, {}, b'{"status": "ok"}'))
    assert client.request("GET", "/health/live") == {"status": "ok"}
    assert fake.sent[0].method == "GET"
    assert fake.sent[0].timeout == 30.0  # settings.timeout_seconds (Section 9.10)


def test_every_request_carries_token_version_and_correlation_headers() -> None:
    client, fake = _client(WireResponse(200, {}, b"{}"))
    client.request("GET", "/api/v1/projects/PID00007")
    headers = fake.sent[0].headers
    assert headers["Authorization"] == f"Bearer {TOKEN}"
    assert headers[API_VERSION_HEADER] == EXPECTED_API_VERSION
    # No scope installed by this test (conftest installs "") → a fresh id is
    # sent (headers.md: the caller generates when it has none to supply).
    assert headers[CORRELATION_HEADER]  # non-empty
    assert headers["Accept"] == "application/json"


def test_installed_correlation_scope_is_propagated_verbatim() -> None:
    token = set_correlation_id("feed-5eed-0001")
    try:
        client, fake = _client(WireResponse(200, {}, b"{}"))
        client.request("GET", "/health/live")
        assert fake.sent[0].headers[CORRELATION_HEADER] == "feed-5eed-0001"
    finally:
        reset_correlation_id(token)


def test_token_never_appears_in_url_repr_or_error() -> None:
    """Section 12.4 + MT-2.3-01 AC: bearer material stays in the header only."""
    client, fake = _client(WireResponse(401, {}, _envelope_body()))
    assert TOKEN not in repr(client)
    with pytest.raises(ApiError) as excinfo:
        client.request("GET", "/api/v1/tasks/PID00007-T004")
    assert TOKEN not in fake.sent[0].url
    assert TOKEN not in str(excinfo.value)
    assert TOKEN not in repr(excinfo.value)


def test_json_body_is_sent_with_content_type() -> None:
    client, fake = _client(WireResponse(201, {}, b'{"id": 1}'))
    client.request("POST", "/api/v1/agent-sessions", body={"project_id": "PID00007"})
    sent = fake.sent[0]
    assert sent.headers["Content-Type"] == "application/json"
    assert json.loads(sent.body or b"") == {"project_id": "PID00007"}


def test_empty_success_body_decodes_to_none() -> None:
    client, _ = _client(WireResponse(204, {}, b""))
    assert client.request("POST", "/api/v1/agent-sessions/x/end") is None


# --- base URL resolution (the WP-2.2 deferral, resolved here) ----------------


def test_binding_manifest_base_url_wins_over_settings() -> None:
    fake = FakeSend([WireResponse(200, {}, b"{}")])
    binding = _binding(
        {"project_id": "PID00007", "orchestrator_api": "http://manifest-host/api/v1"}
    )
    client = ApiClient.for_binding(binding, _settings(), send=fake)
    client.request("GET", "/api/v1/projects/PID00007")
    assert fake.sent[0].url == "http://manifest-host/api/v1/projects/PID00007"


def test_binding_falls_back_to_settings_base_url_when_key_absent() -> None:
    fake = FakeSend([WireResponse(200, {}, b"{}")])
    client = ApiClient.for_binding(_binding(), _settings(), send=fake)
    client.request("GET", "health/live")  # relative form joins the base path
    assert fake.sent[0].url == "http://localhost:8000/api/v1/health/live"


def test_non_http_base_url_fails_fast() -> None:
    with pytest.raises(ConfigError, match="http"):
        ApiClient(_settings(), base_url="ftp://backend.example/api/v1")


# --- non-2xx: Section 9.2 envelope parsing (401 path) ------------------------


def test_401_envelope_becomes_typed_auth_required_error() -> None:
    client, _ = _client(WireResponse(401, {}, _envelope_body(details={"header": "Authorization"})))
    with pytest.raises(ApiError) as excinfo:
        client.request("GET", "/api/v1/projects/PID00007")
    error = excinfo.value
    assert error.code is ErrorCode.AUTH_REQUIRED
    assert error.kind is ErrorKind.ENVELOPE
    assert error.retryable is False  # verbatim server flag
    assert error.status_code == 401
    assert error.correlation_id == "c0a8-4f2e-91d7"
    assert error.details == {"header": "Authorization"}
    assert error.message == "Authentication credentials were not provided."
    assert "AUTH_REQUIRED" in str(error)


def test_retryable_flag_is_taken_verbatim_even_if_unusual() -> None:
    """Flag authority (error-envelope.md rule 3): never re-guessed from status."""
    client, _ = _client(
        WireResponse(409, {}, _envelope_body("TASK_ALREADY_CLAIMED", retryable=True))
    )
    with pytest.raises(ApiError) as excinfo:
        client.request("POST", "/api/v1/tasks/PID00007-T004/claim")
    assert excinfo.value.code is ErrorCode.TASK_ALREADY_CLAIMED
    assert excinfo.value.retryable is True


def test_malformed_body_degrades_to_server_error_tagged_error() -> None:
    client, _ = _client(WireResponse(500, {}, b"<html>gateway exploded</html>"))
    with pytest.raises(ApiError) as excinfo:
        client.request("GET", "/api/v1/projects/PID00007")
    error = excinfo.value
    assert error.code is ErrorCode.SERVER_ERROR
    assert error.kind is ErrorKind.MALFORMED_RESPONSE
    assert error.retryable is True  # 5xx status guess when no flag exists
    assert error.status_code == 500


def test_malformed_body_on_4xx_is_not_retryable() -> None:
    client, _ = _client(WireResponse(404, {}, b"not json"))
    with pytest.raises(ApiError) as excinfo:
        client.request("GET", "/api/v1/tasks/PID00007-T004")
    assert excinfo.value.code is ErrorCode.SERVER_ERROR
    assert excinfo.value.kind is ErrorKind.MALFORMED_RESPONSE
    assert excinfo.value.retryable is False


def test_structurally_wrong_envelope_is_treated_as_malformed() -> None:
    """Strict parse: a missing required field → degrade, never half-trust."""
    broken = json.dumps({"error": {"code": "AUTH_REQUIRED", "message": "x"}}).encode()
    client, _ = _client(WireResponse(401, {}, broken))
    with pytest.raises(ApiError) as excinfo:
        client.request("GET", "/api/v1/projects/PID00007")
    assert excinfo.value.kind is ErrorKind.MALFORMED_RESPONSE
    assert excinfo.value.code is ErrorCode.SERVER_ERROR


def test_out_of_catalog_code_is_downgraded_and_upstream_preserved() -> None:
    """Section 20.4 item 5: the bridge never emits an uncatalogued code."""
    client, _ = _client(WireResponse(400, {}, _envelope_body("FUTURE_CODE")))
    with pytest.raises(ApiError) as excinfo:
        client.request("GET", "/api/v1/projects/PID00007")
    error = excinfo.value
    assert error.code is ErrorCode.SERVER_ERROR
    assert error.details is not None and error.details["upstream_code"] == "FUTURE_CODE"


def test_error_correlation_prefers_backend_response_header_when_body_unparseable() -> None:
    client, _ = _client(WireResponse(500, {CORRELATION_HEADER.lower(): "aaaa-bbbb-cccc"}, b"oops"))
    with pytest.raises(ApiError) as excinfo:
        client.request("GET", "/health/live")
    assert excinfo.value.correlation_id == "aaaa-bbbb-cccc"


# --- transport failures ------------------------------------------------------


def test_connection_refused_maps_to_retryable_transport_failure() -> None:
    client, _ = _client(ConnectionRefusedError(111, "Connection refused"))
    with pytest.raises(ApiError) as excinfo:
        client.request("POST", "/api/v1/agent-sessions")
    error = excinfo.value
    assert error.kind is ErrorKind.TRANSPORT_FAILURE
    assert error.code is ErrorCode.SERVER_ERROR
    assert error.retryable is True  # Section 10.10
    assert error.status_code is None
    assert "ConnectionRefusedError" in error.message


def test_timeout_maps_to_retryable_transport_failure() -> None:
    client, _ = _client(TimeoutError("timed out"))
    with pytest.raises(ApiError) as excinfo:
        client.request("GET", "/api/v1/projects/PID00007/work")
    assert excinfo.value.kind is ErrorKind.TRANSPORT_FAILURE
    assert excinfo.value.retryable is True


def test_oversized_response_is_not_retryable() -> None:
    """Same bytes every attempt — the cap fails fast with an actionable message."""
    client, _ = _client(transport._ResponseTooLarge(200))
    with pytest.raises(ApiError) as excinfo:
        client.request("GET", "/api/v1/attachments/9")
    error = excinfo.value
    assert error.kind is ErrorKind.MALFORMED_RESPONSE
    assert error.retryable is False
    assert error.details is not None and error.details["reason"] == "response_too_large"
    assert "ORCHESTRATOR_BRIDGE_MAX_RESPONSE_MB" in error.message


def test_read_capped_stops_at_the_limit() -> None:
    cap = 16
    assert transport._read_capped(io.BytesIO(b"x" * 16), 200, cap) == b"x" * 16
    with pytest.raises(transport._ResponseTooLarge) as excinfo:
        transport._read_capped(io.BytesIO(b"x" * 17), 503, cap)
    assert excinfo.value.status == 503


# --- Section 10.11 version gate ----------------------------------------------


def _versioned_client(
    headers: dict[str, str], *, stream: io.StringIO | None = None
) -> tuple[ApiClient, FakeSend]:
    settings = _settings()
    if stream is not None:
        configure_logging(settings, stream=stream)
    fake = FakeSend([WireResponse(200, headers, b'{"status": "ok"}')])
    return ApiClient(settings, send=fake), fake


def test_version_match_returns_advertised_value() -> None:
    client, _ = _versioned_client({API_VERSION_HEADER.lower(): "v1"})
    assert verify_api_version(client) == "v1"


def test_version_mismatch_aborts_with_actionable_message() -> None:
    client, _ = _versioned_client({API_VERSION_HEADER.lower(): "v2"})
    with pytest.raises(ApiVersionError) as excinfo:
        verify_api_version(client)
    message = str(excinfo.value)
    assert "v2" in message and EXPECTED_API_VERSION in message
    assert "upgrade the bridge or the backend" in message


def test_unparseable_advertised_version_is_a_mismatch() -> None:
    client, _ = _versioned_client({API_VERSION_HEADER.lower(): "next-gen"})
    with pytest.raises(ApiVersionError, match="next-gen"):
        verify_api_version(client)


def test_missing_version_header_is_unverified_not_a_failure() -> None:
    stream = io.StringIO()
    client, _ = _versioned_client({}, stream=stream)
    assert verify_api_version(client) is None
    records = [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
    assert any(record.get("event") == "api_version_unverified" for record in records)


def test_version_probe_uses_health_live_with_full_headers() -> None:
    client, fake = _versioned_client({API_VERSION_HEADER.lower(): "1"})
    verify_api_version(client)
    sent = fake.sent[0]
    assert sent.method == "GET"
    assert sent.url.endswith(HEALTH_PATH)
    assert sent.headers["Authorization"] == f"Bearer {TOKEN}"
    assert sent.headers[API_VERSION_HEADER] == EXPECTED_API_VERSION


# --- client construction and log hygiene -------------------------------------


def test_client_requires_a_usable_token_at_construction() -> None:
    empty = load_settings(env={}, config_path=ABSENT_CONFIG)
    with pytest.raises(TokenError):
        ApiClient(empty)


def test_failure_logging_never_includes_authorization_header() -> None:
    stream = io.StringIO()
    settings = _settings()
    configure_logging(settings, stream=stream)
    client, _ = _client(WireResponse(401, {}, _envelope_body()), settings=settings)
    with pytest.raises(ApiError):
        client.request("GET", "/api/v1/projects/PID00007")
    logged = stream.getvalue()
    assert TOKEN not in logged
    assert "Bearer" not in logged
    assert "api_error" in logged


def test_send_receives_settings_timeout() -> None:
    settings = _settings({"ORCHESTRATOR_BRIDGE_TIMEOUT_SECONDS": "7.5"})
    fake = FakeSend([WireResponse(200, {}, b"{}")])
    ApiClient(settings, send=fake).request("GET", "/health/live")
    assert fake.sent[0].timeout == 7.5
