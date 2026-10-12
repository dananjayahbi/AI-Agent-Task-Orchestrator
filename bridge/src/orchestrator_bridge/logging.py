"""Structured JSON-line logging for the bridge (parent plan Section 17; MT-2.1-03).

One line = one JSON object (NDJSON). Base fields (the MT's required set):

``st_dev``      stable identifier of the host device running the bridge
                (hostname) — distinguishes logs coming from many agent machines
``pid``         emitting process id
``level``       standard logging level name (``INFO``, …)
``timestamp``   ISO-8601 UTC with milliseconds and ``Z`` suffix (Principle P7;
                same spelling as the backend's logs, Section 17)
``component``   ``bridge.<module>`` — the bridge's own tag
``message``     human-readable text, scrubbed and truncated

Plus ``correlation_id`` iff a scope is installed (headers.md), ``exception``
iff ``exc_info`` was passed, and any ``extra=`` fields scrubbed by key and
content. Redaction happens in exactly one place — ``scrub.py`` (FR-SEC-01, G-07),
paired with the structural token redaction of ``config.py`` (MT-2.1-02).

Stream rule (MT-2.1-03 risk note, verified against the MCP Python SDK 2.3.0
``mcp/server/stdio.py``): the stdio transport claims fd 1 for its JSON-RPC
frames and only diverts fd 1 to stderr *while serving*, so diagnostics written
outside that window would hit the wire. stdio mode therefore logs to
**stderr** — a deviation from the generic "stdout" channel, recorded in the WP
changelog as an OQ candidate. The HTTP and executor modes log to stdout.
No log files or rotation: host-owned (MT-2.1-03 out of scope).
"""

from __future__ import annotations

import json
import logging
import socket
import sys
from datetime import UTC, datetime
from typing import IO, Any

from .config import RunMode, Settings
from .correlation import get_correlation_id
from .scrub import scrub_text, scrub_value

__all__ = [
    "JsonFormatter",
    "TextFormatter",
    "configure_logging",
    "get_logger",
]

# One stable per-host device tag for every line of this process (Section 17
# base field `st_dev`; the value is this machine's hostname — interpretation
# recorded in the WP changelog as an OQ candidate).
ST_DEV: str = socket.gethostname()

_BRIDGE_LOGGER_NAME = "bridge"

# Attributes every LogRecord already carries — anything else in __dict__ is an
# `extra=` field and belongs in the payload.
_STANDARD_RECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class JsonFormatter(logging.Formatter):
    """Render a LogRecord as one scrubbed JSON line (Section 17)."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize *record* to a single-line JSON object."""
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "component": record.name,
            "st_dev": ST_DEV,
            "pid": record.process,
            "message": scrub_text(record.getMessage()),
        }
        correlation_id = get_correlation_id()
        if correlation_id:
            payload["correlation_id"] = correlation_id
        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_ATTRS or key in payload:
                continue
            payload[key] = scrub_value(key, value)
        if record.exc_info is not None:
            payload["exception"] = scrub_text(self.formatException(record.exc_info))
        return json.dumps(payload, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Single-line human format for the explicit ``log_format = "text"`` opt-in.

    Redaction and truncation still apply (one redaction point, MT-2.1-03) —
    ``text`` changes readability only, never the scrubbing rules.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Serialize *record* to one scrubbed line."""
        correlation_id = get_correlation_id()
        scope = f" correlation_id={correlation_id}" if correlation_id else ""
        line = (
            f"{record.levelname} {record.name} pid={record.process} "
            f"st_dev={ST_DEV}{scope} {record.getMessage()}"
        )
        if record.exc_info is not None:
            line = f"{line} | {self.formatException(record.exc_info)}"
        return scrub_text(line)


def configure_logging(
    settings: Settings,
    *,
    stream: IO[str] | None = None,
    mode: RunMode | None = None,
) -> logging.Logger:
    """Install the bridge logger handler; configured once from ``settings``.

    Idempotent (handlers replaced, never stacked) and double-emission-proof
    (``propagate = False``: the MCP SDK's ``MCPServer`` calls
    ``logging.basicConfig`` on the root logger, which must not duplicate bridge
    lines). ``mode`` defaults to ``settings.mode``; the CLI passes the *resolved*
    run mode so the ``--mode`` flag and the stream choice never disagree.
    ``stream`` defaults to stderr for stdio (MCP framing safety, module
    docstring) and stdout otherwise; tests inject their own stream.
    """
    effective_mode = settings.mode if mode is None else mode
    target = stream
    if target is None:
        target = sys.stderr if effective_mode is RunMode.STDIO else sys.stdout
    handler = logging.StreamHandler(target)
    handler.setFormatter(JsonFormatter() if settings.log_format == "json" else TextFormatter())
    logger = logging.getLogger(_BRIDGE_LOGGER_NAME)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(settings.log_level)
    logger.propagate = False
    return logger


def get_logger(component: str) -> logging.Logger:
    """A logger tagged ``bridge.<component>`` (the Section 17 component field)."""
    return logging.getLogger(f"{_BRIDGE_LOGGER_NAME}.{component}")
