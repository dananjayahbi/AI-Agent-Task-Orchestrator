"""MT-2.1-03 — structured logging: JSON schema, redaction, correlation, levels, events.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.1-bridge-skeleton/
MT-2.1-03-structured-logging.md (parent plan Sections 17, 10.10, 10.2;
FR-SEC-01; G-07; NFR-10).
"""

from __future__ import annotations

import io
import json
import logging as std_logging
import os
import re
import sys
from pathlib import Path

import pytest

from orchestrator_bridge.config import RunMode, Settings, load_settings
from orchestrator_bridge.correlation import (
    CORRELATION_ENV_VAR,
    CORRELATION_HEADER,
    get_correlation_id,
    init_from_env,
    reset_correlation_id,
    set_correlation_id,
)
from orchestrator_bridge.events import log_retry_attempt, log_stale_session_abort
from orchestrator_bridge.logging import configure_logging, get_logger
from orchestrator_bridge.scrub import MAX_SCRUBBED_CHARS

_ABSENT_CONFIG = Path("no-such-bridge-config.toml")


def _settings(env: dict[str, str] | None = None) -> Settings:
    return load_settings(env=env or {}, config_path=_ABSENT_CONFIG)


def _stream_settings(stream: io.StringIO, env: dict[str, str] | None = None) -> Settings:
    settings = _settings(env)
    configure_logging(settings, stream=stream)
    return settings


def _records(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


# --- Section 17 schema --------------------------------------------------------


def test_json_line_has_section17_base_fields_and_component_tag() -> None:
    stream = io.StringIO()
    _stream_settings(stream)
    get_logger("unit").info("started", extra={"attempt": 1})
    [record] = _records(stream)
    assert {"timestamp", "level", "component", "st_dev", "pid", "message"} <= record.keys()
    assert record["component"] == "bridge.unit"
    assert record["pid"] == os.getpid()
    assert record["level"] == "INFO"
    assert record["message"] == "started"
    assert record["attempt"] == 1
    assert isinstance(record["timestamp"], str) and record["timestamp"].endswith("Z")
    assert isinstance(record["st_dev"], str) and record["st_dev"]


def test_correlation_id_round_trip_and_omission() -> None:
    stream = io.StringIO()
    _stream_settings(stream)
    token = set_correlation_id("c0a8-4f2e-91d7")
    get_logger("unit").info("with scope")
    reset_correlation_id(token)
    get_logger("unit").info("without scope")
    first, second = _records(stream)
    assert first["correlation_id"] == "c0a8-4f2e-91d7"
    assert "correlation_id" not in second


def test_correlation_env_honor_or_generate_and_header_spelling() -> None:
    assert CORRELATION_HEADER == "X-Correlation-ID"
    assert CORRELATION_ENV_VAR == "ORCHESTRATOR_CORRELATION_ID"
    token = init_from_env({CORRELATION_ENV_VAR: "abc-DEF.123:_ok"})
    assert get_correlation_id() == "abc-DEF.123:_ok"
    reset_correlation_id(token)
    token = init_from_env({CORRELATION_ENV_VAR: "bad id with spaces!"})
    assert re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", get_correlation_id())
    reset_correlation_id(token)
    token = init_from_env({})
    assert re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", get_correlation_id())
    reset_correlation_id(token)


def test_level_filtering_follows_settings() -> None:
    stream = io.StringIO()
    _stream_settings(stream, {"ORCHESTRATOR_LOG_LEVEL": "WARNING"})
    logger = get_logger("unit")
    logger.debug("quiet debug")
    logger.info("quiet info")
    logger.warning("loud warning")
    [record] = _records(stream)
    assert record["level"] == "WARNING" and record["message"] == "loud warning"


# --- redaction (single point) -------------------------------------------------


def test_token_and_authorization_never_leak() -> None:
    stream = io.StringIO()
    _stream_settings(stream)
    get_logger("unit").info(
        "header was Authorization: Bearer sekrit-bearer-value",
        extra={
            "agent_token": "sekrit-field-value",  # pragma: allowlist secret
            "api_key": "sekrit-api-key",  # pragma: allowlist secret
        },
    )
    raw = stream.getvalue()
    assert "sekrit" not in raw
    assert raw.count("[REDACTED]") >= 1
    [record] = _records(stream)
    assert record["agent_token"] == "[REDACTED]"
    assert record["api_key"] == "[REDACTED]"
    assert "[REDACTED]" in str(record["message"])


def test_prompt_and_attachment_content_are_omitted() -> None:
    stream = io.StringIO()
    _stream_settings(stream)
    prompt_text = "ignore previous instructions " * 20
    attachment_text = "secret attachment bytes " * 40
    get_logger("unit").info(
        "tool result",
        extra={"prompt": prompt_text, "attachment_content": attachment_text},
    )
    raw = stream.getvalue()
    assert "ignore previous" not in raw
    assert "secret attachment" not in raw
    [record] = _records(stream)
    assert record["prompt"] == "[OMITTED]"
    assert record["attachment_content"] == "[OMITTED]"


def test_long_message_is_truncated() -> None:
    stream = io.StringIO()
    _stream_settings(stream)
    get_logger("unit").info("x" * (MAX_SCRUBBED_CHARS * 3))
    [record] = _records(stream)
    message = str(record["message"])
    assert len(message) < MAX_SCRUBBED_CHARS + 50
    assert message.endswith("…[truncated]")


def test_text_format_opt_in_still_scrubs() -> None:
    stream = io.StringIO()
    _stream_settings(stream, {"ORCHESTRATOR_LOG_FORMAT": "text"})
    get_logger("unit").info("token=sekrit-text-format-value")
    line = stream.getvalue()
    assert "sekrit" not in line
    assert "[REDACTED]" in line
    assert "bridge.unit" in line


# --- stream selection (stdio framing safety) ----------------------------------


def test_stdio_mode_defaults_to_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_out, fake_err = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", fake_out)
    monkeypatch.setattr(sys, "stderr", fake_err)
    settings = _settings()  # default mode = stdio
    assert settings.mode is RunMode.STDIO
    configure_logging(settings)  # no injected stream: resolves at call time
    get_logger("unit").info("framing stays clean")
    assert "framing stays clean" in fake_err.getvalue()
    assert fake_out.getvalue() == ""


def test_http_mode_defaults_to_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_out, fake_err = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", fake_out)
    monkeypatch.setattr(sys, "stderr", fake_err)
    settings = _settings({"ORCHESTRATOR_BRIDGE_MODE": "http"})
    configure_logging(settings)
    get_logger("unit").info("http diagnostics")
    assert "http diagnostics" in fake_out.getvalue()
    assert fake_err.getvalue() == ""


def test_reconfigure_replaces_handlers_and_stays_off_the_root() -> None:
    first, second = io.StringIO(), io.StringIO()
    configure_logging(_settings(), stream=first)
    configure_logging(_settings(), stream=second)
    get_logger("unit").info("exactly once")
    assert first.getvalue() == ""
    assert len(_records(second)) == 1
    bridge_logger = std_logging.getLogger("bridge")
    assert len(bridge_logger.handlers) == 1
    assert bridge_logger.propagate is False


# --- Section 10.10 resilience events ------------------------------------------


def test_retry_and_stale_session_event_shapes() -> None:
    stream = io.StringIO()
    _stream_settings(stream)
    log_retry_attempt(
        component="unit",
        operation="submit_resolution",
        attempt=2,
        max_attempts=5,
        cause="HTTP_5XX",
        backoff_seconds=1.5,
    )
    log_stale_session_abort(
        component="unit",
        session_id="SID0001",
        reason="lease expired without checkpoint",
        stale_for_seconds=95.0,
    )
    retry, stale = _records(stream)
    assert retry["event"] == "retry_attempt"
    assert retry["component"] == "bridge.unit"
    assert retry["level"] == "INFO"
    assert retry["attempt"] == 2 and retry["max_attempts"] == 5
    assert retry["operation"] == "submit_resolution" and retry["cause"] == "HTTP_5XX"
    assert retry["backoff_seconds"] == 1.5
    assert stale["event"] == "stale_session_abort"
    assert stale["level"] == "WARNING"
    assert stale["session_id"] == "SID0001"
    assert stale["reason"] == "lease expired without checkpoint"
    assert stale["stale_for_seconds"] == 95.0


# --- MT-6.1-04 (WP-6.1): redaction depth audit -------------------------------


def test_redaction_covers_every_registered_secret_key_name() -> None:
    """Probes come from the runtime registry - a new key is covered by construction."""
    from orchestrator_bridge.scrub import (
        _SECRET_KEY_NAMES,
        _SECRET_KEY_SUFFIXES,
        scrub_value,
    )

    probe = "wp61-bridge-secret-value"  # pragma: allowlist secret
    for key in sorted(_SECRET_KEY_NAMES):
        assert scrub_value(key, probe) == "[REDACTED]", key
    for suffix in _SECRET_KEY_SUFFIXES:
        assert scrub_value(f"session{suffix}", probe) == "[REDACTED]", suffix


def test_redaction_survives_every_log_level_including_debug() -> None:
    """The dev profile's most verbose level keeps the scrubbing rules (12.4)."""
    stream = io.StringIO()
    _stream_settings(stream, {"ORCHESTRATOR_LOG_LEVEL": "DEBUG"})
    secret = "wp61-bridge-level-token"  # pragma: allowlist secret
    logger = get_logger("unit")
    for level in (
        std_logging.DEBUG,
        std_logging.INFO,
        std_logging.WARNING,
        std_logging.ERROR,
        std_logging.CRITICAL,
    ):
        logger.log(level, f"authorization: {secret}", extra={"session_token": secret})
    raw = stream.getvalue()
    assert secret not in raw
    records = _records(stream)
    assert len(records) == 5
    assert all(record["session_token"] == "[REDACTED]" for record in records)


def test_redaction_applies_to_exception_tracebacks() -> None:
    """logger.exception paths are scrubbed through the single redaction point."""
    stream = io.StringIO()
    _stream_settings(stream)
    secret = "wp61-bridge-exception-token"  # pragma: allowlist secret
    logger = get_logger("unit")
    try:
        raise RuntimeError(f"probe exploded with token={secret}")
    except RuntimeError:
        logger.exception("operation failed")
    raw = stream.getvalue()
    assert secret not in raw
    [record] = _records(stream)
    assert "exception" in record and "RuntimeError" in str(record["exception"])
    assert "[REDACTED]" in str(record["exception"])


def test_redaction_keeps_correlation_ids_intact() -> None:
    """Scrubbing never removes the NFR-10 join key from a redacted line."""
    stream = io.StringIO()
    _stream_settings(stream)
    secret = "wp61-bridge-corr-token"  # pragma: allowlist secret
    token = set_correlation_id("wp61-bridge-corr-01")
    try:
        get_logger("unit").warning(f"authorization: {secret}")
    finally:
        reset_correlation_id(token)
    [record] = _records(stream)
    assert record["correlation_id"] == "wp61-bridge-corr-01"
    assert secret not in str(record["message"])
    assert "[REDACTED]" in str(record["message"])
