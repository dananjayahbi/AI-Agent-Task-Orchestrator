"""Ops health endpoints (Section 9.2 Ops row; Section 16.1 probe; Section 17).

Canonical paths are root-level ``/health/live`` and ``/health/ready`` — the
exact path the Compose health check requests (Section 16.1), not an
``/api/v1``-prefixed variant; recorded in the WP changelog so the probe and the
OpenAPI document never disagree (MT-1.1-03 risk note).

* ``live``  — the process is serving requests. No dependency checks, no auth.
* ``ready`` — cheap ping-level checks (``SELECT 1``, a cache write) for the
  dependencies Section 16.1 lists for the backend (database, cache). A missing
  dependency answers 503 in the Section 9.2 error envelope with the canonical
  ``SERVER_ERROR`` code — a code that exists in the catalog (20.4 item 5).

Checks are module-level functions so tests can simulate an unreachable
dependency without infrastructure, and stay cheap enough that a slow dependency
cannot restart-loop the container (MT-1.1-03 risk note).
"""

from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.serializers import CharField, DictField, Serializer
from rest_framework.views import APIView

from .errors import SERVER_ERROR
from .serializers import ErrorEnvelopeSerializer


def check_database() -> None:
    """Ping-level database reachability (raises on failure)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


def check_cache() -> None:
    """Ping-level cache reachability (raises on failure)."""
    cache.set("healthcheck", "1", timeout=5)


class ServiceUnavailable(APIException):
    """A required dependency is unreachable — 503, catalog code SERVER_ERROR."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = SERVER_ERROR
    default_detail = "A required dependency is unavailable."


class HealthLiveSerializer(Serializer[Any]):
    """Response body of GET /health/live."""

    status = CharField()


class HealthReadySerializer(Serializer[Any]):
    """Response body of GET /health/ready."""

    status = CharField()
    checks = DictField(child=CharField())


class HealthLive(APIView):
    """GET /health/live — process liveness only (Section 9.2 Ops)."""

    authentication_classes: list[Any] = []
    permission_classes: list[Any] = [AllowAny]

    @extend_schema(responses={200: HealthLiveSerializer})
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
        """200 whenever the process serves requests; never touches a dependency."""
        return Response({"status": "live"})


class HealthReady(APIView):
    """GET /health/ready — database + cache reachability (Section 16.1)."""

    authentication_classes: list[Any] = []
    permission_classes: list[Any] = [AllowAny]

    @extend_schema(
        responses={200: HealthReadySerializer, 503: ErrorEnvelopeSerializer},
    )
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
        """200 when every required dependency answers; 503 envelope otherwise."""
        failures: dict[str, str] = {}
        for name, checker in (("database", check_database), ("cache", check_cache)):
            try:
                checker()
            except Exception:  # noqa: BLE001 - any failure means "not ready"
                failures[name] = "unreachable"
        if failures:
            raise ServiceUnavailable(
                detail=f"Unavailable dependencies: {', '.join(sorted(failures))}",
            )
        return Response({"status": "ready", "checks": {"database": "ok", "cache": "ok"}})
