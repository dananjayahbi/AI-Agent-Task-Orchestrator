"""Worker-side FCM sender (Section 9.8; ADR-003; WP-5.4's MT-5.4-01).

Push never leaves the web process or an end-user device (Section 9.8):
the Celery worker (ADR-003) sends. This module is the delivery loop the
later MTs build on — payload minimization (MT-5.4-02), per-device
dedupe (MT-5.4-03), delivery tracking and token pruning (MT-5.4-04),
preferences (MT-5.4-05) all sit *around* this sender, never inside it.

Three seams, one responsibility each:

* **Transport** — :class:`FcmTransport` is the narrow protocol the
  retry loop talks to; :class:`FirebaseAdminTransport` is the recorded
  dependency pick (``firebase-admin`` 7.x, the official Admin SDK —
  Section 20.1 item 5: the choice is recorded here and in the WP
  changelog). Tests inject a mocked transport; the production default
  is built lazily from the Section 9.10 ``FCM_`` settings so the unit
  suite never needs credentials.
* **Retry/backoff** — Section 9.9's push job is "on event | Dedupe +
  retry": :func:`send_to_token` retries *transient* failures with
  exponential backoff (``base × 2^(n-1)``, the attachment pipeline's
  MT-1.12-07 shape) and stops dead on *permanent* ones. The dedupe
  decision itself is MT-5.4-03's and lives outside this loop.
* **Failure classification** — :func:`classify_fcm_error` is the
  explicit table from FCM's documented error codes to the transient /
  permanent split, with the *invalid-token* subset marked for
  MT-5.4-04's pruning. Misclassifying a transient as permanent
  silently drops a working device (MT-5.4-04 risk note), so unknown
  codes fail **transient** — retried, never pruned on ambiguity.

Latency posture (NFR-03): this loop is the critical path *inside* the
worker job — no batching, no sleeps except the retry backoff, so an
accepted first attempt returns in one network round-trip.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

#: FCM error codes that mean *this token is dead* (uninstalled app,
#: expired token, malformed token). MT-5.4-04 prunes exactly this set;
#: everything else permanent leaves the device row alone.
INVALID_TOKEN_ERROR_CODES: frozenset[str] = frozenset(
    {"UNREGISTERED", "INVALID_ARGUMENT", "SENDER_ID_MISMATCH"}
)

#: FCM error codes that are transient by the transport's documentation:
#: retry with backoff, never prune (Section 9.9 "Dedupe + retry").
TRANSIENT_ERROR_CODES: frozenset[str] = frozenset(
    {"UNAVAILABLE", "INTERNAL", "QUOTA_EXCEEDED", "TIMEOUT"}
)


class SendOutcome:
    """The three-valued result of one send loop (MT-5.4-04's vocabulary)."""

    ACCEPTED = "accepted"
    TRANSIENT_FAILURE = "transient_failure"
    PERMANENT_FAILURE = "permanent_failure"


class FcmTransportError(Exception):
    """One transport-level send failure, classified at the raise site.

    ``code`` is FCM's documented error code (``UNREGISTERED`` and kin);
    ``transient`` is the retry loop's binary decision. ``invalid_token``
    marks the MT-5.4-04 pruning subset of permanents.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str | None,
        transient: bool,
        invalid_token: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.transient = transient
        self.invalid_token = invalid_token


def classify_fcm_error(error_code: str | None) -> tuple[bool, bool]:
    """Map one FCM error code to ``(transient, invalid_token)``.

    The explicit classification table (MT-5.4-04 risk note): known
    transient codes retry, the documented invalid-token codes are
    permanent **and** prune-worthy, and an unknown or absent code is
    treated as transient — ambiguity must never destroy a working
    device token, it may only cost a bounded retry.
    """
    if error_code in INVALID_TOKEN_ERROR_CODES:
        return False, True
    if error_code in TRANSIENT_ERROR_CODES:
        return True, False
    # Unknown code: retry the ambiguity, never prune on it.
    return True, False


@runtime_checkable
class FcmTransport(Protocol):
    """The seam below the sender: one token, one data map, one attempt."""

    def send(self, device_token: str, data: Mapping[str, str]) -> None:
        """Deliver one message; raise :class:`FcmTransportError` on failure."""
        ...


class FirebaseAdminTransport:
    """The production transport — ``firebase-admin``'s FCM v1 API.

    The dependency pick this WP records (risk note: "Choosing the FCM
    client library/transport is a dependency decision — record the
    pick"): ``firebase-admin`` is Google's official Admin SDK, pinned
    in ``pyproject.toml``, and only ever imported when a send is
    actually configured — the unit suite and push-disabled deployments
    never touch it.
    """

    def __init__(self, *, project_id: str, credentials_json: str) -> None:
        """Initialize the default app once per process (lazily imported)."""
        from firebase_admin import (  # noqa: PLC0415
            App,
            credentials,
            get_app,  # noqa: PLC0415
            initialize_app,
        )

        try:
            app: App = get_app()
        except ValueError:
            cert = credentials.Certificate(json.loads(credentials_json))
            app = initialize_app(cert, options={"projectId": project_id})
        self._app = app

    def send(self, device_token: str, data: Mapping[str, str]) -> None:
        """One FCM v1 send; classify failures into ``FcmTransportError``."""
        from firebase_admin import exceptions as fb_exceptions  # noqa: PLC0415
        from firebase_admin import messaging  # noqa: PLC0415

        message = messaging.Message(
            data=dict(data),
            token=device_token,
            notification=messaging.Notification(  # OS banner: ids + title only
                title=data.get("title", ""),
            ),
        )
        try:
            messaging.send(message, app=self._app)
        except fb_exceptions.NotFoundError as exc:  # UNREGISTERED
            raise FcmTransportError(
                str(exc), code="UNREGISTERED", transient=False, invalid_token=True
            ) from exc
        except fb_exceptions.InvalidArgumentError as exc:  # malformed token/payload
            raise FcmTransportError(
                str(exc), code="INVALID_ARGUMENT", transient=False, invalid_token=True
            ) from exc
        except fb_exceptions.UnauthenticatedError as exc:
            raise FcmTransportError(
                str(exc), code="THIRD_PARTY_AUTH_ERROR", transient=False
            ) from exc
        except fb_exceptions.TooManyRequestsError as exc:
            raise FcmTransportError(str(exc), code="QUOTA_EXCEEDED", transient=True) from exc
        except fb_exceptions.UnavailableError as exc:
            raise FcmTransportError(str(exc), code="UNAVAILABLE", transient=True) from exc
        except fb_exceptions.FirebaseError as exc:
            code = getattr(exc, "code", None)
            transient, invalid_token = classify_fcm_error(code)
            raise FcmTransportError(
                str(exc), code=code, transient=transient, invalid_token=invalid_token
            ) from exc


# --- the process-default transport seam -------------------------------------

_default_transport: FcmTransport | None = None


def set_fcm_transport(transport: FcmTransport | None) -> None:
    """Install (or remove) the process-default transport (test seam)."""
    global _default_transport
    _default_transport = transport


def get_fcm_transport() -> FcmTransport:
    """The process-default transport, built from settings on first use.

    Fail-fast at the point of use (Section 9.10, the OCR-engine
    precedent): a send attempted without a configured transport — e.g.
    push enabled without credentials ever reaching this process — is a
    configuration error, never a silent drop.
    """
    if _default_transport is not None:
        return _default_transport
    if not settings.PUSH_ENABLED:
        raise ImproperlyConfigured(
            "push dispatch is disabled (ORCHESTRATOR_PUSH_ENABLED=false) — "
            "no FCM transport is available (WP-5.4 configuration contract)."
        )
    return FirebaseAdminTransport(
        project_id=settings.FCM_PROJECT_ID,
        credentials_json=settings.FCM_CREDENTIALS_JSON,
    )


# --- the retrying sender -----------------------------------------------------


@dataclass(frozen=True)
class SendResult:
    """One token's send-loop outcome (the job's per-device verdict)."""

    outcome: str  # SendOutcome.* — accepted / transient_failure / permanent_failure
    attempts: int
    error_code: str | None = None
    invalid_token: bool = False


def send_to_token(
    device_token: str,
    data: Mapping[str, str],
    *,
    transport: FcmTransport | None = None,
    max_attempts: int | None = None,
    backoff_seconds: int | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> SendResult:
    """Send *data* to one device token with transient-failure retry.

    Section 9.9's "Dedupe + retry" half: transient failures back off
    ``base × 2^(n-1)`` up to ``max_attempts`` (Section 9.10
    ``ORCHESTRATOR_PUSH_RETRY_*`` defaults); permanent failures return
    immediately — retrying a permanent error can never succeed and only
    inflates the NFR-03 latency window. ``sleep`` is injectable so the
    unit suite asserts the backoff schedule without waiting on it.
    """
    transport = transport if transport is not None else get_fcm_transport()
    attempts_budget = max_attempts if max_attempts is not None else settings.PUSH_RETRY_MAX_ATTEMPTS
    backoff_base = (
        backoff_seconds if backoff_seconds is not None else settings.PUSH_RETRY_BACKOFF_SECONDS
    )
    attempts = 0
    while True:
        attempts += 1
        try:
            transport.send(device_token, data)
            return SendResult(outcome=SendOutcome.ACCEPTED, attempts=attempts)
        except FcmTransportError as exc:
            if not exc.transient:
                return SendResult(
                    outcome=SendOutcome.PERMANENT_FAILURE,
                    attempts=attempts,
                    error_code=exc.code,
                    invalid_token=exc.invalid_token,
                )
            if attempts >= attempts_budget:
                return SendResult(
                    outcome=SendOutcome.TRANSIENT_FAILURE,
                    attempts=attempts,
                    error_code=exc.code,
                )
            sleep(backoff_base * 2 ** (attempts - 1))


__all__ = [
    "FirebaseAdminTransport",
    "FcmTransport",
    "FcmTransportError",
    "INVALID_TOKEN_ERROR_CODES",
    "SendOutcome",
    "SendResult",
    "TRANSIENT_ERROR_CODES",
    "classify_fcm_error",
    "get_fcm_transport",
    "send_to_token",
    "set_fcm_transport",
]
