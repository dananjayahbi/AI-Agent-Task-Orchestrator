"""``GET /api/v1/ops/overview`` — the operations view's data source
(Section 17 Dashboards row; NFR-10; MT-6.4-03; WP-6.4).

One owner-scoped read that assembles exactly what the previous two slices
produced, server-side, so the web view never computes its own numbers
(the /metrics endpoint wins on any disagreement — it *is* this payload's
``metrics`` field, the same ``collect()`` document):

* ``metrics`` — MT-6.4-01's nine Section 17 metrics plus the worker/beat/
  sweeper heartbeats, verbatim from ``apps.core.metrics.collect()`` (unit
  semantics tabulated in ``docs/plan/metrics.md``);
* ``alerts`` — MT-6.4-02's six Section 17 rules with firing state, onset
  and signal/threshold context, verbatim from
  ``apps.core.alerts.evaluate_alerts()`` (rules catalog:
  ``docs/plan/alerts.md``);
* ``health`` — the Section 17 Health row: live (this process is serving)
  plus the same ping-level ready checks ``/health/ready`` runs, so the
  view shows one snapshot without a second round-trip.

Why a new endpoint instead of reusing ``/metrics``: that route is
deliberately a plain Django view — out of the OpenAPI document, root-level,
internal/LAN-only (MT-6.4-01's recorded posture), and the web client talks
to the backend only through the generated client over the same-origin
``/api/v1`` proxy (NFR-11 import boundary). This endpoint is the owner-
scoped bridge: it *embeds* the same collectors rather than recomputing, is
read-only, and stays inside the contract.

Caller: **Owner only** — Section 12.2 prints no dashboard/ops capability
row for agents or devices (the matrix grants no agent access to dashboards),
so the Owner-session-only guard applies exactly as on the Dashboard row:
anonymous → ``AUTH_REQUIRED`` (401), every agent role and a device token →
``ROLE_NOT_PERMITTED`` (403). Not a list endpoint: single-resource GET,
no pagination (pagination.md pattern). No events — a read path emits
nothing (Section 9.6 catalog has no ops event).
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BooleanField, CharField, DictField, Serializer
from rest_framework.views import APIView

from apps.accounts.permissions import IsOwnerSession
from apps.core.alerts import evaluate_alerts
from apps.core.health import check_cache, check_database
from apps.core.metrics import collect
from apps.core.serializers import ErrorEnvelopeSerializer

# The owner-side error set for this read: missing credential (401) and
# wrong-role callers (403) — both answer the catalog envelope (Section 9.2).
_READ_ERRORS = {
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
}


class AlertStateSerializer(Serializer[Any]):
    """One MT-6.4-02 rule's state — field names are the alert contract."""

    id = CharField(
        help_text=(
            "Stable rule id: sweeper_not_running, attachment_backlog, "
            "push_failures, tunnel_down, repeated_auth_failures, "
            "media_disk_usage (Section 17 Alerts row, plan order)."
        ),
    )
    name = CharField(help_text="The Section 17 alert name, verbatim.")
    severity = CharField(help_text="'critical' or 'warning' (docs/plan/alerts.md).")
    firing = BooleanField(help_text="True while the rule's condition holds.")
    status = CharField(
        help_text="'firing', 'ok', or 'unknown' (signal never reported — never fires).",
    )
    since = CharField(
        required=False,
        allow_null=True,
        help_text="ISO onset of the current firing stretch, or null when resting.",
    )
    signal = DictField(
        help_text="Numbers only — counts, ages, rates. No identities, no secrets (12.4).",
    )
    threshold = DictField(help_text="The configurable threshold(s) in force.")
    runbook = CharField(
        required=False,
        allow_null=True,
        help_text="Section 17 runbook name where one exists (else null).",
    )


class OpsHealthSerializer(Serializer[Any]):
    """Section 17 Health row: live plus the ready checks' reachability."""

    live = BooleanField(
        help_text="Always true in a 200 body — this process served the request.",
    )
    checks = DictField(
        child=CharField(),
        help_text="'database'/'cache' → 'ok' or 'unreachable' (same pings as /health/ready).",
    )


class OpsOverviewSerializer(Serializer[Any]):
    """``GET /api/v1/ops/overview`` body — one snapshot for the ops view."""

    schema_version = CharField(
        help_text="Payload contract version; bump on breaking shape changes.",
    )
    generated_at = CharField(
        help_text=(
            "ISO timestamp of this snapshot — the view shows it as data "
            "freshness so a frozen view is recognizable as stale "
            "(MT-6.4-03 risk note; polling is the recorded update mode)."
        ),
    )
    metrics = DictField(
        help_text=(
            "MT-6.4-01's nine Section 17 metrics plus heartbeats, verbatim "
            "from the /metrics collector (docs/plan/metrics.md is the "
            "semantics table; this payload and /metrics cannot disagree — "
            "same collect())."
        ),
    )
    alerts = AlertStateSerializer(
        many=True,
        help_text=(
            "MT-6.4-02's six Section 17 rules in plan order, with firing "
            "state and context (docs/plan/alerts.md)."
        ),
    )
    health = OpsHealthSerializer(
        help_text="Section 17 Health row — live/ready plus heartbeat visibility via metrics.",
    )


class OpsOverviewView(APIView):
    """One owner-scoped snapshot: metrics + alert states + health."""

    # Section 12.2 grants no ops/dashboard capability to agents or devices;
    # the Owner-session-only guard is the exact fit (Dashboard-row pattern).
    permission_classes = [IsOwnerSession]

    @extend_schema(
        operation_id="retrieve_ops_overview",
        responses={
            status.HTTP_200_OK: OpsOverviewSerializer,
            **_READ_ERRORS,
        },
        description=(
            "Operations view snapshot (Section 17 Dashboards row): the nine "
            "metrics MT-6.4-01 exposes at /metrics (same collect() — this "
            "payload is authoritative and the client never recomputes), the "
            "six MT-6.4-02 alert states in plan order, and the Health row "
            "(live + ready checks; heartbeats ride `metrics.heartbeats`). "
            "Single-resource GET — no pagination. Caller: Owner only "
            "(Section 12.2); agents and devices answer "
            "ROLE_NOT_PERMITTED, anonymous callers AUTH_REQUIRED. "
            "Read-only: alert acknowledgement, threshold tuning and runbook "
            "execution are out of scope (Section 17 'One operations view')."
        ),
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Render one snapshot: collect() + evaluate_alerts() + health pings."""
        document = collect()
        failures: dict[str, str] = {}
        for name, checker in (("database", check_database), ("cache", check_cache)):
            try:
                checker()
            except Exception:
                # Any exception means "not reachable" — same ping, same wording.
                failures[name] = "unreachable"
        payload = {
            "schema_version": "ops-overview-1",
            "generated_at": document["generated_at"],
            "metrics": document["metrics"],
            "alerts": evaluate_alerts(),
            "health": {
                "live": True,
                "checks": {name: "ok" for name in ("database", "cache")} | failures,
            },
        }
        return Response(OpsOverviewSerializer(payload).data)


__all__ = [
    "AlertStateSerializer",
    "OpsHealthSerializer",
    "OpsOverviewSerializer",
    "OpsOverviewView",
]
