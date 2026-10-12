"""Route guards specific to task-addressed endpoints (Section 9.2; ADR-004).

Capability rows stay in ``apps.accounts.permissions`` (Section 9.1 —
``accounts`` owns the matrix); this module holds the *scope* adapter whose
logic depends on Section 7.3's task-id shape.
"""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.accounts.exceptions import AuthForbiddenProject
from apps.accounts.models import ApiToken, TokenKind
from apps.tasks.services.ids import project_id_of_task


class HasTaskProjectScope(BasePermission):
    """ADR-004 scope guard for ``/tasks/{id}`` — the id embeds the PID.

    Companion of ``accounts.permissions.HasProjectScope``: that guard
    reads a ``pid`` URL kwarg directly; a task id *is*
    ``{PID}-T{index}`` (Section 7.3), so here the addressed project is
    parsed from the task id — still **from the URL, never the body**
    (Section 9.3 step 1; G-07). An agent token for another project answers
    ``AUTH_FORBIDDEN_PROJECT`` **before** any role logic (list it first),
    preserving the WP-1.2 acceptance shape: "a PID00001 agent token
    receives AUTH_FORBIDDEN_PROJECT on any PID00002 resource" — tasks
    included. Non-agent credentials are not project-bound and pass
    through (the Owner-only role class behind this guard still applies).

    A malformed id yields no PID to scope against: the guard lets the
    request through to the role check (agents are refused there anyway by
    Owner-only rows) and the view's boundary validation answers
    ``VALIDATION_ERROR`` for callers that reach it (MT-1.4-03).
    """

    message = "This token is not scoped to the addressed task's project."
    project_url_kwarg = "id"

    def has_permission(self, request: Request, view: Any) -> bool:
        """Compare the token's project to the PID parsed from ``{id}``."""
        token = request.auth
        if not isinstance(token, ApiToken) or token.kind != TokenKind.AGENT:
            return True  # owner/device credentials are not project-bound
        kwargs = getattr(view, "kwargs", None) or {}
        kwarg_name = getattr(view, "project_url_kwarg", self.project_url_kwarg)
        addressed = kwargs.get(kwarg_name)
        pid = project_id_of_task(str(addressed)) if addressed is not None else None
        if pid is None:
            return True  # nothing to scope against; role/validation still apply
        if token.project_id is None or token.project_id != pid:
            raise AuthForbiddenProject(f"Token is scoped to {token.project_id!r}, not {pid!r}.")
        return True
