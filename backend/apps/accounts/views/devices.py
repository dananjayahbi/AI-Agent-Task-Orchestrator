"""Device endpoints: POST /devices, DELETE /devices/{id} (Section 9.2).

WP-1.2 built the Section 9.2 Devices row; WP-5.3's MT-5.3-01 verifies and
hardens it per the micro-task scope: registration now honors the Section 9.2
rule that *all mutating endpoints accept an idempotency key header*
(headers.md; ADR-012) — a retried ``POST /devices`` carrying the same
``Idempotency-Key`` replays the original outcome instead of minting a second
Device + token pair. Everything else the MT asks to verify was already true
and stays covered by ``tests/test_device_registration.py`` (WP-1.2):
canonical catalog errors, closed platform vocabulary, hashed-only storage.
The audit-event half is deferred — see the WP changelog (the MT-1.9-02
helper does not exist yet and the Section 9.6 catalog has no device/token
type; inventing either is out of bounds).

Caller column says **Mobile**, but the credential for both operations is the
owner's — Section 12.2: "device registration after Owner login". The mobile
app presents the owner session (cookie transport on the emulator, bearer
transport of the same session token per Section 15.4), so ``IsOwnerSession``
is the correct guard on both and an agent token is the wrong role
(``ROLE_NOT_PERMITTED``) while anonymous callers get ``AUTH_REQUIRED``.

Revocation is the lost-phone control: one DELETE revokes the Device **and**
its API Token in a single transaction, and authentication re-reads both rows
per request, so access stops on the very next call (no cache; ADR-006).
DELETE needs no replay store: it is idempotent by construction (repeat
returns the original ``revoked_at``), the behavior WP-1.2 already tests.
"""

from __future__ import annotations

from typing import Any, cast

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.idempotency import (
    idempotency_key_of,
    lookup_replay,
    request_fingerprint,
    store_outcome,
)
from apps.core.serializers import ErrorEnvelopeSerializer
from apps.core.throttling import DeviceEndpointThrottle

from ..models import Device, User
from ..permissions import IsOwnerSession
from ..serializers.auth import RevokedSerializer
from ..serializers.devices import (
    DeviceRegisterRequestSerializer,
    DeviceRegisterResponseSerializer,
)
from ..services.devices import register_device, revoke_device

# The canonical idempotency header (Section 9.2: all mutating endpoints
# accept it; one spelling, never an alias — headers.md).
_IDEMPOTENCY_PARAMETER = OpenApiParameter(
    name="Idempotency-Key",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=False,
    description=(
        "Caller-derived key making retries safe (ADR-012; NFR-12). Reusing "
        "the key with the same request replays the original 201 outcome — "
        "the same device id and token material — instead of registering a "
        "second device; reuse with a different request is an open point "
        "(headers.md) and executes normally."
    ),
)


def _replay_or_none(request: Request) -> Response | None:
    """A stored same-request outcome for this ``Idempotency-Key``, if any."""
    key = idempotency_key_of(request)
    if key is None:
        return None
    replay = lookup_replay(request, key, request_fingerprint(request, request.data))
    if replay is None:
        return None
    return Response(replay["body"], status=replay["status"])


def _store_outcome(request: Request, response: Response) -> None:
    """Record a successful outcome under this key (2xx only, inside the store)."""
    key = idempotency_key_of(request)
    if key is None:
        return
    store_outcome(
        request,
        key,
        request_fingerprint(request, request.data),
        status=response.status_code,
        body=response.data,
    )


class DeviceRegisterView(APIView):
    """POST /devices — register a phone after Owner login (Section 12.2).

    Throttled per FR-SEC-05 (MT-1.2-06): the Devices row's caller is Mobile,
    so both device endpoints carry ``DeviceEndpointThrottle`` — agent-facing
    endpoints add ``AgentEndpointThrottle`` as they land (the coverage test
    in ``tests/test_rate_limiting.py`` enumerates them).
    """

    permission_classes: list[Any] = [IsOwnerSession]
    throttle_classes: list[Any] = [DeviceEndpointThrottle]

    @extend_schema(
        request=DeviceRegisterRequestSerializer,
        responses={
            status.HTTP_201_CREATED: DeviceRegisterResponseSerializer,
            status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
            status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
            status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
            status.HTTP_429_TOO_MANY_REQUESTS: ErrorEnvelopeSerializer,
        },
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "Register a device after Owner login (Section 9.2 Devices row; "
            "Section 12.2). Creates the Device row and its `kind = device` "
            "API Token atomically; the plaintext `token` is returned exactly "
            "once — store it in platform secure storage (Section 12.2). "
            "`Idempotency-Key` replays a retried registration instead of "
            "duplicating the device (ADR-012)."
        ),
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Create Device + device token atomically; plaintext returned once."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        input_serializer = DeviceRegisterRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated = input_serializer.validated_data

        user = cast(User, request.user)  # guaranteed by IsOwnerSession
        device, plaintext = register_device(
            user=user,
            platform=validated["platform"],
            push_token=validated["push_token"],
            biometric_bound=validated.get("biometric_bound", False),
        )
        response = Response(
            {
                "id": device.pk,
                "platform": device.platform,
                "biometric_bound": device.biometric_bound,
                "expires_at": device.token.expires_at,
                "token": plaintext,
            },
            status=status.HTTP_201_CREATED,
        )
        _store_outcome(request, response)
        return response


class DeviceRevokeView(APIView):
    """DELETE /devices/{id} — revoke device **and** token together.

    Idempotent (repeat returns the original ``revoked_at``); unknown and
    foreign ids answer identically (``NotFound`` → documented
    ``VALIDATION_ERROR`` mapping — no generic 404 code, no probing).
    Throttled with its sibling per FR-SEC-05 (MT-1.2-06).
    """

    permission_classes: list[Any] = [IsOwnerSession]
    throttle_classes: list[Any] = [DeviceEndpointThrottle]

    @extend_schema(
        responses={
            status.HTTP_200_OK: RevokedSerializer,
            status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
            status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
            status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
            status.HTTP_429_TOO_MANY_REQUESTS: ErrorEnvelopeSerializer,
        },
    )
    def delete(self, request: Request, pk: int, *args: Any, **kwargs: Any) -> Response:
        """Revoke one of the caller's devices (immediate on both rows)."""
        device = Device.objects.filter(pk=pk, user=cast(User, request.user)).first()
        if device is None:
            raise NotFound("Device not found.")
        revoked_at = revoke_device(device)
        return Response({"revoked_at": revoked_at})
