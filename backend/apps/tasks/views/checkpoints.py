"""Checkpoint endpoints — Section 9.2 Progress row (MT-1.8-03 + MT-1.8-04).

One route pair under ``/tasks/{id}/checkpoints``:

* ``POST`` (caller **Agent** — MT-1.8-03; the owner holds no lease
  session, so the Flow B gate would refuse it anyway): validates the
  Section 7.2 input, runs the MT-1.8-02 gate + store + MT-1.6-03
  extension + §9.6 ``task.checkpoint`` emission in one transaction, and
  answers with the stored checkpoint's identity plus the **new
  lease_expires_at** (Section 10.5: "Returns new expiry" — the bridge
  turns it into its ``next_checkpoint_due`` hint). ``LEASE_EXPIRED`` in
  the standard envelope is the bridge's "stop and re-claim" signal.
* ``GET`` (caller **Agent / Owner** — §9.2; MT-1.8-04): the task's
  reverse-chronological checkpoint history with WP-0.5-04 cursor
  pagination, newest first, empty task → empty page.

Plan-wide contracts reused, never re-invented: ``HasTaskProjectScope``
+ the caller classes (ADR-004; the §9.2 Progress row), the canonical
``Idempotency-Key`` replay (NFR-12 — the WP-1.4/1.6 local
``_replay_or_none``/``_store_outcome`` convention), the §9.2 error
envelope with catalog codes only, ``AgentEndpointThrottle`` on the
agent-authenticated write half (FR-SEC-05), and
``parse_page_size`` + the composite ``(timestamp, id)`` cursor helpers
in ``apps.tasks.services.checkpoints`` (pagination.md).

Status decisions (recorded in the WP changelog, same practice as
WP-1.4/1.5/1.6): 400 malformed input/cursor (``VALIDATION_ERROR``),
401 ``AUTH_REQUIRED``, 403 ``ROLE_NOT_PERMITTED`` /
``AUTH_FORBIDDEN_PROJECT`` / ``LEASE_NOT_OWNED``, 404 unknown task
(``TASK_NOT_FOUND``), 409 ``LEASE_EXPIRED``, 429 ``RATE_LIMITED``.
"""

from __future__ import annotations

from typing import Any, cast

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

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

from ..permissions import CanReadCheckpoints, HasTaskProjectScope
from ..serializers.checkpoints import (
    CheckpointCreateSerializer,
    CheckpointListEnvelopeSerializer,
    CheckpointListQuerySerializer,
    CheckpointWriteResponseSerializer,
    checkpoint_payload,
)
from ..services.checkpoints import (
    checkpoint_page,
    decode_checkpoint_cursor,
    submit_checkpoint,
)
from ..services.tasks import get_task_or_404

# The canonical idempotency header on the mutating half (Section 9.2's
# "all mutating endpoints accept an idempotency key header"; headers.md
# one spelling, never an alias).
_IDEMPOTENCY_PARAMETER = OpenApiParameter(
    name="Idempotency-Key",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=False,
    description=(
        "Caller-derived key making retries safe (ADR-012; NFR-12). Reusing "
        "the key with the same request replays the original outcome instead "
        "of storing a second checkpoint or double-extending the lease."
    ),
)

# Error sets: the write half adds the lease-conflict family (409
# LEASE_EXPIRED, 403 LEASE_NOT_OWNED); the read half is a plain
# authenticated read (no lease codes on GET).
_WRITE_ERRORS = {
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


def _agent_project(request: Request) -> str:
    """The token's project scope (Section 9.3 step 1 — never a body value)."""
    token = request.auth
    project_id = getattr(token, "project_id", None)
    # Agent callers always carry one (WP-1.2); the submit service fails
    # closed on ``None`` — here we only normalize for the type checker.
    return str(project_id)


class CheckpointListCreateView(APIView):
    """``POST``/``GET /tasks/{id}/checkpoints`` — the Progress row."""

    # ADR-004: the PID rides inside the task id — scope first, then the
    # §9.2 caller cell per method (POST Agent, GET Agent/Owner), picked
    # in get_permissions below.
    permission_classes: list[Any] = [HasTaskProjectScope, IsAgentToken]
    throttle_classes = [AgentEndpointThrottle]

    def get_permissions(self) -> list[Any]:
        """POST answers to the Agent cell; GET to the Agent/Owner cell."""
        if self.request is not None and self.request.method == "GET":
            return [HasTaskProjectScope(), CanReadCheckpoints()]
        return [super().get_permissions()[0], IsAgentToken()]

    @extend_schema(
        operation_id="create_checkpoint",
        request=CheckpointCreateSerializer,
        responses={
            status.HTTP_200_OK: CheckpointWriteResponseSerializer,
            **_WRITE_ERRORS,
        },
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "Store one agent checkpoint and extend the lease (Section 9.2 "
            "Progress row; caller: Agent lease holder; Section 6.5 Flow B). "
            "One transaction verifies the fencing pair (`session_id` + "
            "`lease_generation`) against the locked row — a stale "
            "generation or dead lease answers LEASE_EXPIRED (409, stop and "
            "re-claim per Section 10.5), a foreign session LEASE_NOT_OWNED "
            "(403) — then stores the row (server timestamp; "
            "`attempt_number` copied at write time), applies Section 8.6's "
            "min(now + duration, acquired + cap) extension, emits "
            "`task.checkpoint` in-transaction, and returns the new "
            "`lease_expires_at` (plus `capped`, so the bridge can surface "
            "submit-or-release guidance). `kind` gates extension (OQ-04 "
            "recorded reading): progress/system always, liveness only under "
            "the project's checkpoint_and_liveness mode. `Idempotency-Key` "
            "replays a retried checkpoint without a duplicate row or a "
            "double extension (NFR-12)."
        ),
    )
    def post(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Store one checkpoint; return its identity + the new expiry."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        input_serializer = CheckpointCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], input_serializer.validated_data)

        submission = submit_checkpoint(
            id,
            session_id=str(validated["session_id"]),
            lease_generation=int(validated["lease_generation"]),
            message=str(validated.get("message", "")),
            percent=validated.get("percent"),
            token_usage=cast(dict[str, Any], validated.get("token_usage") or {}),
            kind=str(validated.get("kind", "progress")),
            caller_project_id=_agent_project(request),
        )
        response = Response(
            CheckpointWriteResponseSerializer(
                {
                    "checkpoint": checkpoint_payload(submission.checkpoint),
                    "lease_extended": submission.lease_extended,
                    "lease_expires_at": submission.lease_expires_at,
                    "capped": submission.capped,
                }
            ).data
        )
        _store_outcome(request, response)
        return response

    @extend_schema(
        operation_id="list_checkpoints",
        responses={
            status.HTTP_200_OK: CheckpointListEnvelopeSerializer,
            **_READ_ERRORS,
        },
        parameters=[CheckpointListQuerySerializer],
        description=(
            "One task's checkpoint history, newest first (Section 9.2 "
            "Progress row; caller: Agent / Owner). Cursor pagination per "
            "WP-0.5-04: `page_size` (default 25, maximum 100), the opaque "
            "`cursor` from the previous page's `next_cursor`, stable "
            "(timestamp, id) ordering so inserts during paging never shift "
            "or duplicate rows. Empty tasks return an empty page, not an "
            "error. Cross-project agent tokens answer "
            "AUTH_FORBIDDEN_PROJECT (403); unknown tasks TASK_NOT_FOUND "
            "(404). History/backfill only — live updates are the "
            "WP-1.10 `task.checkpoint` event stream."
        ),
    )
    def get(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Page one task's checkpoint history, newest first."""
        task = get_task_or_404(id)

        query = CheckpointListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], query.validated_data)

        cursor = decode_checkpoint_cursor(validated.get("cursor") or None)
        page_size = parse_page_size(validated.get("page_size"))
        rows, next_cursor = checkpoint_page(task, cursor=cursor, page_size=page_size)
        return Response(
            CheckpointListEnvelopeSerializer(
                {
                    "results": [checkpoint_payload(row) for row in rows],
                    "next_cursor": next_cursor,
                }
            ).data
        )
