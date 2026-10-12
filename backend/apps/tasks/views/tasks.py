"""Task CRUD endpoints — Section 9.2 Tasks row (MT-1.4-03).

``POST /projects/{pid}/tasks``, ``GET /tasks/{id}`` and
``PATCH /tasks/{id}``; the list half of the first route joins with
MT-1.4-04. Caller **Owner** (Section 9.2's Tasks row caller column — the
``/projects/{pid}/tasks`` POST is also the "Create draft tasks" matrix
row).

Recorded readings (MT-1.4-03 risk note, WP changelog):

* **Owner-only now, matrix cells deferred** — Section 12.2 prints
  Decomposer = Yes and Device = Yes (Could) on "Create draft tasks", but
  with no distinct decomposer token kind yet (MT-1.2-05 risk) these
  endpoints enforce Owner-only *today*; the deferred cells are recorded
  explicitly in ``tests/test_authorization_matrix.py``
  (``DEFERRED_MATRIX_CELLS``) with an explicit revisit marker for
  WP-2.x/M5 — the full row class (``CanCreateDraftTasks``) already
  implements the printed cells and activates by swapping the permission
  class when a distinct kind exists. No silent matrix coverage either
  way.
* **Scope before role** (ADR-004): ``HasProjectScope`` first on the
  project-addressed route, ``HasTaskProjectScope`` first on
  ``/tasks/{id}`` (the PID rides inside the id) — an agent token aimed
  at another project answers ``AUTH_FORBIDDEN_PROJECT`` before any role
  error; then ``IsOwnerSession``.
* **Idempotency** (Section 9.2 rule; ADR-012; headers.md): both mutating
  endpoints honor the canonical ``Idempotency-Key`` header through
  ``apps.core.idempotency`` — same key + same request replays the stored
  outcome; key reuse with a *different* request executes normally (the
  headers.md open point — no invented behavior).
* **``task.created`` hook**: ``services.tasks.create_task`` marks the
  Section 9.6 emission point for WP-1.9.
"""

from __future__ import annotations

from typing import Any, cast

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasProjectScope, IsOwnerSession
from apps.core.idempotency import (
    idempotency_key_of,
    lookup_replay,
    request_fingerprint,
    store_outcome,
)
from apps.core.pagination import parse_page_size
from apps.core.serializers import ErrorEnvelopeSerializer
from apps.projects.services.projects import get_project_or_404

from ..permissions import HasTaskProjectScope
from ..serializers import (
    TaskCreateSerializer,
    TaskListEnvelopeSerializer,
    TaskListQuerySerializer,
    TaskSerializer,
    TaskUpdateSerializer,
)
from ..services.tasks import (
    create_task,
    decode_task_cursor,
    encode_task_cursor,
    filter_beyond_cursor,
    get_task_or_404,
    task_list_queryset,
    update_task,
)

# The canonical idempotency header on every mutating operation
# (Section 9.2: "All mutating endpoints accept an idempotency key
# header") — one spelling, documented, never an alias (headers.md).
_IDEMPOTENCY_PARAMETER = OpenApiParameter(
    name="Idempotency-Key",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=False,
    description=(
        "Caller-derived key making retries safe (ADR-012; NFR-12). Reusing "
        "the key with the same request replays the original outcome instead "
        "of re-executing it; reusing it with a different request is an open "
        "point (headers.md) and executes normally."
    ),
)

# Owner-side error set: bad input/unknown-or-malformed id (400), missing
# credential (401), wrong role or cross-project (403), unknown task (404,
# TASK_NOT_FOUND — the resource-owning status), stale version (409,
# VERSION_CONFLICT). Owner-session endpoints stay unthrottled (FR-SEC-05
# scopes RATE_LIMITED to agent/device endpoints).
_CREATE_ERRORS = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
}
_READ_ERRORS = {
    **_CREATE_ERRORS,
    status.HTTP_404_NOT_FOUND: ErrorEnvelopeSerializer,
}
_UPDATE_ERRORS = {
    **_READ_ERRORS,
    status.HTTP_409_CONFLICT: ErrorEnvelopeSerializer,
}


def _created_by(request: Request) -> str | None:
    """Actor reference for Section 7.2's ``created_by`` (user id, or None)."""
    user = getattr(request, "user", None)
    user_id = getattr(user, "pk", None)
    return str(user_id) if user_id is not None else None


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
    """Record a successful outcome under this key (2xx only, inside the store)."""
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


class TaskListCreateView(APIView):
    """``GET`` (list: filters, canonical order, cursor page) + ``POST``
    (create in ``draft`` — T1's first step).

    The GET half is MT-1.4-04: canonical FR-TSK-05 order computed **in
    the database**, state/priority filters, archived hidden by default,
    MT-0.5-04 cursor pagination.
    """

    # Scope first (ADR-004 zero-bleed outranks role errors), then the
    # Section 9.2 Owner caller / Section 12.2 "Create draft tasks" row's
    # Owner-only enforcement (deferred cells recorded — module docstring).
    permission_classes: list[Any] = [HasProjectScope, IsOwnerSession]

    @extend_schema(
        operation_id="list_tasks",
        responses={status.HTTP_200_OK: TaskListEnvelopeSerializer, **_READ_ERRORS},
        parameters=[TaskListQuerySerializer],
        description=(
            "List one project's tasks (Section 9.2; caller: Owner only). "
            "Default order is FR-TSK-05 canonical: `urgent > high > medium > "
            "low`, then oldest `created_at` first (FIFO), then the task id's "
            "generation order (`T001` … `T999` < `T1000`) — one deterministic "
            "sort computed in the database (NFR-09). Filters: repeat "
            "`state` for canonical values, single `priority`; archived tasks "
            "are excluded unless `include_archived=true` (T19 default "
            "visibility). Pagination: cursor-based — pass `cursor` from the "
            "previous `next_cursor` *with the same filters* (pagination.md "
            "rule 1); `page_size` defaults to 25, clamped to 100. Results "
            "never cross the path project."
        ),
    )
    def get(self, request: Request, pid: str, *args: Any, **kwargs: Any) -> Response:
        """One cursor page of the project's tasks in the canonical order."""
        project = get_project_or_404(pid)
        query = TaskListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], query.validated_data)

        queryset = task_list_queryset(
            project,
            states=validated.get("state"),
            priority=validated.get("priority"),
            include_archived=bool(validated.get("include_archived", False)),
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

    @extend_schema(
        operation_id="create_task",
        request=TaskCreateSerializer,
        responses={status.HTTP_201_CREATED: TaskSerializer, **_CREATE_ERRORS},
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "Create a task (Section 9.2 Tasks row; caller: Owner only). "
            "T1's model-level step: the id is allocated server-side "
            "(`{PID}-T{index}`, Section 7.3), `state` starts at `draft`, "
            "`version` starts at 1 (FR-TSK-06), `audit_required` copies the "
            "project policy, and `target_scope` globs are validated against "
            "Section 12.3. Accepts the FR-TSK-02 field set only — `state`, "
            "`version`, `id`, lease/merge fields are rejected as unknown. "
            "`Idempotency-Key` replays a retry without duplicating the task "
            "(ADR-012)."
        ),
    )
    def post(self, request: Request, pid: str, *args: Any, **kwargs: Any) -> Response:
        """Create one task in ``draft``; return it with ``version`` 1."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        project = get_project_or_404(pid)
        input_serializer = TaskCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], input_serializer.validated_data)

        task = create_task(
            project=project,
            title=validated["title"],
            description=validated["description"],
            acceptance_criteria=validated["acceptance_criteria"],
            target_scope=validated["target_scope"],
            test_command=validated["test_command"],
            priority=validated["priority"],
            created_by=_created_by(request),
            depends_on=validated.get("depends_on"),
        )
        response = Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)
        _store_outcome(request, response)
        return response


class TaskDetailView(APIView):
    """``GET``/``PATCH /tasks/{id}`` — read everything, edit FR-TSK-02 only."""

    # The PID rides inside the task id (Section 7.3) — scope parsed from
    # it, then the Section 9.2 Owner caller column.
    permission_classes: list[Any] = [HasTaskProjectScope, IsOwnerSession]

    @extend_schema(
        operation_id="retrieve_task",
        responses={status.HTTP_200_OK: TaskSerializer, **_READ_ERRORS},
        description=(
            "Read one task by id (Section 9.2; caller: Owner only). Every "
            "Section 7.2 field is returned. A malformed id answers "
            "VALIDATION_ERROR (400) — the boundary check of Section 7.3; an "
            "unknown but well-formed id answers TASK_NOT_FOUND (404). "
            "Archived and completed tasks remain readable (MT-1.4-06)."
        ),
    )
    def get(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Fetch one task by canonical id."""
        return Response(TaskSerializer(get_task_or_404(id)).data)

    @extend_schema(
        operation_id="partial_update_task",
        request=TaskUpdateSerializer,
        responses={status.HTTP_200_OK: TaskSerializer, **_UPDATE_ERRORS},
        parameters=[_IDEMPOTENCY_PARAMETER],
        description=(
            "Partially update a task (FR-TSK-02 fields; caller: Owner only). "
            "The body must carry the `version` the client saw (FR-TSK-06): a "
            "match applies the change and increments `version`; a stale value "
            "answers VERSION_CONFLICT (409) so a drag-and-drop client never "
            "silently overwrites an agent's change. `state`, lease, merge and "
            "archive fields are not client-settable — they are rejected as "
            "unknown fields (the state machine of WP-1.5 owns `state`). "
            "`Idempotency-Key` replays a retried PATCH (ADR-012). Refused "
            "with TASK_STATE_CONFLICT (409) while the row is `completed` "
            "(FR-TSK-08 read-only; Section 7.4 rule 3) or archived — both "
            "stay fully readable by id and in lists (MT-1.4-06)."
        ),
    )
    def patch(self, request: Request, id: str, *args: Any, **kwargs: Any) -> Response:
        """Apply a version-checked partial update to one task."""
        replayed = _replay_or_none(request)
        if replayed is not None:
            return replayed

        task = get_task_or_404(id)
        input_serializer = TaskUpdateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], input_serializer.validated_data)
        expected_version = int(validated.pop("version"))

        task = update_task(
            task=task,
            validated=validated,
            expected_version=expected_version,
            actor_ref=_created_by(request),
        )
        response = Response(TaskSerializer(task).data)
        _store_outcome(request, response)
        return response
