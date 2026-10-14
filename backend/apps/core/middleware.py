"""Request-scope middleware: correlation id and structured request logs (17).

Order matters and is defined once in settings ``MIDDLEWARE``:

1. ``CorrelationIdMiddleware`` — installs the id for the whole scope (first
   among the two, so everything below it logs with the id);
2. ``RequestLoggingMiddleware`` — emits one structured JSON line per request
   after the inner chain completes, still inside the id's scope.

Per headers.md, the id is honored when the canonical header is present and
generated when absent, is stable across the whole request, is echoed on the
response, and appears in every log line of the scope.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from .correlation import (
    CORRELATION_HEADER,
    reset_correlation_id,
    resolve_incoming_id,
    set_correlation_id,
)

logger = logging.getLogger(__name__)

GetResponse = Callable[[HttpRequest], HttpResponse]


class CorrelationIdMiddleware:
    """Honor-or-generate ``X-Correlation-ID`` for one request scope (MT-0.5-03)."""

    def __init__(self, get_response: GetResponse) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = resolve_incoming_id(request.headers.get(CORRELATION_HEADER, ""))
        token = set_correlation_id(correlation_id)
        try:
            response = self.get_response(request)
        finally:
            reset_correlation_id(token)
        response[CORRELATION_HEADER] = correlation_id
        return response


class RequestLoggingMiddleware:
    """Emit one structured JSON line per completed request (Section 17).

    Also records Section 17 ``api_latency`` (WP-6.4): the label is the URL
    resolver's route pattern, not the raw path, so no task id leaks and
    cardinality stays bounded.
    """

    def __init__(self, get_response: GetResponse) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.get_full_path(),
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        from .metrics import record_api_latency

        record_api_latency(
            method=request.method or "UNSPEC",
            route=_resolved_route(request),
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response


def _resolved_route(request: HttpRequest) -> str:
    """URL resolver's route pattern (e.g. ``api/v1/tasks/<id>/claim``).

    Falls back to ``unmatched`` when no resolver matched (a 404 before routing),
    keeping the label bounded and free of the raw path.
    """
    match = getattr(request, "resolver_match", None)
    if match is None or not getattr(match, "route", None):
        return "unmatched"
    return str(match.route)
