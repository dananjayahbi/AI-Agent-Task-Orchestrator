"""Root URL configuration (parent plan Section 9.2).

Routes are contributed by their owning micro-tasks: health endpoints
(MT-1.1-03), the OpenAPI document (MT-1.1-04), then the ``/api/v1`` resources
from WP-1.2 onwards. Ops health paths live at the root (``/health/ready``) —
the exact path the Compose probe requests (Section 16.1; recorded in the
WP-1.1 changelog).
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest, HttpResponse
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.health import HealthLive, HealthReady
from apps.projects.views.dashboard import DashboardSummaryView


class ContractSchemaView(SpectacularAPIView):
    """Serves the OpenAPI contract; the serving route itself is not contract data.

    Excluding the meta-route keeps the document to the actual API surface
    (the route's ``format``/``lang`` negotiation enums are generator noise,
    not client contract — MT-1.1-04 decision in the WP changelog).
    """

    @extend_schema(exclude=True)
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Serve the generated document (YAML default, ``?format=json``)."""
        response: HttpResponse = super().get(  # type: ignore[no-untyped-call]
            request, *args, **kwargs
        )
        return response


urlpatterns: list[URLPattern | URLResolver] = [
    # Section 9.2 Ops endpoints — root-level, unauthenticated, exactly as
    # probed by infra/compose (Section 16.1: GET /health/ready).
    path("health/live", HealthLive.as_view(), name="health-live"),
    path("health/ready", HealthReady.as_view(), name="health-ready"),
    # The OpenAPI contract itself (ADR-005; NFR-11). Serving path decided
    # once in MT-1.1-04: the document at /api/v1/schema (YAML by default,
    # ?format=json for JSON), Swagger UI at /api/v1/schema/swagger-ui.
    path("api/v1/schema", ContractSchemaView.as_view(), name="schema"),
    path(
        "api/v1/schema/swagger-ui",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # WP-1.2 resources under the Section 9.2 base path /api/v1 (MT-1.2-01
    # lands auth; tokens and devices join from the same include with
    # MT-1.2-03/04).
    path("api/v1/", include("apps.accounts.urls")),
    # WP-1.3 project registry under the same base path (MT-1.3-03; policy
    # and manifest routes join with MT-1.3-04/05).
    path("api/v1/", include("apps.projects.urls")),
    # WP-1.4 task surface under the same base path (MT-1.4-03: create +
    # detail; the list half and sub-resources join from their owning MTs).
    path("api/v1/", include("apps.tasks.urls")),
    # WP-1.6 agent-work surface (MT-1.6-07): claim, release, work list.
    path("api/v1/", include("apps.leases.urls")),
    # WP-1.6 agent sessions (MT-1.6-09 — the Section 9.2 Sessions row the
    # bridge calls): open and end.
    path("api/v1/", include("apps.agents.urls")),
    # WP-1.10 realtime gateway (MT-1.10-01 — the Section 9.2 Events row:
    # /events/stream and /events).
    path("api/v1/", include("apps.events.urls")),
    # WP-1.11 attachment surface (MT-1.11-03/04/05 — the Section 9.2
    # Attachments row: upload, list, detail, delete).
    path("api/v1/", include("apps.attachments.urls")),
    # Section 9.2 Dashboard row (MT-1.15-06): the Owner-facing summary the
    # mobile Overview consumes (FR-MOB-01). Mounted directly because it is
    # a cross-cutting roll-up, not a /projects/{pid} sub-resource.
    path("api/v1/dashboard/summary", DashboardSummaryView.as_view(), name="dashboard-summary"),
]
