"""``GET/PATCH /projects/{pid}/policy`` — Section 9.2 Projects row (MT-1.3-04).

Caller **Owner** (Section 12.2 "Manage projects/policy"), with the ADR-004
scope guard first — the same answer set as the project routes: agent token
aimed elsewhere → ``AUTH_FORBIDDEN_PROJECT``, agent token aimed here →
``ROLE_NOT_PERMITTED``, no credential → ``AUTH_REQUIRED``.

Recorded notes (MT-1.3-04, WP changelog):

* this endpoint is **the only supported way to change policy**
  (Section 12.5; FR-PRJ-05's validated write path) — the Policy Engine
  (WP-3.x), lease sweeper (WP-1.7) and claim limit (WP-1.6) read the rows
  it writes;
* policy edits are state changes: the audit/event emission point is the
  ``save`` call below, once WP-1.9's helper exists (Section 12.5 requires
  policy edits in the audit trail — recorded hook, not emitted yet);
* bounds follow Section 7.2 only — nothing beyond it is clamped or
  invented (risk note); glob semantics stay with the Policy Engine.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanManageProjects, HasProjectScope

from ..serializers.policy import ProjectPolicySerializer
from ..services.projects import get_project_or_404
from .projects import _READ_ERRORS


class ProjectPolicyDetailView(APIView):
    """Read and partially update one project's Section 7.2 policy."""

    permission_classes: list[Any] = [HasProjectScope, CanManageProjects]

    @extend_schema(
        operation_id="retrieve_project_policy",
        responses={status.HTTP_200_OK: ProjectPolicySerializer, **_READ_ERRORS},
        description=(
            "Read the project's full policy with current values (Section 7.2 "
            "field names and documented defaults). Caller: Owner only — "
            "agent access activates in WP-2.x and is denied until then. A "
            "malformed or unknown pid answers VALIDATION_ERROR (400)."
        ),
    )
    def get(self, request: Request, pid: str, *args: Any, **kwargs: Any) -> Response:
        """Full policy document for the addressed project."""
        project = get_project_or_404(pid)
        return Response(ProjectPolicySerializer(project.agent_policy).data)

    @extend_schema(
        operation_id="partial_update_project_policy",
        request=ProjectPolicySerializer,
        responses={status.HTTP_200_OK: ProjectPolicySerializer, **_READ_ERRORS},
        description=(
            "Partially update the policy — the only supported way to change "
            "it (Section 12.5). Validation states exactly what Section 7.2 "
            "states: enums (`lease_extension_mode`, `merge_strategy`), "
            "positive durations/retries/thresholds, `auditor_min_confidence` "
            "1-5, `max_concurrent_tasks` >= 0, non-empty branch prefix and "
            "glob lists when supplied; unknown fields are rejected, never "
            "ignored. Unspecified fields keep their current values. "
            "`branch_prefix` is the G-09 canonical prefix (default "
            "`feat/{PID}-`) applied when bridge branch names are derived. "
            "Caller: Owner only. Policy edits emit an audit event once "
            "WP-1.9's helper exists."
        ),
    )
    def patch(self, request: Request, pid: str, *args: Any, **kwargs: Any) -> Response:
        """Apply a partial, validated update to the project's policy."""
        project = get_project_or_404(pid)
        input_serializer = ProjectPolicySerializer(
            project.agent_policy, data=request.data, partial=True
        )
        input_serializer.is_valid(raise_exception=True)
        input_serializer.save()
        # Audit/event hook (WP-1.9, Section 12.5): emit `policy.updated`
        # (with actor + correlation id) after commit here.
        return Response(ProjectPolicySerializer(project.agent_policy).data)
