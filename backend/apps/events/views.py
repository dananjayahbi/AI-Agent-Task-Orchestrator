"""The realtime gateway: ``GET /events/stream`` (SSE) and ``GET /events``.

Section 9.2 lists both endpoints as Owner-facing reads; Section 9.6 defines
the wire contract (filters, monotonic ids, resume, 15 s heartbeats, per-
connection/per-event authorization); ADR-002 fixes SSE as the v1 transport.
This module hosts the two views only — the fan-out hub lives in
``fanout.py``, replay in ``resume.py``, and the per-event policy in
``permissions.py`` — so each layer stays independently testable (modular
small files, WP-1.10 structure).

Authentication (Section 12.2, "Read events" row): the same DRF
authentication every endpoint uses — Owner session (cookie; a same-origin
``EventSource``/fetch stream carries it — MT-4.3-04) or a device/bearer
token (Section 15.4 transport, the mobile fetch-stream client) — guarded by
WP-1.2's ``CanReadEvents`` (agents never subscribe: ``ROLE_NOT_PERMITTED``;
no credential: ``AUTH_REQUIRED``). No query-parameter token scheme exists in
the plan, so none is invented here.

Streaming mechanics (why an async generator): Django's ASGI handler
consumes an async ``StreamingHttpResponse`` incrementally on the event loop,
while a *sync* generator would be materialized with ``sync_to_async(list)``
— buffered whole, exactly what the no-buffering headers exist to prevent.
The response therefore carries the Section 9.6 mime type plus
``Cache-Control: no-cache`` and ``X-Accel-Buffering: no`` (proxy/RISK-05;
tunnel verification belongs to WP-5.1).

History order (MT-1.10-01 risk note resolved): rows are paged in ``id``
ascending order — the Event model's monotonic id *is* the total order used
for replay (MT-1.9-01), so history pages read chronologically forward with
the canonical ``cursor``/``page_size`` contract (pagination.md).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.http import StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanReadEvents
from apps.core.pagination import decode_cursor, id_cursor_page, parse_page_size
from apps.core.serializers import ErrorEnvelopeSerializer

from .envelope import event_envelope
from .fanout import HEARTBEAT_COMMENT, StreamConnection, drain_queue, hub, sse_frame
from .models import Event
from .permissions import scope_for_request
from .resume import last_event_id_from, missed_envelopes
from .serializers import (
    EventListEnvelopeSerializer,
    HistoryQuerySerializer,
    StreamQuerySerializer,
)

_ERROR_RESPONSES: dict[int | str, type[Any]] = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
}


def _filters(query: dict[str, Any]) -> tuple[str | None, str | None]:
    """Validated ``(project, task)`` pair from a parsed query serializer."""
    project = query.get("project")
    task = query.get("task")
    return (
        str(project) if project is not None else None,
        str(task) if task is not None else None,
    )


class EventHistoryView(APIView):
    """GET /events — stored rows in ``id`` order, cursor-paginated (9.2, 9.6).

    The history half of the gateway: same filters as the stream, same
    Section 9.6 envelope per item, pagination.md's two-member envelope per
    page. Section 12.5's viewer is read-only — this endpoint never mutates.
    """

    permission_classes: list[type[BasePermission]] = [CanReadEvents]

    @extend_schema(
        responses={status.HTTP_200_OK: EventListEnvelopeSerializer, **_ERROR_RESPONSES},
        parameters=[HistoryQuerySerializer],
        description=(
            "Event history (Section 9.6 envelope per item). Sort: id "
            "ascending (chronological — the monotonic SSE id order). "
            "Pagination: cursor-based — pass `cursor` from the previous "
            "`next_cursor`; `page_size` defaults to 25 and is clamped to 100. "
            "Filters: `project`, `task` (Section 9.6 names)."
        ),
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """One cursor page of stored events, oldest → newest by id."""
        query = HistoryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        project, task = _filters(query.validated_data)

        # Per-event authorization on the history path too (MT-1.10-05): the
        # stream can never read what history denies — same scope, same
        # filters, one policy module.
        scope = scope_for_request(request)
        queryset = scope.narrowed_queryset(Event.objects.all())
        if project is not None:
            queryset = queryset.filter(project_id=project)
        if task is not None:
            queryset = queryset.filter(task_id=task)

        rows, next_cursor = id_cursor_page(
            queryset,
            cursor=decode_cursor(query.validated_data.get("cursor")),
            page_size=parse_page_size(query.validated_data.get("page_size")),
            descending=False,  # declared sort: id ascending (MT-1.10-01)
        )
        return Response(
            {
                "results": [event_envelope(row) for row in rows],
                "next_cursor": next_cursor,
            }
        )


class EventStreamView(APIView):
    """GET /events/stream — the authenticated SSE subscription (Section 9.6).

    Filters (``project``, ``task``) are fixed at connect time and govern
    every delivery path of this connection (live, replay and the history
    endpoint's equivalent query). Permission checks run *before* the
    streaming response exists, so a rejected caller receives a canonical
    JSON error envelope, never a half-open stream.
    """

    permission_classes: list[type[BasePermission]] = [CanReadEvents]

    @extend_schema(
        responses={
            (status.HTTP_200_OK, "text/event-stream"): OpenApiTypes.BINARY,
            **_ERROR_RESPONSES,
        },
        parameters=[StreamQuerySerializer],
        description=(
            "Server-Sent Events feed of Section 9.6 envelopes (`id:` carries "
            "the monotonic event id; `data:` carries the envelope JSON; "
            "comment lines are heartbeats and carry no id). Filters: "
            "`project`, `task`, fixed at connect. Resume: send the last "
            "received id as the `Last-Event-ID` header (or `last_event_id` "
            "query parameter) to replay missed events before switching to "
            "live. Authentication: owner session or device bearer token — "
            "agents never subscribe (Section 12.2)."
        ),
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> StreamingHttpResponse:
        """Open one SSE connection (heartbeat joins in MT-1.10-04)."""
        query = StreamQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        project, task = _filters(query.validated_data)
        # Client resume input, validated before any stream opens (MT-1.10-03).
        last_event_id = last_event_id_from(request)

        # Register before the response exists so no event published between
        # response start and the generator's first step can slip past the
        # connection (the gap-free handover of MT-1.10-03 builds on this).
        # The scope is fixed here, from the credential that authenticated
        # (MT-1.10-05: per-connection authorization).
        connection = StreamConnection(project=project, task=task, scope=scope_for_request(request))
        hub.register(connection)

        response = StreamingHttpResponse(
            _stream(connection, last_event_id),
            content_type="text/event-stream",
        )
        # No-buffering headers: browsers never buffer EventSource, and the
        # edge/proxy must stream chunks through (Section 9.6; RISK-05).
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


async def _stream(connection: StreamConnection, last_event_id: int | None) -> AsyncIterator[bytes]:
    """One open SSE connection: replay (if any), then live — exactly once each.

    Lifecycle (MT-1.10-02/03/04): the view registered *connection* before
    the response start; this generator starts the single shared Redis
    subscription, replays the missed rows for a reconnecting client
    (thread-sensitive ORM read), then turns queued envelopes into SSE
    frames — each id delivered exactly once via ``connection.claim``, which
    is shared by the replay and live paths so the handover between them
    duplicates nothing and skips nothing. While the queue stays silent for
    ``EVENTS_HEARTBEAT_SECONDS`` (Section 9.6 default 15 s), a heartbeat
    comment keeps the proxies and mobile radios awake; it carries no id
    and never moves the client's resume position. Cleanup runs on client
    disconnect (ASGI cancellation closes the generator): the connection
    leaves the hub, so repeated open/close cycles cannot leak
    registrations.
    """
    hub.start_subscriber()
    try:
        if last_event_id is not None:
            replay = await sync_to_async(missed_envelopes)(last_event_id, connection)
            for envelope in replay:
                if connection.claim(envelope):
                    yield sse_frame(envelope)
        while True:
            live = await drain_queue(connection, float(settings.EVENTS_HEARTBEAT_SECONDS))
            if live is None:
                yield HEARTBEAT_COMMENT
                continue
            if connection.claim(live):
                yield sse_frame(live)
    finally:
        hub.unregister(connection)


__all__ = ["EventHistoryView", "EventStreamView"]
