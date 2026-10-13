"""Wire replies for the local HTTP service (Section 9.2 envelope; Section 10.5).

Every non-2xx answer this service produces is the standard Section 9.2 error
envelope — exactly the five published fields (``docs/plan/conventions/
error-envelope.md`` rule 5: no invented fields) with only catalog codes
(rule 4). The Section 10.5 *hint* and *next action* the MTs require when the
error is surfaced to the client ride inside ``details`` (structured context),
never as extra top-level keys.

The happy paths (``/health`` and anything the MCP session manager answers)
use :func:`send_json` / pass the ASGI stream straight through.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from ..api_errors import ErrorCode
from ..correlation import get_correlation_id, new_correlation_id

__all__ = ["error_payload", "send_error", "send_json"]

_JSON_HEADERS: list[tuple[bytes, bytes]] = [
    (b"content-type", b"application/json"),
]


def error_payload(
    code: ErrorCode,
    message: str,
    *,
    retryable: bool = False,
    details: Mapping[str, Any] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """One Section 9.2 envelope body (the five published fields, verbatim)."""
    return {
        "error": {
            "code": str(code),
            "message": message,
            "retryable": retryable,
            "details": dict(details) if details is not None else None,
            "correlation_id": correlation_id or get_correlation_id() or new_correlation_id(),
        }
    }


async def send_json(send: Any, status: int, payload: Mapping[str, Any]) -> None:
    """Write one complete JSON HTTP response on an ASGI ``send`` callable."""
    body = json.dumps(payload).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [*_JSON_HEADERS, (b"content-length", str(len(body)).encode("ascii"))],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def send_error(
    send: Any,
    status: int,
    code: ErrorCode,
    message: str,
    *,
    retryable: bool = False,
    details: Mapping[str, Any] | None = None,
) -> None:
    """Write one catalog-coded Section 9.2 envelope as an HTTP response.

    Never raises on a double start (a response already in flight when a late
    failure is discovered): the transport-level problem is for the socket, not
    for a second, protocol-breaking reply.
    """
    payload = error_payload(code, message, retryable=retryable, details=details)
    try:
        await send_json(send, status, payload)
    except RuntimeError:  # response already started — nothing left to say
        pass
