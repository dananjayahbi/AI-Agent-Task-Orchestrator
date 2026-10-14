"""The merge queue endpoints (Section 9.2; MT-3.7-01).

Three routes, the Merge Executor's whole surface: ``GET
/merge/pending`` (Owner read + executor per Section 12.2's *Merge
queue* row), ``POST /merge/{task}/start`` and ``POST
/merge/{task}/result`` (executor only — the Owner cell is *Read*, so
no owner bypass exists here; risk note of MT-3.7-01). Conventions
inherit from the audit views: scope first (ADR-004 zero-bleed — the
task id carries the PID), ``Idempotency-Key`` replay/storing on both
mutations (ADR-012), ``AgentEndpointThrottle`` on every route
(FR-SEC-05; the owner GET rides the shared-row budget recorded in the
WP-3.7 changelog), catalog error codes only, and ``@extend_schema``
operation ids so the generated document enumerates the row
(Section 20.4 item 4).

The pending listing is the one URL-less route: its project scope
comes from the token (``request.auth.project_id``) and filters the
queryset inside the service — an agent token sees only its own
project's queue, the Owner sees every project (Section 12.2 *Read*).
"""

from __future__ import annotations

from typing import Any, cast

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanOperateMergeQueue, CanReadMergeQueue
from apps.core.idempotency import (
    idempotency_key_of,
    lookup_replay,
    request_fingerprint,
    store_outcome,
)
from apps.core.pagination import decode_str_cursor, parse_page_size
from apps.core.serializers import ErrorEnvelopeSerializer
from apps.core.throttling import AgentEndpointThrottle
from apps.tasks.permissions import HasTaskProjectScope
from apps.tasks.serializers.resolutions import task_state_payload

from .serializers import (
    MergeQueueListEnvelopeSerializer,
    MergeQueueListQuerySerializer,
    MergeResultRequestSerializer,
    MergeResultResponseSerializer,
    MergeStartRequestSerializer,
    MergeStartResponseSerializer,
)
from .services import (
    branch_names_for,
    list_merge_pending,
    report_merge_result,
    start_merge,
)

_IDEMPOTENCY_PARAMETER = OpenApiParameter(
    name="Idempotency-Key",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=False,
    description=(
        "Caller-derived key making retries safe (ADR-012; NFR-12). Reusing "
        "the key with the same request replays the original outcome instead "
        "of storing a second claim or applying a second merge result."
    ),
)

_MUTATION_ERRORS = {
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
    are not project-bound and answer ``None`` (no scope filter — the
    Owner's Read cell spans projects).
    """
    project_id = getattr(request.auth, "project_id", None)
    return str(project_id) if project_id is not None else None


class MergePendingView(APIView):
    """``GET /merge/pending`` — one FIFO page of the merge queue."""

    permission_classes: list[Any] = [CanReadMergeQueue]
    throttle_classes = [AgentEndpointThrottle]

    @extend_schema(
        operation_id="list_merge_pending",
        responses={
            status.HTTP_200_OK: MergeQueueListEnvelopeSerializer,
            **_READ_ERRORS,
        },
        parameters=[MergeQueueListQuerySerializer],
        description=(
            "Tasks awaiting a merge (Section 9.2 Merge queue row; caller: "
            "Merge Executor, Owner read-only — §12.2). The queue is every "
            "live task with `merge_status = pending` in a carrier state "
            "(`in_human_review` from T15's approve, `to_be_audited` from "
            "the engine-approved T10/T13 branches — Section 8.1's "
            "sub-status, never a seventh state). Cursor pagination per "
            "pagination.md: `page_size` (default 25, maximum 100, clamped), "
            "the opaque `cursor` from the previous `next_cursor`, FIFO by "
            "task id so polling is stable. An agent token sees only its "
            "own project's queue (ADR-004 zero-bleed); the Owner sees "
            "every project. Coder/auditor/decomposer agents and devices "
            "answer ROLE_NOT_PERMITTED (403); anonymous AUTH_REQUIRED "
            "(401)."
        ),
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Page one FIFO slice of the merge-pending queue."""
        query = MergeQueueListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], query.validated_data)

        cursor = decode_str_cursor(validated.get("cursor") or None)
        page_size = parse_page_size(validated.get("page_size"))
        rows, next_cursor = list_merge_pending(
            caller_project_id=_caller_project(request),
            cursor=cursor,
            page_size=page_size,
        )
        branches = branch_names_for(rows)
        return Response(
            MergeQueueListEnvelopeSerializer(
                {
                    "results": [
                        {
                            "id": task.pk,
                            "project_id": task.project_id,
                            "title": task.title,
                            "state": task.state,
                            "version": task.version,
                            "merge_status": task.merge_status,
                            "branch_name": branches.get(task.pk),
                            "merge_strategy": task.project.agent_policy.merge_strategy,
                        }
                        for task in rows
                    ],
                    "next_cursor": next_cursor,
                }
            ).data
        )


class MergeStartView(APIView):
    """``POST /merge/{task}/start`` — claim one queue entry (→ merging)."""

    # Scope first (ADR-004 zero-bleed outranks role errors), then the
    # Section 12.2 *Merge queue* write cell (Merge Executor only — the
    # Owner cell is Read, so an owner POST answers ROLE_NOT_PERMITTED).
    permission_classes: list[Any] = [HasTaskProjectScope, CanOperateMergeQueue]
    throttle_classes = [AgentEndpointThrottle]
    #: ``HasTaskProjectScope`` parses the PID out of this URL kwarg.
    project_url_kwarg = "task"

    @extend_schema(
        operation_id="start_merge",
        request=MergeStartRequestSerializer,
        responses={status.HTTP_200_OK: MergeStartResponseSerializer, **_MUTATION_ERRORS},
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "Claim one pending task for merging (Section 9.2 Merge queue "
            "row; caller: Merge Executor — §12.2). One transaction: verify "
            "the task is live, in a carrier state and still `merge_status = "
            "pending` (anything else answers TASK_STATE_CONFLICT, 409 — a "
            "second executor's claim or an exited task changes nothing), "
            "optional `version` CAS (VERSION_CONFLICT, 409), then set "
            "`merging`, increment `version` and write the `merge.started` "
            "event (Section 9.6) — published after commit. Not a "
            "dispatch: Section 8.2 has no start row (recorded reading). "
            "`Idempotency-Key` replays a retried claim with no second "
            "event. Rejections: VALIDATION_ERROR (400), ROLE_NOT_PERMITTED "
            "/ AUTH_FORBIDDEN_PROJECT (403), TASK_NOT_FOUND (404), "
            "TASK_STATE_CONFLICT / VERSION_CONFLICT (409), RATE_LIMITED "
            "(429)."
        ),
    )
    def post(self, request: Request, task: str, *args: Any, **kwargs: Any) -> Response:
        """Claim *task* for this executor; answer with its new identity."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        input_serializer = MergeStartRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], input_serializer.validated_data)
        version = validated.get("version")

        updated = start_merge(
            task,
            caller_project_id=_caller_project(request),
            version=int(version) if version is not None else None,
        )
        response = Response(
            MergeStartResponseSerializer({"task": task_state_payload(updated)}).data,
            status=status.HTTP_200_OK,
        )
        _store_outcome(request, response)
        return response


class MergeResultView(APIView):
    """``POST /merge/{task}/result`` — apply T17 (success) or T18 (failure)."""

    # Same composition as start: scope before the executor-only cell.
    permission_classes: list[Any] = [HasTaskProjectScope, CanOperateMergeQueue]
    throttle_classes = [AgentEndpointThrottle]
    project_url_kwarg = "task"

    @extend_schema(
        operation_id="report_merge_result",
        request=MergeResultRequestSerializer,
        responses={status.HTTP_200_OK: MergeResultResponseSerializer, **_MUTATION_ERRORS},
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "Report one merge outcome (Section 9.2 Merge queue row; caller: "
            "Merge Executor — §12.2). `succeeded` dispatches T17 → "
            "`completed` + `merge_status = merged` (ADR-008: completed only "
            "when the result is reported), carrying the required `sha` in "
            "the payload, the history note and the `merge.succeeded` event "
            "data (Section 7.2 has no sha column — the three carriers are "
            "the contract). `conflict`/`failed` dispatch T18 → "
            "`in_human_review` with `review_reason = merge_conflict` "
            "(Section 8.4) and the Section 9.8 push, emitting "
            "`merge.failed`. Exactly one row applies: a repeat report on an "
            "exited task answers TASK_STATE_CONFLICT (409). "
            "`Idempotency-Key` replays a retried report with no second "
            "transition. Rejections: VALIDATION_ERROR (400), "
            "ROLE_NOT_PERMITTED / AUTH_FORBIDDEN_PROJECT (403), "
            "TASK_NOT_FOUND (404), TASK_STATE_CONFLICT / VERSION_CONFLICT "
            "(409), RATE_LIMITED (429)."
        ),
    )
    def post(self, request: Request, task: str, *args: Any, **kwargs: Any) -> Response:
        """Apply one reported outcome; answer with the new task identity."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        input_serializer = MergeResultRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], input_serializer.validated_data)
        version = validated.get("version")

        outcome = report_merge_result(
            task,
            result=str(validated["result"]),
            sha=str(validated.get("sha", "")) or None,
            details=str(validated.get("details", "")),
            version=int(version) if version is not None else None,
            caller_project_id=_caller_project(request),
        )
        response = Response(
            MergeResultResponseSerializer(
                {
                    "task": task_state_payload(outcome.task),
                    "result": outcome.result,
                    "sha": outcome.sha,
                }
            ).data,
            status=status.HTTP_200_OK,
        )
        _store_outcome(request, response)
        return response


__all__ = ["MergePendingView", "MergeResultView", "MergeStartView"]
