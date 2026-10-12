"""MT-2.3-03 — idempotency keys: mutating verbs only, stable across retries.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.3-api-client/
MT-2.3-03-idempotency-keys.md (parent plan Sections 9.2, 10.10, 23/ADR-012;
NFR-12; headers.md).

Keys are proven at the HTTP boundary: presence exactly on mutating verbs,
identity across the retry loop's attempts, uniqueness across logical
operations, and absence from logs.
"""

from __future__ import annotations

import io
import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from orchestrator_bridge.api_errors import ApiError, ErrorCode
from orchestrator_bridge.config import Settings, load_settings
from orchestrator_bridge.idempotency import (
    IDEMPOTENCY_HEADER,
    MAX_KEY_CHARS,
    is_mutating,
    new_key,
)
from orchestrator_bridge.logging import configure_logging
from orchestrator_bridge.transport import ApiClient, WireResponse

ABSENT_CONFIG = Path("no-such-bridge-config.toml")
TOKEN = "fixture-token-not-a-real-secret"
KEY_SHAPE = re.compile(r"\A[A-Za-z0-9._-]+\Z")


@dataclass
class SentRequest:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes | None


@dataclass
class FakeSend:
    queue: list[WireResponse | BaseException] = field(default_factory=list)
    sent: list[SentRequest] = field(default_factory=list)

    def __call__(
        self, method: str, url: str, headers: Any, body: bytes | None, timeout: float
    ) -> WireResponse:
        self.sent.append(SentRequest(method, url, dict(headers), body))
        if not self.queue:
            raise AssertionError("FakeSend queue is empty")
        item = self.queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def _settings(**overrides: str) -> Settings:
    env = {"ORCHESTRATOR_AGENT_TOKEN": TOKEN, **overrides}
    return load_settings(env=env, config_path=ABSENT_CONFIG)


def _client(
    *responses: WireResponse | BaseException,
    settings: Settings | None = None,
    stream: io.StringIO | None = None,
) -> tuple[ApiClient, FakeSend]:
    resolved = settings or _settings()
    if stream is not None:
        configure_logging(resolved, stream=stream)
    fake = FakeSend(list(responses))
    client = ApiClient(
        resolved,
        send=fake,
        sleep=lambda _: None,  # recorded tests never wait (MT-2.3-02 seam)
        rng=random.Random(7),
    )
    return client, fake


def _ok() -> WireResponse:
    return WireResponse(200, {}, b'{"ok": true}')


def _retryable_500() -> WireResponse:
    body = json.dumps(
        {
            "error": {
                "code": "SERVER_ERROR",
                "message": "boom",
                "retryable": True,
                "correlation_id": "c0a8-4f2e-91d7",
            }
        }
    ).encode()
    return WireResponse(500, {}, body)


def _key_of(fake: FakeSend, index: int = 0) -> str:
    headers = fake.sent[index].headers
    assert IDEMPOTENCY_HEADER in headers
    return headers[IDEMPOTENCY_HEADER]


# --- header name: one canonical spelling (headers.md) ------------------------


def test_header_name_is_the_canonical_spelling() -> None:
    assert IDEMPOTENCY_HEADER == "Idempotency-Key"


@pytest.mark.parametrize(
    ("method", "mutating"),
    [
        ("POST", True),
        ("post", True),  # verbs are case-insensitive on the wire
        ("PATCH", True),
        ("PUT", True),
        ("DELETE", True),
        ("GET", False),
        ("HEAD", False),
        ("OPTIONS", False),
    ],
)
def test_is_mutating_classification(method: str, mutating: bool) -> None:
    assert is_mutating(method) is mutating


# --- presence: every mutating request, never a read --------------------------


@pytest.mark.parametrize("method", ["POST", "PATCH", "PUT", "DELETE"])
def test_mutating_requests_carry_a_key(method: str) -> None:
    client, fake = _client(_ok())
    client.request(method, "/api/v1/tasks/PID00007-T004/checkpoints", body={"percentage": 40})
    key = _key_of(fake)
    assert KEY_SHAPE.match(key)
    assert len(key) <= MAX_KEY_CHARS


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_reads_never_carry_a_key(method: str) -> None:
    client, fake = _client(_ok())
    client.request(method, "/api/v1/projects/PID00007/work")
    assert IDEMPOTENCY_HEADER not in fake.sent[0].headers


# --- uniqueness: distinct logical operations never share a key ---------------


def test_separate_calls_get_distinct_keys() -> None:
    """Same endpoint twice = two logical operations = two keys (NFR-12)."""
    client, fake = _client(_ok(), _ok())
    client.request("POST", "/api/v1/tasks/PID00007-T004/claim", body={})
    client.request("POST", "/api/v1/tasks/PID00007-T004/claim", body={})
    assert _key_of(fake, 0) != _key_of(fake, 1)


def test_different_targets_get_distinct_keys() -> None:
    client, fake = _client(_ok(), _ok())
    client.request("POST", "/api/v1/tasks/PID00007-T001/claim", body={})
    client.request("POST", "/api/v1/tasks/PID00007-T002/claim", body={})
    first, second = _key_of(fake, 0), _key_of(fake, 1)
    assert first != second
    assert "PID00007-T001" in first and "PID00007-T002" in second  # target visible


def test_new_key_shape_nonce_sequence_fingerprint() -> None:
    first = new_key("POST", target="/api/v1/tasks/PID00007-T004/claim")
    second = new_key("POST", target="/api/v1/tasks/PID00007-T004/claim")
    nonce_first, seq_first, *_ = first.split("-", 2)
    nonce_second, seq_second, *_ = second.split("-", 2)
    assert nonce_first == nonce_second  # one process-run nonce
    assert seq_first != seq_second  # monotonic sequence
    assert first != second
    assert KEY_SHAPE.match(first)
    assert "api-v1-tasks-PID00007-T004-claim" in first  # slugified target


def test_new_key_without_target_still_unique() -> None:
    assert new_key("POST") != new_key("POST")


# --- stability: a retried operation re-sends the identical key ---------------


def test_retry_replays_the_identical_key() -> None:
    """The MT's core guarantee: one logical call, one key, N attempts."""
    client, fake = _client(_retryable_500(), _retryable_500(), _ok())
    client.request("POST", "/api/v1/tasks/PID00007-T004/checkpoints", body={"percentage": 10})

    assert len(fake.sent) == 3
    keys = {_key_of(fake, i) for i in range(3)}
    assert len(keys) == 1
    # The whole header set replays identically (ADR-012 pairing with retry).
    assert fake.sent[0].headers == fake.sent[1].headers == fake.sent[2].headers


def test_caller_supplied_key_is_used_verbatim() -> None:
    """A caller may span one logical operation across explicit calls."""
    client, fake = _client(_ok())
    client.request(
        "POST",
        "/api/v1/agent-sessions",
        body={"project_id": "PID00007"},
        idempotency_key="session-open-PID00007-run1",
    )
    assert _key_of(fake) == "session-open-PID00007-run1"


def test_key_survives_through_final_failure() -> None:
    """Retries up to the cap all carry the same key; the raised error does not."""
    client, fake = _client(_retryable_500(), _retryable_500(), _retryable_500())
    with pytest.raises(ApiError) as excinfo:
        client.request("POST", "/api/v1/tasks/PID00007-T004/resolution", body={})
    assert excinfo.value.code is ErrorCode.SERVER_ERROR
    assert len(fake.sent) == 3
    assert len({_key_of(fake, i) for i in range(3)}) == 1


# --- hygiene: no key material in logs ----------------------------------------


def test_idempotency_key_never_appears_in_logs() -> None:
    stream = io.StringIO()
    client, fake = _client(_retryable_500(), _ok(), stream=stream)
    client.request("POST", "/api/v1/tasks/PID00007-T004/checkpoints", body={"percentage": 5})

    key = _key_of(fake)
    logged = stream.getvalue()
    assert key not in logged
    assert TOKEN not in logged
    # The retry was still observably logged (Section 17), minus the key.
    assert "api_retry" in logged
