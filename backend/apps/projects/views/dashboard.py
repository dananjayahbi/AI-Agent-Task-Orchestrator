"""``GET /dashboard/summary`` — Section 9.2 Dashboard row (MT-1.15-06).

The one Owner-facing roll-up endpoint of the v1 surface: per-project
Overview cards (counts per state, velocity, active agents — Section 14.1
Home / FR-MOB-01), aggregated server-side by ``services.dashboard`` so no
client ever assembles the numbers itself (MT-5.6-01 risk note; the WP-5.6
changelog's "Dashboard endpoint gap" recommendation closed here).

Caller: **Owner only** — Section 9.2's Dashboard row names Owner, and
Section 12.2 prints no dashboard capability row, so the Owner-session-only
guard applies exactly as on the token/device management rows: anonymous →
``AUTH_REQUIRED`` (401), every agent role and a device token →
``ROLE_NOT_PERMITTED`` (403). Granting the mobile's device token a cell is
an owner decision (recorded OQ — the WP-1.8 checkpoints precedent), never a
silent widening here.

Not a list endpoint: single-resource GET with no pagination (pagination.md
names "dashboard summary" among the non-list GETs). No events are emitted —
the Section 9.6 catalog has no dashboard event (Section 20.4 item 6).
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsOwnerSession
from apps.core.serializers import ErrorEnvelopeSerializer

from ..serializers.dashboard import DashboardSummarySerializer
from ..services.dashboard import build_dashboard_summary

# The owner-side error set for this read: missing credential (401) and
# wrong-role callers (403) — both answer the catalog envelope (Section 9.2).
_READ_ERRORS = {
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
}


class DashboardSummaryView(APIView):
    """One card per project: state counts, velocity, active agents."""

    # Section 9.2 Dashboard row caller = Owner; no Section 12.2 capability
    # row exists for it, so the Owner-session-only guard is the exact fit
    # (same pattern as the /tokens and /devices rows).
    permission_classes: list[Any] = [IsOwnerSession]

    @extend_schema(
        operation_id="retrieve_dashboard_summary",
        responses={
            status.HTTP_200_OK: DashboardSummarySerializer,
            **_READ_ERRORS,
        },
        description=(
            "Per-project Overview cards for the Home / Overview surfaces "
            "(Section 14.1; FR-MOB-01). Every registered project appears "
            "once, ordered by project id. `state_counts` carries all six "
            "canonical G-01 states (ADR-010), zero-filled, over the "
            "project's non-archived tasks (T19 default visibility). "
            "`velocity` counts the project's completions in the trailing "
            "7-day window on the server clock (conservative documented "
            "default — the plan states no definition; this payload is "
            "authoritative and clients never recompute it). `active_agents` "
            "counts AgentSession rows with `ended_at` null. Single-resource "
            "GET — no pagination (pagination.md). Caller: Owner only "
            "(Section 9.2); agents and devices answer ROLE_NOT_PERMITTED, "
            "anonymous callers AUTH_REQUIRED."
        ),
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Render the summary payload (no query parameters, no pagination)."""
        return Response(DashboardSummarySerializer(build_dashboard_summary()).data)
