"""Project CRUD endpoints — Section 9.2 Projects row (MT-1.3-03).

``GET/POST /projects`` and ``GET/PATCH /projects/{pid}``, caller **Owner**
(Section 12.2 "Manage projects/policy" = Owner only — ``CanManageProjects``,
with ``HasProjectScope`` first on the addressed routes so ADR-004's
zero-bleed answer outranks a role error for an agent token pointed at
another project).

Recorded readings (MT-1.3-03, WP changelog):

* **PATCH, not DELETE** — projects are never deleted; pause/archive are
  ``active_status`` transitions (mirrors Section 7.3's task-id continuity
  intent; no ``DELETE /projects/{pid}`` exists in Section 9.2 either).
* **Agent read-only access is active** — Section 9.2's caller cell
  ("agents read-only for own project") is wired on ``GET /projects/{pid}``
  (and ``GET /projects/{pid}/policy``) as the WP-2.x activation the views
  recorded: agent tokens read their own project behind the scope guard,
  every other caller shape (list, create, patch) stays Owner-only, and
  ``GET /projects`` — the *Manage projects/policy* matrix row — remains
  Owner-only because it spans every project. Devices stay denied on the
  detail read (not in the caller cell).
* Unknown ``{pid}`` → ``VALIDATION_ERROR``/400 via the documented
  generic-NotFound mapping (the catalog has no ``PROJECT_NOT_FOUND`` —
  asymmetry with ``TASK_NOT_FOUND`` recorded in the changelog).
* ``project.created`` / ``project.updated`` emissions: written inside
  the same transaction as the change through WP-1.9's event helper
  (``write_event``) — Section 9.6, MT-1.9-02; the schema description
  below says so on the wire.
"""

from __future__ import annotations

from typing import Any, cast

from django.db import transaction
from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanManageProjects, HasProjectScope
from apps.core.pagination import decode_str_cursor, parse_page_size, string_id_cursor_page
from apps.core.serializers import ErrorEnvelopeSerializer
from apps.events.services import write_event

from ..models import Project
from ..permissions import CanReadProject
from ..serializers.projects import (
    ProjectCreateSerializer,
    ProjectListEnvelopeSerializer,
    ProjectListQuerySerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
)
from ..services.projects import create_project, get_project_or_404


def _actor_ref(request: Request) -> str:
    """Section 9.6 ``actor.ref`` for the caller: owner user id, else label.

    Owner-session routes always carry a user pk; the label fallback only
    covers a context without one (mirrors ``_created_by`` in the tasks
    views — MT-1.9-02).
    """
    user_id = getattr(getattr(request, "user", None), "pk", None)
    return str(user_id) if user_id is not None else "owner"


# The owner-side error set shared by every endpoint in this module: bad
# input/unknown pid (400), missing credential (401), wrong role or
# cross-project (403). Owner-session endpoints are deliberately unthrottled
# (FR-SEC-05 scopes RATE_LIMITED to agent/device endpoints), so no 429 is
# documented here — and the Section 7.3 sequence exhaustion on create adds
# 500 (SERVER_ERROR — PidSequenceExhausted).
_CREATE_ERRORS = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
    status.HTTP_500_INTERNAL_SERVER_ERROR: ErrorEnvelopeSerializer,
}
_READ_ERRORS = {
    status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
    status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
    status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
}


class ProjectListCreateView(APIView):
    """GET (list, cursor page) and POST (create with server-assigned PID)."""

    # Section 12.2 "Manage projects/policy": Owner only. No project is
    # addressed by this route, so the ADR-004 scope guard has nothing to
    # compare and is not listed (it fires on ``{pid}`` routes below).
    permission_classes: list[Any] = [CanManageProjects]

    @extend_schema(
        operation_id="list_projects",
        responses={
            status.HTTP_200_OK: ProjectListEnvelopeSerializer,
            status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
            status.HTTP_401_UNAUTHORIZED: ErrorEnvelopeSerializer,
            status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
        },
        parameters=[ProjectListQuerySerializer],
        description=(
            "List registered projects. Sort: project id ascending — PID "
            "generation order, i.e. creation order (zero-padded Section 7.3 "
            "ids make lexicographic order deterministic; pagination.md rule "
            "2). Pagination: cursor-based — pass `cursor` from the previous "
            "`next_cursor`; `page_size` defaults to 25, clamped to 100. "
            "Caller: Owner only — the list spans every project, so agent "
            "tokens are refused here (ROLE_NOT_PERMITTED); an agent reads "
            "its own project through `GET /projects/{pid}` instead."
        ),
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """One cursor page of projects (Section 9.2 pagination rule)."""
        query = ProjectListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        queryset: QuerySet[Project] = Project.objects.all()
        rows, next_cursor = string_id_cursor_page(
            queryset,
            cursor=decode_str_cursor(validated.get("cursor")),
            page_size=parse_page_size(validated.get("page_size")),
        )
        return Response(
            {
                "results": [ProjectSerializer(row).data for row in rows],
                "next_cursor": next_cursor,
            }
        )

    @extend_schema(
        operation_id="create_project",
        request=ProjectCreateSerializer,
        responses={
            status.HTTP_201_CREATED: ProjectSerializer,
            **_CREATE_ERRORS,
        },
        description=(
            "Create a project. The `PID` id is assigned server-side from "
            "the Section 7.3 database sequence — no client-supplied id is "
            "accepted (an `id` key is rejected as unknown). The default "
            "Project Policy (Section 7.2 defaults) is created as a pair "
            "(Section 7.1). Optional `policy_preset` (WP-3.1) seeds the "
            "new policy's three glob fields from a framework preset "
            "(django | nextjs | flutter); omitted = stock Section 7.2 "
            "defaults. Caller: Owner only."
        ),
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Create one project + default policy pair; return the project."""
        input_serializer = ProjectCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated = cast(dict[str, Any], input_serializer.validated_data)

        project = create_project(
            name=validated["name"],
            repo_path=validated["repo_path"],
            default_branch=validated["default_branch"],
            system_prompt_rules=validated.get("system_prompt_rules", ""),
            actor_ref=_actor_ref(request),
            policy_preset=validated.get("policy_preset"),
        )
        return Response(
            ProjectSerializer(project).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectDetailView(APIView):
    """GET and PATCH one project addressed by its ``{pid}``."""

    # Scope guard first: a PID00001 agent token on /projects/PID00002 must
    # answer AUTH_FORBIDDEN_PROJECT before the role error (ADR-004;
    # WP-1.2 acceptance extended to the real routes here). The GET cell is
    # §9.2's "agents read-only for own project"; PATCH keeps the §12.2
    # Manage-projects Owner cell.
    permission_classes: list[Any] = [HasProjectScope, CanManageProjects]

    def get_permissions(self) -> list[Any]:
        """GET answers to the read cell; PATCH to the Owner-only cell."""
        if self.request is not None and self.request.method == "GET":
            return [HasProjectScope(), CanReadProject()]
        return [HasProjectScope(), CanManageProjects()]

    @extend_schema(
        operation_id="retrieve_project",
        responses={status.HTTP_200_OK: ProjectSerializer, **_READ_ERRORS},
        description=(
            "Read one project. Caller: Owner or an agent token scoped to "
            "this project (Section 9.2: agents read-only for own project); "
            "other agent tokens answer AUTH_FORBIDDEN_PROJECT (403) and "
            "devices ROLE_NOT_PERMITTED. A malformed or unknown pid "
            "answers VALIDATION_ERROR (400): the catalog has no "
            "PROJECT_NOT_FOUND."
        ),
    )
    def get(self, request: Request, pid: str, *args: Any, **kwargs: Any) -> Response:
        """Fetch one project by canonical id."""
        return Response(ProjectSerializer(get_project_or_404(pid)).data)

    @extend_schema(
        operation_id="partial_update_project",
        request=ProjectUpdateSerializer,
        responses={status.HTTP_200_OK: ProjectSerializer, **_READ_ERRORS},
        description=(
            "Partially update a project: `name`, `repo_path`, "
            "`default_branch`, `system_prompt_rules`, `active_status` "
            "(transitions among active | paused | archived — FR-PRJ-04; "
            "projects are never deleted). Unspecified fields keep their "
            "current values. The `id` is immutable (Section 7.3/7.4) and "
            "is rejected if sent. Caller: Owner only. Emits "
            "`project.updated` (Section 9.6) inside the update transaction."
        ),
    )
    def patch(self, request: Request, pid: str, *args: Any, **kwargs: Any) -> Response:
        """Apply a partial update to one project."""
        project = get_project_or_404(pid)
        input_serializer = ProjectUpdateSerializer(project, data=request.data, partial=True)
        input_serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            input_serializer.save()
            # Section 9.6 `project.updated` in the same transaction as the
            # change — rollback takes both (MT-1.9-02).
            write_event(
                type="project.updated",
                project_id=project.pk,
                actor_type="owner",
                actor_ref=_actor_ref(request),
                data={"scope": "project", "fields": sorted(input_serializer.validated_data)},
            )
        return Response(ProjectSerializer(project).data)
