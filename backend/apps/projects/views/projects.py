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
* **Agent read-only access stays reserved** — Section 9.2's caller column
  ("agents read-only for own project") activates in WP-2.x; until then the
  endpoints answer ``ROLE_NOT_PERMITTED`` for every agent credential (the
  OpenAPI description says so, so no client expects otherwise).
* Unknown ``{pid}`` → ``VALIDATION_ERROR``/400 via the documented
  generic-NotFound mapping (the catalog has no ``PROJECT_NOT_FOUND`` —
  asymmetry with ``TASK_NOT_FOUND`` recorded in the changelog).
* ``project.created`` / ``project.updated`` emission point: the services/
  view call sites below, once WP-1.9's event helper exists.
"""

from __future__ import annotations

from typing import Any, cast

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanManageProjects, HasProjectScope
from apps.core.pagination import decode_str_cursor, parse_page_size, string_id_cursor_page
from apps.core.serializers import ErrorEnvelopeSerializer

from ..models import Project
from ..serializers.projects import (
    ProjectCreateSerializer,
    ProjectListEnvelopeSerializer,
    ProjectListQuerySerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
)
from ..services.projects import create_project, get_project_or_404

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
            "Caller: Owner only — agent read-only access for a token's own "
            "project activates in WP-2.x and is denied until then."
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
            "(Section 7.1). Caller: Owner only."
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
        )
        # Event hook (WP-1.9): emit `project.created` after commit here.
        return Response(
            ProjectSerializer(project).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectDetailView(APIView):
    """GET and PATCH one project addressed by its ``{pid}``."""

    # Scope guard first: a PID00001 agent token on /projects/PID00002 must
    # answer AUTH_FORBIDDEN_PROJECT before the Owner-only role error
    # (ADR-004; WP-1.2 acceptance extended to the real routes here).
    permission_classes: list[Any] = [HasProjectScope, CanManageProjects]

    @extend_schema(
        operation_id="retrieve_project",
        responses={status.HTTP_200_OK: ProjectSerializer, **_READ_ERRORS},
        description=(
            "Read one project. Caller: Owner only — agent read-only access "
            "for a token's own project activates in WP-2.x and is denied "
            "until then. A malformed or unknown pid answers "
            "VALIDATION_ERROR (400): the catalog has no PROJECT_NOT_FOUND."
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
            "`project.updated` once WP-1.9's event helper exists."
        ),
    )
    def patch(self, request: Request, pid: str, *args: Any, **kwargs: Any) -> Response:
        """Apply a partial update to one project."""
        project = get_project_or_404(pid)
        input_serializer = ProjectUpdateSerializer(project, data=request.data, partial=True)
        input_serializer.is_valid(raise_exception=True)
        input_serializer.save()
        # Event hook (WP-1.9): emit `project.updated` after commit here.
        return Response(ProjectSerializer(project).data)
