"""Route guards for attachment-addressed endpoints (Section 9.2; ADR-004).

Capability rows stay in ``apps.accounts.permissions`` (Section 9.1 —
``accounts`` owns the matrix); this module holds the *scope* adapters
whose logic depends on how an attachment resolves to a project.

The ``/tasks/{id}/attachments`` routes reuse the tasks app's
``HasTaskProjectScope`` (the PID rides inside the task id — Section
7.3). ``/attachments/{id}`` addresses a **UUID**, which carries no PID,
so :class:`HasAttachmentProjectScope` resolves the row and reads the
project from its owning task — still never from the request body
(Section 9.3 step 1; G-07). An unknown or malformed id yields no row to
scope against: agent tokens are refused (nothing to authorize — deny by
default for the project-bound kind), while owner/device credentials
pass through to the role check and the view's boundary validation
answers ``VALIDATION_ERROR``.

Caller cells (Section 9.2 Attachments row: "Owner / Agent (read)"):
reads admit Owner session **or** a project-scoped agent token
(:class:`CanReadAttachments`); the upload (POST) and delete (DELETE)
halves are Owner-only — Section 9.2 gives agents read access only
(MT-1.11-03 out-of-scope note). Devices are not in the cell and answer
``ROLE_NOT_PERMITTED``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.accounts.exceptions import AuthForbiddenProject
from apps.accounts.models import ApiToken, TokenKind
from apps.attachments.models import TaskAttachment


class HasAttachmentProjectScope(BasePermission):
    """ADR-004 scope guard for ``/attachments/{id}`` — resolve, then compare.

    Companion of ``tasks.permissions.HasTaskProjectScope``: an
    attachment id is a UUID (Section 7.2) with no embedded PID, so the
    addressed project is the row's owning task's project — resolved from
    the **URL**, never the body (G-07). An agent token for another
    project answers ``AUTH_FORBIDDEN_PROJECT`` before any role logic.
    """

    message = "This token is not scoped to the addressed attachment's project."
    attachment_url_kwarg = "id"

    def has_permission(self, request: Request, view: Any) -> bool:
        """Compare the token's project to the attachment's task project."""
        token = request.auth
        if not isinstance(token, ApiToken) or token.kind != TokenKind.AGENT:
            return True  # owner/device credentials are not project-bound
        kwargs = getattr(view, "kwargs", None) or {}
        raw = kwargs.get(self.attachment_url_kwarg)
        try:
            attachment_id: UUID | None = UUID(str(raw)) if raw is not None else None
        except ValueError:
            attachment_id = None
        if attachment_id is None:
            return False  # nothing to scope against — deny for agent tokens
        project_id = (
            TaskAttachment.objects.filter(pk=attachment_id)
            .values_list("task__project_id", flat=True)
            .first()
        )
        if project_id is None:
            return False  # unknown attachment — deny for agent tokens
        if token.project_id is None or token.project_id != project_id:
            raise AuthForbiddenProject(
                f"Token is scoped to {token.project_id!r}, not {project_id!r}."
            )
        return True


class CanReadAttachments(BasePermission):
    """Section 9.2 Attachments read cell: Owner session **or** agent token.

    ``GET /tasks/{id}/attachments`` and ``GET /attachments/{id}`` feed
    the owner's UI and (from WP-2.x) the bridge's
    ``read_task_attachment`` tool — the caller cell this adapter
    expresses admits owner sessions and live agent tokens, with the
    scope guards listed first so a foreign-project agent token still
    answers ``AUTH_FORBIDDEN_PROJECT`` before any role logic
    (ADR-004 zero-bleed). Devices are not in the cell and answer
    ``ROLE_NOT_PERMITTED``; anonymous callers fail DRF's authentication
    step with ``AUTH_REQUIRED``.
    """

    message = "Attachment descriptors are readable by the owner or an agent token."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Owner session, or any live agent token; other kinds denied."""
        token = request.auth
        if not isinstance(token, ApiToken):
            return False  # anonymous → AUTH_REQUIRED via DRF
        return token.kind in (TokenKind.OWNER_SESSION, TokenKind.AGENT)


__all__ = ["CanReadAttachments", "HasAttachmentProjectScope"]
