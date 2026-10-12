"""Authentication classes resolving the three Section 7.2 token kinds.

MT-1.2-01 ships the owner-session class; MT-1.2-03 adds the bearer class that
covers ``agent`` and ``device`` tokens (wired into
``REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]`` in base.py).

``OwnerSessionAuthentication`` is DRF's session authentication plus the
Section 12.2/FR-SEC-02 binding: a session is only as good as its
``owner_session`` API Token row. Every request re-reads that row, so logout,
expiry and (later) any revocation path take effect on the very next call —
no server-side session store to poison, no cache to invalidate (the
signed-cookie session cannot be revoked by itself; the row is the authority).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import (
    BaseAuthentication,
    SessionAuthentication,
    get_authorization_header,
)
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.request import Request

from apps.accounts.models import ApiToken, Device, TokenKind
from apps.accounts.services.sessions import binding_for_request
from apps.accounts.services.tokens import hash_token, mark_token_used


class OwnerSessionAuthentication(SessionAuthentication):
    """Cookie/bearer session authentication bound to a live token row."""

    def enforce_csrf(self, request: Request) -> None:
        """CSRF failures answer ``AUTH_REQUIRED`` (MT-1.2-01's code set).

        DRF raises ``PermissionDenied`` here, which the envelope handler would
        render as ``ROLE_NOT_PERMITTED`` — wrong semantics for a request that
        merely arrived without the CSRF half of its credentials. Re-raising as
        ``AuthenticationFailed`` yields the canonical 401 ``AUTH_REQUIRED``
        (Sections 9.2, 20.4 item 5).
        """
        try:
            super().enforce_csrf(request)
        except PermissionDenied as exc:
            raise AuthenticationFailed("CSRF token missing or incorrect.") from exc

    def authenticate(self, request: Request) -> tuple[Any, ApiToken] | None:
        """Resolve (user, owner_session row); reject unbound/dead sessions."""
        result = super().authenticate(request)
        if result is None:
            return None
        user, _ = result
        binding = binding_for_request(request._request)
        if binding is None:
            # A session with no binding predates this login flow or was built
            # outside it — treat as unauthenticated rather than trust it.
            raise AuthenticationFailed("Session has no owner_session token bound.")
        token = ApiToken.objects.filter(
            kind=TokenKind.OWNER_SESSION, hash=hash_token(binding)
        ).first()
        if token is None or not token.is_valid():
            # Revoked or expired (or never issued): fail closed, every request,
            # with no cache lag — WP-1.2 acceptance half.
            raise AuthenticationFailed("Session token is revoked or expired.")
        mark_token_used(token)
        return user, token


# drf-spectacular's extension hook is typed-less at the __init_subclass__
# boundary (py.typed package, one untyped method) — same ignore style as
# config/urls.py uses for the same package.
class OwnerSessionAuthenticationExtension(  # type: ignore[no-untyped-call]
    OpenApiAuthenticationExtension
):
    """Describe the owner session as cookie security in the OpenAPI contract.

    ADR-005/NFR-11: the generated document must show *how* a client
    authenticates, not just that some class ran. Web clients send the
    HTTP-only ``sessionid`` cookie (plus ``X-CSRFToken`` for mutations);
    token-auth clients (Section 15.4) send ``Authorization: Bearer`` with the
    same session token — the bearer scheme is declared by MT-1.2-03's
    extension for the shared token classes.
    """

    target_class = "apps.accounts.authentication.OwnerSessionAuthentication"
    name = "sessionAuth"

    def get_security_definition(self, auto_schema: Any) -> dict[str, Any]:
        """Cookie security scheme bound to Django's session cookie name."""
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.SESSION_COOKIE_NAME,
            "description": (
                "Owner session cookie issued by POST /api/v1/auth/login "
                "(HTTP-only; mutations also require the X-CSRFToken header "
                "duplicated from the csrftoken cookie)."
            ),
        }


class TokenBearerAuthentication(BaseAuthentication):
    """``Authorization: Bearer <token>`` for agent/device tokens (MT-1.2-03).

    Covers every Section 7.2 kind by hashing the presented credential and
    looking the row up — the same stored representation as the owner session,
    so revocation (``revoked_at``/``expires_at``) takes effect on the very
    next request on both transports (FR-SEC-02; no cache — risk note of
    MT-1.2-03). Project scope is *not* checked here: ADR-004's guard resolves
    the addressed project inside permission checks (MT-1.2-05, Section 9.3
    step 1) so every agent-facing endpoint shares one enforcement point.

    An owner session token presented as a bearer authenticates too — the
    Section 15.4 token-auth transport for mobile clients; ``IsOwnerSession``
    then applies exactly as for the cookie transport.
    """

    keyword = "Bearer"

    def authenticate(self, request: Request) -> tuple[Any, ApiToken] | None:
        """Resolve a bearer credential to a live token row, or pass on."""
        auth = get_authorization_header(request).split()
        if not auth:
            return None
        if auth[0].lower() != self.keyword.lower().encode():
            # Some other scheme (none is defined by the plan) — pass through
            # to the next authenticator instead of inventing an error.
            return None
        if len(auth) != 2:
            raise AuthenticationFailed("Invalid bearer credential header.")
        try:
            credentials = auth[1].decode("ascii")
        except UnicodeDecodeError as exc:
            raise AuthenticationFailed("Bearer credential must be ASCII.") from exc
        token = ApiToken.objects.filter(hash=hash_token(credentials)).first()
        if token is None or not token.is_valid():
            # Unknown, revoked or expired: fail closed (AUTH_REQUIRED via the
            # exception map; WP-1.2 acceptance "revoked tokens fail
            # immediately").
            raise AuthenticationFailed("Token is invalid, revoked or expired.")
        if token.kind == TokenKind.DEVICE:
            # The Device row is the second half of the lost-phone control
            # (Section 12.2; ADR-006): registration/revocation always move
            # both rows together, so a device-bound credential without a live
            # device cannot authenticate — belt against any partial state.
            device = Device.objects.filter(token=token).select_related("token").first()
            if device is None or not device.is_active():
                raise AuthenticationFailed("Device is revoked or unknown.")
            # Section 7.2 hygiene: show the phone was seen recently.
            device.last_seen_at = timezone.now()
            device.save(update_fields=["last_seen_at"])
        mark_token_used(token)
        return token.user, token

    def authenticate_header(self, request: Request) -> str | None:
        """Advertise the scheme on 401 responses (RFC-style challenge)."""
        return self.keyword


class TokenBearerAuthenticationExtension(  # type: ignore[no-untyped-call]
    OpenApiAuthenticationExtension
):
    """Declare the bearer scheme in the OpenAPI contract (ADR-005; NFR-11)."""

    target_class = "apps.accounts.authentication.TokenBearerAuthentication"
    name = "bearerAuth"

    def get_security_definition(self, auto_schema: Any) -> dict[str, Any]:
        """Opaque bearer scheme — never a JWT (plaintext shown once, 7.2)."""
        return {
            "type": "http",
            "scheme": "bearer",
            "description": (
                "Project-scoped agent token (or owner session token in the "
                "Section 15.4 token-auth transport) issued by "
                "POST /api/v1/tokens/agent or /auth/login. The server stores "
                "only its SHA-256 hash; the plaintext is shown exactly once."
            ),
        }
