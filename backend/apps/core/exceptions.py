"""DRF exception handler rendering the Section 9.2 error envelope.

Wired via ``REST_FRAMEWORK["EXCEPTION_HANDLER"]``. Responsibilities:

* every non-2xx produced by an API view uses the envelope built in
  ``apps.core.errors`` — exactly five fields, a **catalog** code only
  (Section 20.4, item 5), scrubbed ``message``/``details`` (Sections 17,
  12.4), and this request's ``correlation_id`` (headers.md);
* ``retryable`` follows one documented rule: ``true`` for 5xx and
  ``RATE_LIMITED`` (a retry can succeed), ``false`` otherwise;
* exceptions whose ``default_code`` is already a canonical code pass through
  unchanged, so later work packages emit catalog codes simply by setting
  ``default_code`` on their own ``APIException`` subclasses.

Known mapping limits are deliberate and commented: the catalog has no generic
404/405 code, so DRF's generic ``NotFound``/``MethodNotAllowed`` fall back to
``VALIDATION_ERROR`` — **both in code and in HTTP status** (400, the status
the OpenAPI contract declares for that mapping; a client switching on the
``code``+status pair must see exactly what the document promises). Resource-
owning work packages raise their specific code (e.g. ``TASK_NOT_FOUND``)
from their own exceptions and keep their own status.
"""

from __future__ import annotations

import logging
from typing import Any

from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    ParseError,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .correlation import get_correlation_id
from .errors import (
    AUTH_REQUIRED,
    RATE_LIMITED,
    ROLE_NOT_PERMITTED,
    SERVER_ERROR,
    VALIDATION_ERROR,
    build_error_envelope,
    is_canonical_code,
)

logger = logging.getLogger(__name__)

# Exact DRF exception classes whose canonical code is known today (Section 9.2).
# WP-1.2+ permission classes raise their own exceptions with canonical
# default_codes (AUTH_FORBIDDEN_PROJECT, SCOPE_VIOLATION, …), which flow via
# the is_canonical_code path below rather than this map.
_CODE_BY_EXCEPTION_TYPE: dict[type[Exception], str] = {
    ParseError: VALIDATION_ERROR,
    ValidationError: VALIDATION_ERROR,
    NotAuthenticated: AUTH_REQUIRED,
    AuthenticationFailed: AUTH_REQUIRED,
    PermissionDenied: ROLE_NOT_PERMITTED,
    NotFound: VALIDATION_ERROR,  # no generic 404 code exists in the catalog
    MethodNotAllowed: VALIDATION_ERROR,  # no generic 405 code exists either
    Throttled: RATE_LIMITED,
}

# The status half of the two "no code exists" mappings above: VALIDATION_ERROR
# is a 400 in the documented contract (the views' extend_schema declares 400,
# never 404/405), so a generic NotFound/MethodNotAllowed answers 400 with the
# envelope — status and code stay the pair the OpenAPI snapshot promises.
_STATUS_BY_EXCEPTION_TYPE: dict[type[Exception], int] = {
    NotFound: status.HTTP_400_BAD_REQUEST,
    MethodNotAllowed: status.HTTP_400_BAD_REQUEST,
}


def _resolve_code(exc: Exception, http_status: int) -> str:
    """Pick a canonical code for *exc*: explicit map, then default_code, then status."""
    mapped = _CODE_BY_EXCEPTION_TYPE.get(type(exc))
    if mapped is not None:
        return mapped
    default_code = getattr(exc, "default_code", "")
    if isinstance(default_code, str) and is_canonical_code(default_code):
        return default_code
    if http_status >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        return SERVER_ERROR
    return VALIDATION_ERROR


def _is_retryable(http_status: int, code: str) -> bool:
    """Retry rule: 5xx and RATE_LIMITED can succeed on retry; other 4xx cannot."""
    return http_status >= status.HTTP_500_INTERNAL_SERVER_ERROR or code == RATE_LIMITED


def _plain_details(exc: Exception) -> dict[str, object]:
    """Structured context for the envelope, or ``{}`` when the exception has none."""
    detail = getattr(exc, "detail", None)
    if detail is None:
        return {}
    try:
        return dict({"detail": detail}) if not isinstance(detail, dict) else dict(detail)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return {}


def orchestrator_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Convert any API-view exception into a Section 9.2 envelope response."""
    response = drf_exception_handler(exc, context)
    if response is None:
        # Not a DRF API exception (programming/data error). Log it with the
        # traceback, then still answer with the envelope contract — a generic
        # HTML/leaky 500 must never bypass the documented wire format.
        logger.exception("unhandled exception in API view", exc_info=exc)
        http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
        code = SERVER_ERROR
        message = "Internal server error."
        details: dict[str, object] = {}
        headers: dict[str, str] = {}
    else:
        http_status = _STATUS_BY_EXCEPTION_TYPE.get(type(exc), response.status_code)
        code = _resolve_code(exc, http_status)
        message = str(exc) or response.status_text
        details = _plain_details(exc)
        headers = dict(response.headers)

    envelope = build_error_envelope(
        code=code,
        message=message,
        retryable=_is_retryable(http_status, code),
        details=details,
        correlation_id=get_correlation_id(),
    )
    return Response(envelope, status=http_status, headers=headers)
