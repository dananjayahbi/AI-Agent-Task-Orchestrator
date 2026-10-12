"""Agent-work endpoints — Section 9.2 "Agent work" row (MT-1.6-07).

Three routes, caller **Agent** (project-scoped token, Section 12.2):

* ``POST /tasks/{id}/claim`` — Section 9.3's algorithm end to end;
  200 returns task details, the Section 8.6 lease record (including
  ``lease_generation``) and the Section 10.6 rules block (step 6).
* ``POST /tasks/{id}/release`` — T6, with the owner-override half of
  Section 8.2 T6's Actor column (C, O); 200 returns the updated task.
* ``GET /projects/{pid}/work`` — the offer list (non-locking read);
  ``claim_next_available`` is the locking select-and-claim twin behind
  the service layer (Section 9.3 last paragraph).

Plan-wide contracts reused, never re-invented: scope from the token
(``HasTaskProjectScope`` / ``HasProjectScope`` — ADR-004, never the
body), capability rows from ``accounts.permissions``, the Section 9.2
error envelope with catalog codes only, the canonical
``Idempotency-Key`` replay (ADR-012; NFR-12 — same local
``_replay_or_none``/``_store_outcome`` convention as WP-1.4/MT-1.2-04),
and ``AgentEndpointThrottle`` (FR-SEC-05).

Status decisions (recorded in the WP changelog): 400 malformed input
(``VALIDATION_ERROR``), 404 unknown task (``TASK_NOT_FOUND``), 409
conflict family (``TASK_ALREADY_CLAIMED``, ``TASK_STATE_CONFLICT``,
``DEPENDENCY_UNMET``, ``CONCURRENCY_LIMIT_REACHED``,
``LEASE_EXPIRED``, ``VERSION_CONFLICT``), 403 (``ROLE_NOT_PERMITTED``,
``AUTH_FORBIDDEN_PROJECT``, ``LEASE_NOT_OWNED``), 401
(``AUTH_REQUIRED``), 429 (``RATE_LIMITED``).
"""

from __future__ import annotations

from typing import Any, cast

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import ApiToken, TokenKind
from apps.accounts.permissions import HasProjectScope
from apps.agents.permissions import IsAgentToken
from apps.core.idempotency import (
    idempotency_key_of,
    lookup_replay,
    request_fingerprint,
    store_outcome,
)
from apps.core.pagination import parse_page_size
from apps.core.serializers import ErrorEnvelopeSerializer
from apps.core.throttling import AgentEndpointThrottle
from apps.projects.services.projects import get_project_or_404
from apps.tasks.permissions import HasTaskProjectScope
from apps.tasks.serializers import TaskListEnvelopeSerializer, TaskSerializer
from apps.tasks.services.tasks import (
    decode_task_cursor,
    encode_task_cursor,
    filter_beyond_cursor,
)

from .claim import WorkRole, claim_task, eligible_work_queryset
from .permissions import CanClaimTask, CanReleaseTask
from .release import release_task
from .rules import rules_block_payload
from .serializers import (
    ClaimRequestSerializer,
    ClaimResponseSerializer,
    LeaseRecordSerializer,
    ReleaseRequestSerializer,
    WorkQuerySerializer,
    lease_record_payload,
)

_IDEMPOTENCY_PARAMETER = OpenApiParameter(
    name="Idempotency-Key",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=False,
    description=(
        "Caller-derived key making retries safe (ADR-012; NFR-12). Reusing "
        "the key with the same request replays the original outcome instead "
        "of executing the claim/release again."
    ),
)

_CLAIM_ERRORS = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
    status.HTTP_404_NOT_FOUND: ErrorEnvelopeSerializer,
    status.HTTP_409_CONFLICT: ErrorEnvelopeSerializer,
    status.HTTP_429_TOO_MANY_REQUESTS: ErrorEnvelopeSerializer,
}
_RELEASE_ERRORS = {**_CLAIM_ERRORS}
_WORK_ERRORS = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
    status.HTTP_429_TOO_MANY_REQUESTS: ErrorEnvelopeSerializer,
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


def _agent_project(request: Request) -> str:
    """The token's project scope (Section 9.3 step 1 — never a body value)."""
    token = request.auth
    project_id = getattr(token, "project_id", None)
    # Agent callers always carry one (WP-1.2); the claim service fails
    # closed on ``None`` — here we only normalize for the type checker.
    return str(project_id)


class ClaimView(APIView):
    """``POST /tasks/{id}/claim`` — the Section 9.3 atomic claim."""

    permission_classes: list[Any] = [HasTaskProjectScope, CanClaimTask]
    throttle_classes = [AgentEndpointThrottle]

    @extend_schema(
        operation_id="claim_task",
        request=ClaimRequestSerializer,
        responses={status.HTTP_200_OK: ClaimResponseSerializer, **_CLAIM_ERRORS},
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "Atomically claim a pending task (Section 9.2 Agent-work row; "
            "caller: Agent coder). One transaction takes the row with "
            "`FOR UPDATE SKIP LOCKED`, re-validates state, project status, "
            "dependencies and `max_concurrent_tasks` inside the lock, sets "
            "the Section 8.6 lease and bumps `lease_generation` and "
            "`attempt_number` (FR-LEA-01/02; ADR-012 fencing). 200 returns "
            "task details, the lease record and the Section 10.6 rules "
            "block. Errors: TASK_ALREADY_CLAIMED, TASK_NOT_FOUND, "
            "TASK_STATE_CONFLICT, DEPENDENCY_UNMET, "
            "CONCURRENCY_LIMIT_REACHED, AUTH_FORBIDDEN_PROJECT — all 409/"
            "404/403 per the documented mapping. `Idempotency-Key` replays "
            "a retried claim without leasing twice (NFR-12)."
        ),
    )
    def post(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Claim *id*; return task + lease record + rules block."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        input_serializer = ClaimRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], input_serializer.validated_data)

        task = claim_task(
            task_id=id,
            session_id=str(validated["session_id"]),
            worker_agent_id=str(validated["worker_agent_id"]),
            caller_project_id=_agent_project(request),
        )
        response = Response(
            {
                "task": TaskSerializer(task).data,
                "lease": LeaseRecordSerializer(lease_record_payload(task)).data,
                "rules_block": rules_block_payload(task.project),
            }
        )
        _store_outcome(request, response)
        return response


class ReleaseView(APIView):
    """``POST /tasks/{id}/release`` — T6 voluntary release / Owner override."""

    permission_classes: list[Any] = [HasTaskProjectScope, CanReleaseTask]
    throttle_classes = [AgentEndpointThrottle]

    @extend_schema(
        operation_id="release_task",
        request=ReleaseRequestSerializer,
        responses={status.HTTP_200_OK: TaskSerializer, **_RELEASE_ERRORS},
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "Voluntarily release a claimed task back to `pending` (Section "
            "9.2; Section 8.2 T6 — actors C, O). No `failure_retry_count` "
            "increment (FR-LEA-06); `attempt_number` is preserved. Agent "
            "callers must carry `session_id` and `lease_generation` "
            "(ADR-012): a foreign session answers LEASE_NOT_OWNED, a stale "
            "generation or dead lease LEASE_EXPIRED. An Owner session "
            "applies the documented override without the fencing pair. "
            "Optional `reason` lands on the Transition note; optional "
            "`version` enables the FR-TSK-06 stale-version check. 200 "
            "returns the updated task."
        ),
    )
    def post(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Release *id* (owner override or fencing-pair agent)."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        input_serializer = ReleaseRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], input_serializer.validated_data)

        token = request.auth
        owner_override = isinstance(token, ApiToken) and token.kind == TokenKind.OWNER_SESSION
        actor_ref = (
            str(request.user.pk)
            if owner_override and request.user.is_authenticated
            else str(validated["session_id"] or "owner")
        )
        session_id = validated.get("session_id")
        task = release_task(
            task_id=id,
            session_id=str(session_id) if session_id is not None else None,
            lease_generation=(
                int(validated["lease_generation"])
                if validated.get("lease_generation") is not None
                else None
            ),
            actor_type="owner" if owner_override else "agent",
            actor_ref=actor_ref,
            owner_override=owner_override,
            reason=str(validated.get("reason", "")),
            expected_version=(
                int(validated["version"]) if validated.get("version") is not None else None
            ),
            caller_project_id=None if owner_override else _agent_project(request),
        )
        response = Response(TaskSerializer(task).data)
        _store_outcome(request, response)
        return response


class WorkView(APIView):
    """``GET /projects/{pid}/work`` — the offer list (FR-PRJ-04, FR-TSK-07)."""

    permission_classes: list[Any] = [HasProjectScope, IsAgentToken]
    throttle_classes = [AgentEndpointThrottle]

    @extend_schema(
        operation_id="list_work",
        responses={status.HTTP_200_OK: TaskListEnvelopeSerializer, **_WORK_ERRORS},
        parameters=[WorkQuerySerializer],
        description=(
            "List the project's offerable work (Section 9.2 Agent-work row; "
            "caller: Agent). `role=coder` (default) lists `pending` tasks "
            "whose dependencies are completed; `role=auditor` lists "
            "`to_be_audited` (the audit claim arrives with WP-3.3). "
            "Archived tasks are hidden (T19), a non-active project returns "
            "an empty list (FR-PRJ-04), order is FR-TSK-05 canonical "
            "(priority, then oldest first), cursor-paginated. This read is "
            "deliberately non-locking: the locking select-and-claim twin is "
            "the claim-next service (Section 9.3)."
        ),
    )
    def get(self, request: Request, pid: str, *args: Any, **kwargs: Any) -> Response:
        """One cursor page of offerable tasks (or an empty list)."""
        project = get_project_or_404(pid)
        query = WorkQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], query.validated_data)

        empty: dict[str, Any] = {"results": [], "next_cursor": None}
        if project.active_status != "active":
            return Response(empty)  # FR-PRJ-04: paused/archived offers no work

        queryset = eligible_work_queryset(
            project,
            role=cast(WorkRole, validated["role"]),
            priority=validated.get("priority"),
        )
        cursor = decode_task_cursor(validated.get("cursor"))
        if cursor is not None:
            queryset = filter_beyond_cursor(queryset, cursor)

        page_size = parse_page_size(validated.get("page_size"))
        rows = list(queryset[: page_size + 1])
        has_more = len(rows) > page_size
        rows = rows[:page_size]
        next_cursor = encode_task_cursor(rows[-1]) if has_more and rows else None
        return Response(
            {
                "results": [TaskSerializer(row).data for row in rows],
                "next_cursor": next_cursor,
            }
        )
