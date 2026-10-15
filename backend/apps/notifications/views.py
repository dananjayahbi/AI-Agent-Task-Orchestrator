"""``GET``/``PUT /api/v1/notifications/preferences`` (MT-5.4-05).

The storage + endpoint half of Section 9.8's preferences: **one
account-level record** (a single-owner product — no owner FK exists, the
same recorded reading as MT-5.4-01's fan-out) that the Section 13.1 web
settings surface and the Section 14.1 mobile toggles both read and write.
Toggle *UIs* are out of this MT's scope — its own Scope fixes it at
"storage, endpoint and dispatch consultation" — so this view is the backend
half MT-5.9-03's toggles consume (the dependency ruling recorded in the
WP-5.4 changelog).

**Authorization (the MT's "confirm against the matrix and record the
choice"):** the Section 12.2 matrix has no notification-preferences row and
Section 9.2 lists no notifications endpoint, so the guard is its own named
class — `HasNotificationPreferencesAccess` — granting **Owner and Device**
(the two actors the plan hands these surfaces: web account settings and the
phone's toggles), denying every agent (push stays the owner's dashboard
surface, like the events row). Recorded here and in its docstring.

Response shape: the full closed set every time (the read path materializes
the OQ-13 defaults, so clients never guess a default).
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasNotificationPreferencesAccess
from apps.core.serializers import ErrorEnvelopeSerializer

from .models import NotificationPreference
from .preferences import ensure_preference_rows, get_or_create_preference
from .serializers import (
    NotificationPreferencesRequestSerializer,
    NotificationPreferencesResponseSerializer,
)

_ERROR_RESPONSES: dict[int | str, type[Any]] = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
}


def _payload(rows: list[NotificationPreference]) -> dict[str, list[dict[str, Any]]]:
    """The wire body — declared row order, ids and booleans only (12.4)."""
    return {"preferences": [{"event_type": row.event_type, "enabled": row.enabled} for row in rows]}


class NotificationPreferencesView(APIView):
    """Read and update the account-level per-event-type switches."""

    permission_classes: list[type[BasePermission]] = [HasNotificationPreferencesAccess]

    @extend_schema(
        operation_id="retrieve_notification_preferences",
        responses={
            status.HTTP_200_OK: NotificationPreferencesResponseSerializer,
            **_ERROR_RESPONSES,
        },
        description=(
            "All Section 9.8 notification preference types with their "
            "switches (the closed set — clients render toggles from this "
            "list and never invent types). Defaults: escalation triggers "
            "on, `completion_digest` off (OQ-13). Caller: Owner session or "
            "device token (Section 13.1 / Section 14.1 — one record, both "
            "surfaces); agents are denied."
        ),
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Materialize and return every preference row (declared order)."""
        return Response(_payload(ensure_preference_rows()))

    @extend_schema(
        operation_id="update_notification_preferences",
        request=NotificationPreferencesRequestSerializer,
        responses={
            status.HTTP_200_OK: NotificationPreferencesResponseSerializer,
            **_ERROR_RESPONSES,
        },
        description=(
            "Update any subset of the per-event-type switches "
            "(`preferences` is a list of `{event_type, enabled}` pairs; "
            "unknown or duplicated `event_type` values are rejected with "
            "VALIDATION_ERROR). The response carries the full current set. "
            "Caller: Owner session or device token."
        ),
    )
    def put(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Apply the requested switches, then answer with the full set."""
        serializer = NotificationPreferencesRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for item in serializer.validated_data["preferences"]:
            row = get_or_create_preference(str(item["event_type"]))
            if row.enabled != item["enabled"]:
                row.enabled = bool(item["enabled"])
                row.save(update_fields=["enabled", "updated_at"])
        return Response(_payload(ensure_preference_rows()))
