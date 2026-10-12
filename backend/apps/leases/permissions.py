"""Route guards for the Agent-work endpoints (Section 9.2; MT-1.6-07).

Capability rows live in ``apps.accounts.permissions`` (Section 9.1 —
``accounts`` owns the matrix), so this module only composes them for the
lease endpoints' caller shapes:

* **claim** → :class:`CanClaimTask`, because the single
  ``POST /tasks/{id}/claim`` route carries **two** Section 12.2 rows:
  *Claim pending* (Agent coder) and *Claim to_be_audited* (Agent
  auditor) — the cell is picked from the task's current state, the role
  classes themselves still delegated to accounts verbatim, behind
  ``HasTaskProjectScope`` (ADR-004, the PID rides inside the task id).
* **release** → :class:`CanReleaseTask`, because Section 9.2 lists the
  caller as *Agent* while Section 8.2 T6's Actor column is **C, O** —
  the coder agent (lease holder) *or* an Owner session applying the
  documented override. Devices, auditors and other agent roles are not
  T6 actors and answer ``ROLE_NOT_PERMITTED``.
* **work** → ``IsAgentToken`` (any agent role may *read* its offer list;
  the ``role`` query parameter filters, it does not authorize — claims
  remain the gated operation).
"""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.accounts.models import ApiToken, TokenKind
from apps.accounts.permissions import CanClaimAuditTasks, CanClaimPendingTasks
from apps.tasks.models import Task, TaskState


class CanClaimTask(BasePermission):
    """State-dependent claim cell (Section 12.2's two claim rows).

    ``pending`` (and every non-audit state) answers to the *Claim
    pending* row — coder only; ``to_be_audited`` answers to *Claim
    to_be_audited* — auditor only. An unknown id falls through to the
    pending cell: the view's boundary then answers TASK_NOT_FOUND /
    VALIDATION_ERROR rather than leaking a role answer first.
    """

    message = "This agent's role may not claim tasks in this state."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Delegate to the accounts row for the addressed task's state."""
        kwargs = getattr(view, "kwargs", None) or {}
        addressed = kwargs.get("id")
        state: str | None = None
        if addressed is not None:
            state = Task.objects.filter(pk=str(addressed)).values_list("state", flat=True).first()
        cell = CanClaimAuditTasks if state == TaskState.TO_BE_AUDITED else CanClaimPendingTasks
        return cell().has_permission(request, view)


class CanReleaseTask(BasePermission):
    """Matrix-adjacent row: T6 actors (Section 8.2) — coder agent, Owner."""

    message = "Only the lease-holding coder agent or the owner can release a task."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Owner session, or an agent token carrying the ``coder`` role."""
        token = request.auth
        if not isinstance(token, ApiToken):
            return False  # anonymous → AUTH_REQUIRED via DRF
        if token.kind == TokenKind.OWNER_SESSION:
            return True
        if token.kind == TokenKind.AGENT:
            scopes = token.scopes if isinstance(token.scopes, list) else []
            return "coder" in scopes
        return False
