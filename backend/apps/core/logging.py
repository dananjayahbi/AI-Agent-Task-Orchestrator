"""Structured JSON logging (Section 17) — the single field-spelling authority.

Every log line is one JSON object on one line (NDJSON), carrying:

==================  =========================================================
Field               Meaning
==================  =========================================================
``timestamp``       ISO-8601 UTC with milliseconds (``…Z``), Principle P7
``level``           standard logging level name (``INFO``, ``ERROR``, …)
``logger``          originating logger name
``message``         human-readable message, scrubbed and truncated (12.4)
``correlation_id``  present iff the line is emitted inside a request scope
``exception``       formatted traceback, present iff ``exc_info`` was passed
==================  =========================================================

Any ``extra=`` fields are merged in (telemetry), scrubbed by key and content.
These spellings are defined here once — referenced by the tests and recorded
in the WP changelog — so no G-01-style drift can appear between producers.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from .correlation import get_correlation_id
from .scrub import scrub_text, scrub_value

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
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": scrub_text(record.getMessage()),
        }
        correlation_id = get_correlation_id()
        if correlation_id:
            payload["correlation_id"] = correlation_id
        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_ATTRS:
                continue
            payload[key] = scrub_value(key, value)
        if record.exc_info is not None:
            payload["exception"] = scrub_text(self.formatException(record.exc_info))
        return json.dumps(payload, default=str, ensure_ascii=False)
