"""The Sessions endpoints — Section 9.2 rows, caller Bridge (MT-1.6-09).

``POST /agent-sessions`` opens a session; ``POST /agent-sessions/{id}/end``
closes it. Both are agent-facing: ``AgentEndpointThrottle`` applies
(FR-SEC-05 — the rate-limit enumeration flips when these land) and the
canonical ``Idempotency-Key`` header makes retries safe (NFR-12;
ADR-012) through the same replay-store pattern the other mutating
endpoints use (local ``_replay_or_none``/``_store_outcome`` helpers —
the established per-view convention of WP-1.4/MT-1.2-04; a shared
helper is a candidate refactor, not a hidden divergence).

Status codes (recorded): ``201`` on open (row created), ``200`` on end
(including the idempotent second call); errors flow through the core
envelope — 401 ``AUTH_REQUIRED``, 403 ``ROLE_NOT_PERMITTED`` /
``AUTH_FORBIDDEN_PROJECT``, 400 ``VALIDATION_ERROR`` (bad input,
duplicate id, unknown session — the core handler's no-catalog-code
mapping for resources without a code of their own).
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.exceptions import AuthForbiddenProject
from apps.core.idempotency import (
    idempotency_key_of,
    lookup_replay,
    request_fingerprint,
    store_outcome,
)
from apps.core.serializers import ErrorEnvelopeSerializer
from apps.core.throttling import AgentEndpointThrottle
from apps.projects.services.projects import get_project_or_404

from .permissions import HasSessionProjectScope, IsAgentToken, agent_token
from .serializers import AgentSessionCreateSerializer, AgentSessionSerializer
from .services import end_session, open_session

_IDEMPOTENCY_PARAMETER = OpenApiParameter(
    name="Idempotency-Key",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=False,
    description=(
        "Caller-derived key making retries safe (ADR-012; NFR-12). Reusing "
        "the key with the same request replays the original outcome instead "
        "of opening a second session."
    ),
)

_OPEN_ERRORS = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
}
_END_ERRORS = {**_OPEN_ERRORS}


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


class AgentSessionOpenView(APIView):
    """``POST /agent-sessions`` — open one bridge session (Section 9.2)."""

    permission_classes: list[Any] = [IsAgentToken]
    throttle_classes = [AgentEndpointThrottle]

    @extend_schema(
        operation_id="open_agent_session",
        request=AgentSessionCreateSerializer,
        responses={
            status.HTTP_201_CREATED: AgentSessionSerializer,
            **_OPEN_ERRORS,
        },
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "Open an agent session (Section 9.2 Sessions row; caller: Bridge). "
            "The session id is bridge-issued and unguessable (G-18) and travels "
            "in the body; `project_id` and `token_id` are taken from the "
            "authenticated agent token — never from the payload (ADR-004; a "
            "body `project_id` is rejected as an unknown field). `capability` "
            "defaults to `unknown` (Section 10.4); `transport` is one of "
            "Section 10.2's run modes. 201 returns the Section 7.2 row; a "
            "duplicate id answers VALIDATION_ERROR; `Idempotency-Key` replays "
            "a retried open without creating a second row."
        ),
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Create one session row bound to the token's project."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        input_serializer = AgentSessionCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated = input_serializer.validated_data

        token = agent_token(request)
        assert token is not None  # IsAgentToken passed
        if token.project_id is None:
            # Agent tokens always carry a project (WP-1.2); fail closed.
            raise AuthForbiddenProject("Agent token carries no project scope.")
        project = get_project_or_404(token.project_id)

        session = open_session(
            session_id=str(validated["id"]),
            project_id=project.pk,
            token_id=int(token.pk),
            agent_label=str(validated["agent_label"]),
            client_name=str(validated["client_name"]),
            capability=str(validated["capability"]),
            transport=str(validated["transport"]),
        )
        response = Response(AgentSessionSerializer(session).data, status=status.HTTP_201_CREATED)
        _store_outcome(request, response)
        return response


class AgentSessionEndView(APIView):
    """``POST /agent-sessions/{id}/end`` — close one session (Section 9.2)."""

    permission_classes: list[Any] = [HasSessionProjectScope, IsAgentToken]
    throttle_classes = [AgentEndpointThrottle]

    @extend_schema(
        operation_id="end_agent_session",
        request=None,  # empty body — the accounts pattern (logout)
        responses={
            status.HTTP_200_OK: AgentSessionSerializer,
            **_END_ERRORS,
        },
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "End an agent session (Section 9.2 Sessions row; caller: Bridge). "
            "Sets `ended_at` exactly once; repeating the call returns the same "
            "row unchanged (best-effort shutdown calls must be safe). The "
            "session's project must match the token's scope "
            "(AUTH_FORBIDDEN_PROJECT otherwise); an unknown id answers the "
            "standard no-catalog-code mapping (VALIDATION_ERROR, 400). "
            "`Idempotency-Key` replays a retried end."
        ),
    )
    def post(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Mark the session ended; return the row (idempotent)."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        token = agent_token(request)
        assert token is not None  # IsAgentToken passed
        session = end_session(session_id=id, project_id=str(token.project_id))
        response = Response(AgentSessionSerializer(session).data)
        _store_outcome(request, response)
        return response
