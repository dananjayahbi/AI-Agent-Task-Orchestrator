"""Token endpoints: POST /tokens/agent, GET /tokens, DELETE /tokens/{id}.

Section 9.2 Tokens row, caller Owner (Section 12.2: token management is an
Owner-only row of the matrix — ``IsOwnerSession``). The views stay thin: the
services module mints/revokes, the core pagination module pages, and this
file only adapts HTTP to those primitives.

Error discipline (Section 20.4 item 5): validation problems answer
``VALIDATION_ERROR``; unauthenticated callers ``AUTH_REQUIRED``; a non-owner
credential (e.g. an agent bearer token probing this endpoint) gets
``ROLE_NOT_PERMITTED``. An unknown token id raises DRF's ``NotFound`` which
the envelope handler documents as ``VALIDATION_ERROR`` — there is no generic
"not found" code in the catalog (apps/core/exceptions.py), and revealing
whether another user's token id exists would leak state, so unknown and
not-owned ids answer identically.
"""

from __future__ import annotations

from typing import Any, cast

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import decode_cursor, id_cursor_page, parse_page_size
from apps.core.serializers import ErrorEnvelopeSerializer

from ..models import ApiToken, User
from ..permissions import IsOwnerSession
from ..serializers.auth import RevokedSerializer
from ..serializers.tokens import (
    AgentTokenIssueRequestSerializer,
    AgentTokenIssueResponseSerializer,
    TokenListEnvelopeSerializer,
    TokenListQuerySerializer,
    TokenSummarySerializer,
)
from ..services.tokens import issue_agent_token, revoke_token


class AgentTokenIssueView(APIView):
    """POST /tokens/agent — mint a project-scoped, revocable bearer token.

    The plaintext appears in this response and nowhere else (Section 7.2);
    only its hash is stored with ``kind = agent``, the target ``project_id``
    and the Section 9.10 expiry (ADR-004: one project per token, never a
    token that could address two). Project existence/active-status is
    validated by format here — the registry check joins with WP-1.3 (open
    deviation recorded in the changelog).
    """

    permission_classes: list[Any] = [IsOwnerSession]

    @extend_schema(
        request=AgentTokenIssueRequestSerializer,
        responses={
            status.HTTP_201_CREATED: AgentTokenIssueResponseSerializer,
            status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
            status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
            status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Issue one agent token; plaintext returned exactly once."""
        input_serializer = AgentTokenIssueRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        user = cast(User, request.user)  # guaranteed by IsOwnerSession
        token, plaintext = issue_agent_token(
            user,
            project_id=input_serializer.validated_data["project_id"],
            scopes=input_serializer.validated_data.get("scopes"),
        )
        return Response(
            {
                "id": token.pk,
                "kind": token.kind,
                "project_id": token.project_id,
                "scopes": token.scopes,
                "expires_at": token.expires_at,
                "token": plaintext,
            },
            status=status.HTTP_201_CREATED,
        )


class TokenListView(APIView):
    """GET /tokens — the caller's own tokens, metadata only (never secrets).

    Ordered ``-pk`` (newest first) — the declared stable sort of this
    endpoint (pagination.md rule 2; ``BigAutoField`` ids are monotonic).
    Filterable by ``kind`` and ``project_id`` (Section 9.2; the page is
    scoped to the authenticated owner so one owner never lists another's
    rows).
    """

    permission_classes: list[Any] = [IsOwnerSession]

    @extend_schema(
        responses={
            status.HTTP_200_OK: TokenListEnvelopeSerializer,
            status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
            status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
            status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
        },
        parameters=[TokenListQuerySerializer],
        description=(
            "List the caller's API tokens as metadata (no hash, no "
            "plaintext). Sort: id descending (newest first). Pagination: "
            "cursor-based — pass `cursor` from the previous `next_cursor`; "
            "`page_size` defaults to 25 and is clamped to 100."
        ),
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """One cursor page of the caller's tokens."""
        query = TokenListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        queryset = ApiToken.objects.filter(user=cast(User, request.user))
        if "kind" in validated:
            queryset = queryset.filter(kind=validated["kind"])
        if "project_id" in validated:
            queryset = queryset.filter(project_id=validated["project_id"])

        rows, next_cursor = id_cursor_page(
            queryset,
            cursor=decode_cursor(validated.get("cursor")),
            page_size=parse_page_size(validated.get("page_size")),
        )
        return Response(
            {
                "results": [TokenSummarySerializer(row).data for row in rows],
                "next_cursor": next_cursor,
            }
        )


class TokenRevokeView(APIView):
    """DELETE /tokens/{id} — set ``revoked_at``; effective on the next use.

    Idempotent: repeating the call returns the original ``revoked_at``
    (NFR-12 spirit, same as logout). Rows of other users answer exactly like
    unknown ids so the endpoint cannot be used to probe token existence.
    """

    permission_classes: list[Any] = [IsOwnerSession]

    @extend_schema(
        responses={
            status.HTTP_200_OK: RevokedSerializer,
            status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
            status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
            status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
        },
    )
    def delete(self, request: Request, pk: int, *args: Any, **kwargs: Any) -> Response:
        """Revoke one of the caller's tokens (immediate — no cache)."""
        token = ApiToken.objects.filter(pk=pk, user=cast(User, request.user)).first()
        if token is None:
            raise NotFound("Token not found.")
        revoked_at = revoke_token(token)
        return Response({"revoked_at": revoked_at})
