"""``GET /projects/{pid}/manifest`` — Section 9.2 Projects row (MT-1.3-05).

Returns the Section 10.3 document as a **downloadable file**
(``Content-Disposition: attachment; filename="orchestrator.json"``),
caller **Owner** (Section 9.2 caller column; Section 12.2
"Manage projects/policy"), ADR-004 scope guard first like every addressed
route.

Recorded notes (MT-1.3-05, WP changelog):

* agents read their own project's manifest through the bridge's local
  file, never through this endpoint (Section 10.3 step 1) — agent access
  stays reserved for WP-2.x, stated in the OpenAPI description;
* the bridge validates the downloaded document against the published
  ``schemas/manifest.v1.json`` (Section 10.3 step 2 — WP-2.2);
* no pagination: the manifest is a single document (MT-1.3-05 confirmed
  with MT-0.5-04's inventory).
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanManageProjects, HasProjectScope

from ..serializers.manifest import OrchestratorManifest
from ..services.manifest import render_manifest
from ..services.projects import get_project_or_404
from .projects import _READ_ERRORS


class ProjectManifestView(APIView):
    """Download the project's orchestrator.json (Section 10.3 contract)."""

    permission_classes: list[Any] = [HasProjectScope, CanManageProjects]

    @extend_schema(
        operation_id="retrieve_project_manifest",
        responses={status.HTTP_200_OK: OrchestratorManifest, **_READ_ERRORS},
        description=(
            "Download the project manifest (orchestrator.json) as an "
            "attachment — the Section 10.3 wire contract: schema_version 1, "
            "the allowlisted keys only, `auto_branch_prefix` from policy "
            "(G-09), `orchestrator_api` from server configuration (NFR-06), "
            "`audit_required_default` from policy. No secret values: safe to "
            "commit (FR-SEC-04). Validate against the published "
            "schemas/manifest.v1.json. Caller: Owner only — agents read "
            "their own project's manifest from the bridge's local file "
            "(Section 10.3), and endpoint access for them activates in "
            "WP-2.x. A malformed or unknown pid answers VALIDATION_ERROR "
            "(400)."
        ),
    )
    def get(self, request: Request, pid: str, *args: Any, **kwargs: Any) -> Response:
        """Render and hand over the manifest document."""
        project = get_project_or_404(pid)
        return Response(
            render_manifest(project),
            headers={"Content-Disposition": 'attachment; filename="orchestrator.json"'},
        )
