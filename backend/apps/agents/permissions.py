"""Route guards for the Sessions endpoints (Section 9.2; ADR-004; MT-1.6-09).

Capability rows live in ``apps.accounts.permissions`` (Section 9.1) —
these two are the *endpoint-shape* adapters the Sessions row needs:

* :class:`IsAgentToken` — the Section 9.2 caller column for Sessions is
  **Bridge**, which authenticates with the project-scoped agent token
  (Section 12.2). Owner sessions and devices are not Bridge: they answer
  ``ROLE_NOT_PERMITTED``; anonymous answers ``AUTH_REQUIRED``.
* :class:`HasSessionProjectScope` — the end route addresses a session
  *id*, not a PID, so the ADR-004 scope guard reads the project from
  the session row (still never from the body): an agent token of
  another project answers ``AUTH_FORBIDDEN_PROJECT`` before anything
  else touches the row.
"""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.accounts.exceptions import AuthForbiddenProject
from apps.accounts.models import ApiToken, TokenKind

from .models import AgentSession


def agent_token(request: Request) -> ApiToken | None:
    """The authenticated agent token, or ``None`` (other kinds pass through)."""
    auth = request.auth
    if isinstance(auth, ApiToken) and auth.kind == TokenKind.AGENT:
        return auth
    return None


class IsAgentToken(BasePermission):
    """Bridge caller: a live agent token, nothing else (Section 9.2)."""

    message = "This endpoint requires an agent token (bridge caller)."

    def has_permission(self, request: Request, view: Any) -> bool:
        """True iff authentication produced a live agent token."""
        return agent_token(request) is not None


class HasSessionProjectScope(BasePermission):
    """ADR-004 scoping for ``/agent-sessions/{id}/end`` — the row decides.

    List it first: Zero-Bleed outranks role errors (same ordering rule
    as the task- and project-addressed guards). An unknown id has no
    row to scope against and passes through — the view's boundary
    mapping answers it (the core handler's no-catalog-code reading).
    """

    message = "This token is not scoped to the addressed session's project."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Compare the token's project to the session row's project."""
        token = agent_token(request)
        if token is None:
            return True  # not this guard's refusal — IsAgentToken/auth answer
        kwargs = getattr(view, "kwargs", None) or {}
        session_id = kwargs.get("id")
        if session_id is None:
            return True  # nothing to scope against
        session = AgentSession.objects.filter(pk=str(session_id)).values("project_id").first()
        if session is None:
            return True  # unknown id — the view's NotFound mapping handles it
        if token.project_id is None or token.project_id != session["project_id"]:
            raise AuthForbiddenProject(
                f"Token is scoped to {token.project_id!r}, not {session['project_id']!r}."
            )
        return True
