"""Backend HTTP transport for the API client (parent plan Sections 9.2, 10.1,
10.3, 10.10, 10.11, 12.2; MT-2.3-01).

The raw layer every bridge tool call passes through:

* **Base URL** — the manifest's ``orchestrator_api`` when the client is built
  from a :class:`~orchestrator_bridge.manifest.StartupBinding`
  (:meth:`ApiClient.for_binding`), with ``settings.api_base_url`` as the
  fallback (defensive: the manifest schema requires the key). This resolves the
  precedence WP-2.2 explicitly deferred to WP-2.3 (``manifest.py`` note): the
  per-project binding wins over the process default. Section 9.2 fixes the API
  base path at ``/api/v1``, so catalog paths are origin-absolute
  (``/api/v1/...``) and are joined to the base URL's origin; a path without a
  leading slash is joined relative to the base instead (for path-prefixed
  deployments behind a reverse proxy).
* **Auth** — the project-scoped agent bearer token resolved through
  :func:`~orchestrator_bridge.credentials.require_agent_token` (Section 10.3
  step 3: environment > user config, never the manifest). ``Settings`` stays
  the single holder; the value is read per request and never stored on the
  client, logged, or placed in a URL (Section 12.4).
* **Headers on every request** — ``Authorization``, ``X-Correlation-ID``
  (headers.md honor-or-generate via the correlation scope) and the API version
  header; mutating verbs additionally get ``Idempotency-Key``
  (MT-2.3-03, minted once per logical call before the first attempt), reads
  never do.
* **Version gate** (Section 10.11) — :func:`verify_api_version` reads the
  backend's advertised version at startup and raises
  :class:`~orchestrator_bridge.errors.ApiVersionError` on a mismatch. The
  header *name* is not fixed anywhere in the plan or by WP-1.1 (MT-2.3-01 risk
  note): ``X-API-Version`` with the major version ``1`` is the proposed value
  recorded as an open question in the WP changelog — when the backend starts
  advertising it, an absent header stops being the norm; today absence is
  treated as "unverified", not a mismatch, so startup stays compatible.
* **Envelope parsing** — non-2xx bodies are parsed into the typed
  :class:`~orchestrator_bridge.api_errors.ApiError` (Section 9.2's five fields
  verbatim); unparseable bodies degrade to a ``SERVER_ERROR``-tagged error
  instead of crashing (MT-2.3-01 acceptance). Connection errors and timeouts
  become retryable ``transport_failure`` errors (Section 10.10).
* **Bounds** — ``settings.timeout_seconds`` per request and
  ``settings.max_response_mb`` per response (Section 9.10: named settings with
  documented defaults).

The HTTP boundary is a single injectable seam (:data:`SendFn`): production
uses the stdlib opener, tests inject deterministic fakes. Retry with backoff
(MT-2.3-02) wraps the send inside :meth:`ApiClient.exchange` — headers
(including the ``Idempotency-Key`` of MT-2.3-03) are prepared **once per
logical call**, so every retry re-sends the identical request (ADR-012).
"""

from __future__ import annotations

import json
import random
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from email.message import Message
from typing import Any, Final
from urllib.parse import urlsplit

from .api_errors import ApiError, ErrorCode, ErrorKind
from .config import ConfigError, Settings
from .correlation import CORRELATION_HEADER, get_correlation_id, new_correlation_id
from .credentials import require_agent_token
from .errors import ApiVersionError
from .idempotency import IDEMPOTENCY_HEADER, is_mutating, new_key
from .logging import get_logger
from .manifest import StartupBinding
from .retry import RetryPolicy, retry_call

__all__ = [
    "API_VERSION_HEADER",
    "EXPECTED_API_VERSION",
    "HEALTH_PATH",
    "ApiClient",
    "ApiResponse",
    "SendFn",
    "WireResponse",
    "verify_api_version",
]

#: Proposed Section 10.11 header — no canonical name exists yet (OQ; changelog).
API_VERSION_HEADER: Final = "X-API-Version"
#: The API major this bridge speaks (base path ``/api/v1``, Section 9.2).
EXPECTED_API_VERSION: Final = "1"
#: Cheap, unauthenticated startup probe for the version gate (Section 9.2 Ops).
HEALTH_PATH: Final = "/health/live"

_LOGGER_COMPONENT = "api"


@dataclass(frozen=True, slots=True)
class WireResponse:
    """One raw HTTP exchange at the send seam: status, lower-cased headers, bytes."""

    status: int
    headers: Mapping[str, str]
    body: bytes


@dataclass(frozen=True, slots=True)
class ApiResponse:
    """One parsed exchange: status, lower-cased headers, decoded JSON body."""

    status: int
    headers: Mapping[str, str]
    body: Any


#: The HTTP boundary: ``(method, url, headers, body, timeout_seconds)``.
#: Raises ``OSError``-family exceptions for transport failures (mapped below).
SendFn = Callable[[str, str, Mapping[str, str], bytes | None, float], WireResponse]


class _ResponseTooLarge(Exception):
    """Internal: the response exceeded ``settings.max_response_mb``."""

    def __init__(self, status: int) -> None:
        super().__init__("response too large")
        self.status = status


@dataclass(frozen=True, slots=True)
class _Envelope:
    """A parseable Section 9.2 error envelope (``code`` still unchecked)."""

    code: str
    message: str
    retryable: bool
    details: Mapping[str, Any] | None
    correlation_id: str


def _lower_headers(headers: Message) -> dict[str, str]:
    return {str(name).lower(): str(value) for name, value in headers.items()}


def _read_capped(stream: Any, status: int, limit: int) -> bytes:
    """Read at most *limit* bytes; raise rather than buffer an oversized body."""
    data: bytes = stream.read(limit + 1)
    if len(data) > limit:
        raise _ResponseTooLarge(status)
    return data


def _parse_envelope(body: bytes) -> _Envelope | None:
    """Parse the Section 9.2 envelope; ``None`` for anything not conforming.

    Strict by design (mirrors the schema's required fields): bad JSON, wrong
    nesting, a missing field, a non-boolean ``retryable`` or a non-object
    ``details`` all mean "not a valid envelope" — the caller degrades to the
    ``SERVER_ERROR``-tagged path instead of trusting a half-parsed contract.
    """
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    message = error.get("message")
    retryable = error.get("retryable")
    correlation_id = error.get("correlation_id")
    details = error.get("details")
    if not isinstance(code, str) or not isinstance(message, str):
        return None
    if not isinstance(retryable, bool) or not isinstance(correlation_id, str):
        return None
    if details is not None and not isinstance(details, dict):
        return None
    return _Envelope(
        code=code,
        message=message,
        retryable=retryable,
        details=details,
        correlation_id=correlation_id,
    )


def _status_guesses_retryable(status: int) -> bool:
    """No envelope flag available: 5xx/408/429 can succeed on retry, other 4xx cannot.

    Deliberately mirrors the backend's own rule (its envelope builder marks
    exactly 5xx and ``RATE_LIMITED`` retryable) so a degraded parse never
    widens the retry set beyond what the server would have said.
    """
    return status >= 500 or status in (408, 429)


class ApiClient:
    """Typed HTTP client for the backend's ``/api/v1`` surface (Section 9.2).

    One logical call = :meth:`request` / :meth:`exchange`: headers assembled
    once, retry with backoff around the send (MT-2.3-02; every retry replays
    the identical headers — the ADR-012 pairing MT-2.3-03 completes), uniform
    success/envelope/malformed/transport handling.

    ``sleep`` and ``rng`` are test seams for the retry loop (deterministic,
    no wall-clock waits); ``send`` is the HTTP-boundary seam.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        base_url: str | None = None,
        send: SendFn | None = None,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        raw_base = settings.api_base_url if base_url is None else base_url
        self._base_url = _normalize_base_url(raw_base)
        self._settings = settings
        # Fail fast on a missing/unsafe token before any request (Section 10.3
        # step 3); the value itself stays inside Settings and is re-read per call.
        require_agent_token(settings)
        self._send_fn: SendFn = send if send is not None else self._send_via_urllib
        self._max_response_bytes = int(settings.max_response_mb * 1024 * 1024)
        self._retry = RetryPolicy.from_settings(settings)
        self._sleep = sleep
        self._rng = rng

    @classmethod
    def for_binding(
        cls,
        binding: StartupBinding,
        settings: Settings,
        *,
        send: SendFn | None = None,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> ApiClient:
        """Build the client bound to a validated manifest (Section 10.3).

        The manifest's ``orchestrator_api`` is the per-project authority;
        ``settings.api_base_url`` remains the fallback for the defensive case
        where the key is absent (the schema requires it — WP-2.2 deferral).
        """
        declared = binding.manifest.get("orchestrator_api")
        base_url = declared if isinstance(declared, str) and declared.strip() else None
        return cls(settings, base_url=base_url, send=send, sleep=sleep, rng=rng)

    def __repr__(self) -> str:
        """Debug-safe view — never the token, never a request body (Section 12.4)."""
        return f"ApiClient(base_url={self._base_url!r})"

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """One logical call; returns the decoded JSON body (``None`` for empty)."""
        return self.exchange(method, path, body=body, idempotency_key=idempotency_key).body

    def exchange(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> ApiResponse:
        """One logical call; returns the full :class:`ApiResponse`.

        Raises :class:`ApiError` for every failure shape: parsed envelope
        (verbatim Section 9.2 fields), malformed body (``SERVER_ERROR``-tagged)
        or transport failure (retryable, ``SERVER_ERROR``-tagged). Retryable
        failures are retried per ``settings`` (MT-2.3-02); only the final
        failure is logged and raised. Mutating verbs carry an
        ``Idempotency-Key`` (MT-2.3-03) — minted here, before the first
        attempt, so every retry re-sends the same key (ADR-012); reads never
        carry one. ``idempotency_key`` lets a caller span one logical
        operation across several explicit calls.
        """
        verb = method.upper()
        token = require_agent_token(self._settings)
        url = self._url(path)
        headers: dict[str, str] = {
            "Accept": "application/json",
            # headers.md: honor an installed scope id, generate one otherwise.
            "Authorization": f"Bearer {token}",
            CORRELATION_HEADER: get_correlation_id() or new_correlation_id(),
            API_VERSION_HEADER: EXPECTED_API_VERSION,
        }
        payload: bytes | None = None
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if is_mutating(verb):
            # One logical call → one key; retries replay this exact header.
            headers[IDEMPOTENCY_HEADER] = idempotency_key or new_key(verb, target=path)
        logger = get_logger(_LOGGER_COMPONENT)

        def operation() -> ApiResponse:
            # Headers dict is closed over: every attempt sends identical bytes
            # (the ADR-012 idempotency pairing MT-2.3-03 relies on this).
            try:
                wire = self._send_fn(verb, url, headers, payload, self._settings.timeout_seconds)
            except _ResponseTooLarge as exc:
                raise self._too_large_error(exc, verb, path) from None
            except OSError as exc:
                raise self._transport_error(exc, verb, path) from None
            return self._unwrap(wire, verb, path)

        def note_retry(attempt: int, error: ApiError, delay: float) -> None:
            logger.info(
                "retrying backend call",
                extra={
                    "event": "api_retry",
                    "method": verb,
                    "path": path,
                    "attempt": attempt,
                    "delay_seconds": round(delay, 3),
                    "error_code": str(error.code),
                    "retryable": error.retryable,
                },
            )

        try:
            response = retry_call(
                operation,
                self._retry,
                sleep=self._sleep,
                rng=self._rng,
                on_retry=note_retry,
            )
        except ApiError as exc:
            # Never log headers (Authorization, Idempotency-Key) — fields only.
            logger.error(
                exc.message,
                extra={
                    "event": "api_error",
                    "method": verb,
                    "path": path,
                    "error_code": str(exc.code),
                    "error_kind": str(exc.kind),
                    "status": exc.status_code,
                    "retryable": exc.retryable,
                },
            )
            raise
        logger.info(
            "backend call succeeded",
            extra={
                "event": "api_response",
                "method": verb,
                "path": path,
                "status": response.status,
            },
        )
        return response

    # --- internals -----------------------------------------------------------

    def _url(self, path: str) -> str:
        if path.startswith("/"):
            origin = urlsplit(self._base_url)
            return f"{origin.scheme}://{origin.netloc}{path}"
        return f"{self._base_url}/{path.lstrip('/')}"

    def _send_via_urllib(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> WireResponse:
        """Default send: stdlib opener, HTTP errors returned (not raised)."""
        request = urllib.request.Request(url, data=body, headers=dict(headers), method=method)
        limit = self._max_response_bytes
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return WireResponse(
                    status=response.status,
                    headers=_lower_headers(response.headers),
                    body=_read_capped(response, response.status, limit),
                )
        except urllib.error.HTTPError as exc:
            # Non-2xx is a response, not a transport failure (Section 9.2).
            with exc:
                return WireResponse(
                    status=exc.code,
                    headers=_lower_headers(exc.headers),
                    body=_read_capped(exc, exc.code, limit),
                )

    def _unwrap(self, wire: WireResponse, method: str, path: str) -> ApiResponse:
        if 200 <= wire.status < 300:
            return ApiResponse(
                status=wire.status,
                headers=wire.headers,
                body=self._parse_success_body(wire, method, path),
            )
        raise self._error_from_response(wire, method, path)

    def _parse_success_body(self, wire: WireResponse, method: str, path: str) -> Any:
        if not wire.body:
            return None
        try:
            return json.loads(wire.body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(
                code=ErrorCode.SERVER_ERROR,
                message=f"response body from {method} {path} is not valid JSON",
                retryable=_status_guesses_retryable(wire.status),
                kind=ErrorKind.MALFORMED_RESPONSE,
                details={"reason": "invalid_json"},
                correlation_id=_response_correlation(wire),
                status_code=wire.status,
            ) from None

    def _error_from_response(self, wire: WireResponse, method: str, path: str) -> ApiError:
        envelope = _parse_envelope(wire.body)
        if envelope is None:
            # Degrade, never crash (MT-2.3-01): SERVER_ERROR-tagged, status-based guess.
            return ApiError(
                code=ErrorCode.SERVER_ERROR,
                message=(
                    f"unparseable error response from {method} {path} "
                    f"(HTTP {wire.status}): not a valid Section 9.2 envelope"
                ),
                retryable=_status_guesses_retryable(wire.status),
                kind=ErrorKind.MALFORMED_RESPONSE,
                details={"reason": "invalid_error_envelope", "upstream_body_bytes": len(wire.body)},
                correlation_id=_response_correlation(wire),
                status_code=wire.status,
            )
        try:
            code = ErrorCode(envelope.code)
            details = envelope.details
        except ValueError:
            # Unknown code (newer backend): DoD item 5 forbids emitting it —
            # downgrade to SERVER_ERROR, preserve the upstream value verbatim.
            code = ErrorCode.SERVER_ERROR
            merged = dict(envelope.details) if envelope.details else {}
            merged["upstream_code"] = envelope.code
            details = merged
        return ApiError(
            code=code,
            message=envelope.message,
            retryable=envelope.retryable,
            kind=ErrorKind.ENVELOPE,
            details=details,
            correlation_id=envelope.correlation_id,
            status_code=wire.status,
        )

    def _transport_error(self, exc: OSError, method: str, path: str) -> ApiError:
        return ApiError(
            code=ErrorCode.SERVER_ERROR,
            message=f"transport failure calling {method} {path}: {type(exc).__name__}: {exc}",
            retryable=True,  # Section 10.10: unreachable backend = retryable
            kind=ErrorKind.TRANSPORT_FAILURE,
            details={"reason": type(exc).__name__},
            correlation_id=get_correlation_id() or None,
            status_code=None,
        )

    def _too_large_error(self, exc: _ResponseTooLarge, method: str, path: str) -> ApiError:
        limit = self._max_response_bytes
        return ApiError(
            code=ErrorCode.SERVER_ERROR,
            message=(
                f"response from {method} {path} exceeds the "
                f"{self._settings.max_response_mb:g} MB response cap "
                "(ORCHESTRATOR_BRIDGE_MAX_RESPONSE_MB)"
            ),
            retryable=False,  # same bytes on every attempt — retry cannot help
            kind=ErrorKind.MALFORMED_RESPONSE,
            details={"reason": "response_too_large", "limit_bytes": limit},
            correlation_id=_response_correlation_from_scope(),
            status_code=exc.status,
        )


def _normalize_base_url(value: str) -> str:
    candidate = value.strip().rstrip("/")
    if not candidate.startswith(("http://", "https://")):
        raise ConfigError(f"API base URL must be an http(s):// URL, got {value!r}") from None
    return candidate


def _response_correlation(wire: WireResponse) -> str | None:
    """Prefer the backend's response header, else the local scope, else ``None``."""
    return wire.headers.get(CORRELATION_HEADER.lower()) or _response_correlation_from_scope()


def _response_correlation_from_scope() -> str | None:
    return get_correlation_id() or None


_MAJOR_DIGITS = re.compile(r"\d+")


def _major_version(advertised: str) -> str | None:
    """Major component of an advertised version (``v1``/``1``/``1.4.0`` → ``1``)."""
    digits = _MAJOR_DIGITS.match(advertised.strip().lstrip("vV"))
    return digits.group() if digits else None


def verify_api_version(client: ApiClient) -> str | None:
    """Section 10.11 startup gate: backend and bridge must speak the same API.

    Probes :data:`HEALTH_PATH` through the full transport (auth, correlation
    and version headers attached) and compares the backend's advertised
    ``X-API-Version`` major against :data:`EXPECTED_API_VERSION`:

    * mismatch (or an unparseable advertised value) →
      :class:`~orchestrator_bridge.errors.ApiVersionError` with an actionable
      "upgrade the bridge or the backend" message — the entry point's
      ``BindingError`` handler turns that into a clean startup abort;
    * header absent → the backend does not advertise a version yet (WP-1.1 has
      not settled the name — OQ in the WP changelog): logged as
      ``event=api_version_unverified`` and accepted, not a mismatch;
    * present and compatible → the advertised value is returned.

    Wired into the session-open startup path with MT-2.2-04 (deferred); the
    mismatch behaviour is exercised directly by ``tests/test_transport.py``.
    """
    logger = get_logger(_LOGGER_COMPONENT)
    response = client.exchange("GET", HEALTH_PATH)
    advertised = response.headers.get(API_VERSION_HEADER.lower())
    if advertised is None:
        logger.warning(
            "backend does not advertise the API version header; compatibility unverified",
            extra={
                "event": "api_version_unverified",
                "header": API_VERSION_HEADER,
                "expected": EXPECTED_API_VERSION,
                "path": HEALTH_PATH,
            },
        )
        return None
    if _major_version(advertised) != EXPECTED_API_VERSION:
        raise ApiVersionError(
            f"backend advertises API version {advertised!r} ({API_VERSION_HEADER}) "
            f"but this bridge speaks {EXPECTED_API_VERSION}; upgrade the bridge "
            "or the backend so both run the same API version"
        )
    logger.info(
        "backend API version verified",
        extra={
            "event": "api_version_verified",
            "advertised": advertised,
            "path": HEALTH_PATH,
        },
    )
    return advertised
