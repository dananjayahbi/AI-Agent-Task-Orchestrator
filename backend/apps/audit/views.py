"""Audit endpoints — Section 9.2 "Audit" row (WP-3.3; FR-AUD-01, FR-AUD-02).

Two routes, caller **Auditor / Owner** (split by method, like the other
§9.2 shared rows):

* ``POST /tasks/{id}/audit-verdict`` — MT-3.3-05: validates the Section
  10.5 contract, authorizes the **current auditor lease owner** (the
  ``CanSubmitAuditVerdict`` matrix cell first, then the service's
  shared fencing gate), re-proves independence (MT-3.3-02), persists
  the Audit Report (MT-3.3-04) and delegates the outcome to the
  decision seam — the endpoint itself never approves (invariant
  8.3.4). 201 returns the stored report plus the post-transition task
  identity; ``Idempotency-Key`` replays a retried verdict without a
  second report row or a second transition (Section 9.2 idempotency
  rule; NFR-12).
* ``GET /tasks/{id}/audit-reports`` — MT-3.3-04: the task's reports,
  newest first, cursor-paginated (pagination.md) — the review panel's
  and mobile review sheet's read surface.

Plan-wide contracts reused, never re-invented: scope from the token
(``HasTaskProjectScope`` — ADR-004, never the body), capability rows
from ``accounts.permissions`` (plus the app-local ``CanReadAuditReports``
read adapter), the Section 9.2 error envelope with catalog codes only,
the canonical ``Idempotency-Key`` replay (same local
``_replay_or_none``/``_store_outcome`` convention as WP-1.6/WP-3.2),
and ``AgentEndpointThrottle`` (FR-SEC-05).

Status decisions (recorded in the WP changelog): 400 malformed input
(``VALIDATION_ERROR`` — including a body ``task_id`` that disagrees
with the path), 401 ``AUTH_REQUIRED``, 403 ``ROLE_NOT_PERMITTED`` /
``AUTH_FORBIDDEN_PROJECT`` / ``LEASE_NOT_OWNED``, 404 unknown task
(``TASK_NOT_FOUND``), 409 conflict family (``TASK_STATE_CONFLICT``,
``LEASE_EXPIRED``, ``AUDITOR_SAME_AS_CODER``), 429 ``RATE_LIMITED``.
"""

from __future__ import annotations

from typing import Any, cast

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanSubmitAuditVerdict
from apps.core.idempotency import (
    idempotency_key_of,
    lookup_replay,
    request_fingerprint,
    store_outcome,
)
from apps.core.pagination import parse_page_size
from apps.core.serializers import ErrorEnvelopeSerializer
from apps.core.throttling import AgentEndpointThrottle
from apps.tasks.permissions import HasTaskProjectScope
from apps.tasks.serializers.resolutions import task_state_payload
from apps.tasks.services.tasks import get_task_or_404

from .permissions import CanReadAuditReports
from .serializers import (
    AuditReportListEnvelopeSerializer,
    AuditReportListQuerySerializer,
    AuditVerdictRequestSerializer,
    AuditVerdictResponseSerializer,
)
from .services import (
    decode_report_cursor,
    report_page,
    report_payload,
    submit_audit_verdict,
)

_IDEMPOTENCY_PARAMETER = OpenApiParameter(
    name="Idempotency-Key",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=False,
    description=(
        "Caller-derived key making retries safe (ADR-012; NFR-12). Reusing "
        "the key with the same request replays the original outcome instead "
        "of storing a second Audit Report or firing a second transition."
    ),
)

_VERDICT_ERRORS = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
    status.HTTP_404_NOT_FOUND: ErrorEnvelopeSerializer,
    status.HTTP_409_CONFLICT: ErrorEnvelopeSerializer,
    status.HTTP_429_TOO_MANY_REQUESTS: ErrorEnvelopeSerializer,
}
_READ_ERRORS = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
    status.HTTP_404_NOT_FOUND: ErrorEnvelopeSerializer,
}


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
    """Record a successful outcome under this key (2xx only)."""
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


def _caller_project(request: Request) -> str | None:
    """The token's project scope (Section 9.3 step 1 — never a body value).

    Agent callers always carry one (WP-1.2); owner/device credentials
    are not project-bound and answer ``None`` (no scope filter).
    """
    project_id = getattr(request.auth, "project_id", None)
    return str(project_id) if project_id is not None else None


class AuditVerdictView(APIView):
    """``POST /tasks/{id}/audit-verdict`` — the auditor's structured verdict."""

    permission_classes: list[Any] = [HasTaskProjectScope, CanSubmitAuditVerdict]
    throttle_classes = [AgentEndpointThrottle]

    @extend_schema(
        operation_id="submit_audit_verdict",
        request=AuditVerdictRequestSerializer,
        responses={status.HTTP_201_CREATED: AuditVerdictResponseSerializer, **_VERDICT_ERRORS},
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "Store the auditor's proposal and delegate the outcome to the "
            "Policy Engine seam (Section 9.2 Audit row; caller: Auditor, "
            "current lease owner — §12.2). One transaction: verify the "
            "fencing pair (`session_id` + `lease_generation`) against the "
            "locked `to_be_audited` row, re-prove independence "
            "(`AUDITOR_SAME_AS_CODER`, G-20), persist the Audit Report "
            "(§7.2: evidence verbatim, confidence 1-5, proposed verdict), "
            "then dispatch exactly one row: T14 `audit_verdict_escalated` "
            "→ `in_human_review` with an enumerated §8.4 reason (the "
            "fail-closed default until MT-3.4-07 installs the engine) or "
            "T13 `audit_verdict_pass` → `merge_status = pending` (engine "
            "approval only — invariant 8.3.4: this endpoint never "
            "approves). 201 returns the report, the post-transition task "
            "identity, the trigger and the decision. `Idempotency-Key` "
            "replays a retried verdict with no second report and no "
            "second transition. Rejections: VALIDATION_ERROR (400), "
            "LEASE_NOT_OWNED (403), ROLE_NOT_PERMITTED (403), "
            "TASK_STATE_CONFLICT / LEASE_EXPIRED / AUDITOR_SAME_AS_CODER "
            "(409), TASK_NOT_FOUND (404)."
        ),
    )
    def post(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Validate one verdict, store the report, dispatch the outcome."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        input_serializer = AuditVerdictRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], input_serializer.validated_data)

        if str(validated["task_id"]) != id:
            # Section 10.5 carries task_id in the payload; the path is the
            # authority (G-07: the body never addresses another task).
            raise ValidationError({"task_id": "task_id does not match the addressed task."})

        criteria = validated.get("acceptance_criteria_results")
        submission = submit_audit_verdict(
            id,
            session_id=str(validated["session_id"]),
            lease_generation=int(validated["lease_generation"]),
            verdict=str(validated["verdict"]),
            confidence=int(validated["confidence"]),
            notes=str(validated.get("notes", "")),
            evidence=cast(dict[str, Any], validated["evidence"]),
            acceptance_criteria_results=cast(
                "list[dict[str, Any]] | None",
                criteria,
            ),
            caller_project_id=_caller_project(request),
        )
        response = Response(
            AuditVerdictResponseSerializer(
                {
                    "report": report_payload(submission.report),
                    "task": task_state_payload(submission.task),
                    "trigger": submission.trigger,
                    "decision": {
                        "approve": submission.decision.approve,
                        "reason": submission.decision.reason,
                    },
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )
        _store_outcome(request, response)
        return response


class AuditReportListView(APIView):
    """``GET /tasks/{id}/audit-reports`` — one task's audit trail."""

    permission_classes: list[Any] = [HasTaskProjectScope, CanReadAuditReports]
    throttle_classes = [AgentEndpointThrottle]

    @extend_schema(
        operation_id="list_audit_reports",
        responses={
            status.HTTP_200_OK: AuditReportListEnvelopeSerializer,
            **_READ_ERRORS,
        },
        parameters=[AuditReportListQuerySerializer],
        description=(
            "One task's Audit Reports, newest first (Section 9.2 Audit "
            "row; caller: Auditor / Owner — the review panel and mobile "
            "review sheet read surface, MT-3.3-04). Cursor pagination per "
            "pagination.md: `page_size` (default 25, maximum 100), the "
            "opaque `cursor` from the previous page's `next_cursor`, "
            "stable (created_at, id) ordering so inserts during paging "
            "never shift or duplicate rows. Reports accumulate per "
            "resolution across T12 audit retries (recorded reading). "
            "Empty tasks return an empty page. Coder agents and devices "
            "answer ROLE_NOT_PERMITTED (403), cross-project agent tokens "
            "AUTH_FORBIDDEN_PROJECT (403), unknown tasks TASK_NOT_FOUND "
            "(404)."
        ),
    )
    def get(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Page one task's audit reports, newest first."""
        task = get_task_or_404(id)

        query = AuditReportListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], query.validated_data)

        cursor = decode_report_cursor(validated.get("cursor") or None)
        page_size = parse_page_size(validated.get("page_size"))
        rows, next_cursor = report_page(task, cursor=cursor, page_size=page_size)
        return Response(
            AuditReportListEnvelopeSerializer(
                {
                    "results": [report_payload(row) for row in rows],
                    "next_cursor": next_cursor,
                }
            ).data
        )


__all__ = ["AuditReportListView", "AuditVerdictView"]
