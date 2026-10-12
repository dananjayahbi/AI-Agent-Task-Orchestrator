"""Route guards for project-addressed endpoints (Section 9.2; ADR-004).

Capability rows stay in ``apps.accounts.permissions`` (Section 9.1 —
``accounts`` owns the matrix); this module holds the *endpoint-shape*
adapter whose caller cell differs per method on the project routes —
the same composition pattern as ``apps.tasks.permissions``.
"""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.accounts.models import ApiToken, TokenKind


class CanReadProject(BasePermission):
    """Section 9.2 Projects-row read caller: Owner session **or** agent token.

    The §9.2 caller cell for ``GET /projects/{pid}`` and
    ``GET /projects/{pid}/policy`` is "Owner; agents read-only for own
    project" — this class expresses which token kinds that cell admits;
    the *own project* half is ``HasProjectScope``'s job and must stay
    listed first (ADR-004: a foreign-project agent token answers
    ``AUTH_FORBIDDEN_PROJECT`` before any role logic).

    Devices are not in the caller cell and answer
    ``ROLE_NOT_PERMITTED``; anonymous callers fail DRF's authentication
    step with ``AUTH_REQUIRED``. PATCH stays behind
    ``CanManageProjects`` (Section 12.2 "Manage projects/policy" —
    reading a project never implies editing it).
    """

    message = "Projects are readable by the owner or an agent token."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Owner session, or any live agent token; other kinds denied."""
        token = request.auth
        if not isinstance(token, ApiToken):
            return False  # anonymous → AUTH_REQUIRED via DRF
        return token.kind in (TokenKind.OWNER_SESSION, TokenKind.AGENT)
