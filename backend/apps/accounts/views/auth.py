"""Owner session endpoints: POST /auth/login, /auth/logout, /auth/refresh.

Section 9.2 Auth row (caller Owner) driven exactly as Section 12.2 specifies:
username/password login into a CSRF-protected, secure HTTP-only cookie
session, recorded as a revocable ``owner_session`` API Token (hashed at rest),
revoked immediately by logout, extended only while alive by refresh.

Failure discipline (MT-1.2-01 scope): only Section 9.2 catalog codes —
``AUTH_REQUIRED`` (bad credentials, missing/dead session, missing CSRF),
``VALIDATION_ERROR`` (malformed body), ``RATE_LIMITED`` if these endpoints are
ever throttled (they are not: FR-SEC-05 scopes rate limiting to agent and
device endpoints — MT-1.2-06).
"""

from __future__ import annotations

from typing import Any, cast

from django.contrib.auth import authenticate
from django.middleware.csrf import get_token
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import ErrorEnvelopeSerializer

from ..exceptions import AuthRequired
from ..models import ApiToken, User
from ..permissions import IsOwnerSession
from ..serializers.auth import (
    LoginRequestSerializer,
    OwnerSessionSerializer,
    RefreshedSerializer,
    RevokedSerializer,
)
from ..services.sessions import end_owner_session, refresh_owner_session, start_owner_session


class LoginView(APIView):
    """POST /auth/login — exchange owner credentials for a live session.

    Unauthenticated by definition (``authentication_classes = []``): the
    request *creates* the session rather than presenting one. CSRF protection
    still applies where it matters — every session-authenticated mutation after
    login is CSRF-checked by ``OwnerSessionAuthentication`` — and the response
    marks the csrftoken cookie for delivery (Section 12.2; the web client
    echoes it back as ``X-CSRFToken``).
    """

    authentication_classes: list[Any] = []
    permission_classes: list[Any] = [AllowAny]

    @extend_schema(
        request=LoginRequestSerializer,
        responses={
            status.HTTP_200_OK: OwnerSessionSerializer,
            status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
            status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Verify credentials, start the session, return the binding once."""
        input_serializer = LoginRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        authenticated = authenticate(
            request._request,
            username=input_serializer.validated_data["username"],
            password=input_serializer.validated_data["password"],
        )
        # None covers both unknown user and bad password — one message so the
        # endpoint cannot be used to enumerate accounts. Inactive accounts are
        # rejected inside authenticate() as well. AuthRequired (not DRF's
        # AuthenticationFailed): with `authentication_classes = []` this view
        # cannot emit a WWW-Authenticate challenge, so DRF would coerce the
        # built-in exception down to 403 — the envelope contract here is the
        # 401 AUTH_REQUIRED (MT-1.2-01; Section 9.2).
        if authenticated is None:
            # MT-6.4-02: Section 15.3 layer-4 anomaly signal — one failed
            # login attempt counted (hashed source, fixed window). The
            # counter is read by the repeated-auth-failures alert; nothing
            # else changes here.
            from apps.core.alerts import record_auth_failure

            record_auth_failure(request._request.META.get("REMOTE_ADDR", "unknown"))
            raise AuthRequired("Invalid username or password.")
        if not isinstance(authenticated, User):  # pragma: no cover - defensive
            raise AuthRequired("Invalid username or password.")

        token, binding = start_owner_session(request._request, authenticated)
        # Side effect (documented Django behaviour): the CsrfViewMiddleware
        # adds the csrftoken cookie to this response.
        get_token(request._request)
        return Response(
            {
                "token": binding,
                "expires_at": token.expires_at,
                "user": {"id": authenticated.pk, "username": authenticated.username},
            }
        )


class LogoutView(APIView):
    """POST /auth/logout — revoke the current session token immediately.

    The response's ``revoked_at`` is the instant the credential stopped
    working; the very next authenticated request fails with ``AUTH_REQUIRED``
    on both transports (cookie and bearer) because each one re-reads the same
    row (FR-SEC-02; WP-1.2 acceptance "revoked tokens fail immediately").
    """

    permission_classes: list[Any] = [IsOwnerSession]

    @extend_schema(
        request=None,
        responses={
            status.HTTP_200_OK: RevokedSerializer,
            status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
            status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Revoke the caller's ``owner_session`` row and flush its session."""
        token = cast(ApiToken, request.auth)  # guaranteed by IsOwnerSession
        revoked_at = end_owner_session(request._request, token)
        return Response({"revoked_at": revoked_at})


class RefreshView(APIView):
    """POST /auth/refresh — extend a *live* session's lifetime.

    Authentication runs before this view: a revoked or expired session token
    never reaches it — it fails with ``AUTH_REQUIRED`` instead of being
    resurrected (MT-1.2-01 acceptance).
    """

    permission_classes: list[Any] = [IsOwnerSession]

    @extend_schema(
        request=None,
        responses={
            status.HTTP_200_OK: RefreshedSerializer,
            status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
            status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Push expiry forward by the Section 9.10 lifetime; return it."""
        token = cast(ApiToken, request.auth)  # guaranteed by IsOwnerSession
        expires_at = refresh_owner_session(request._request, token)
        return Response({"expires_at": expires_at})
