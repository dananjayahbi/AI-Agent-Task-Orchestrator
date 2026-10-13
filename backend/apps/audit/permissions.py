"""Route guards for the audit endpoints (Section 9.2 Audit row; WP-3.3).

Capability rows live in ``apps.accounts.permissions`` (Section 9.1 —
``accounts`` owns the matrix), so this module only composes them for the
audit endpoints' caller shapes:

* **verdict POST** → ``accounts.permissions.CanSubmitAuditVerdict`` —
  the Section 12.2 *Submit verdict* row verbatim (agent token with the
  ``auditor`` scope; Owner's cell is **No** there, so the §9.2
  "Auditor / Owner" caller column is read as *the auditor session* for
  the write half — Owner-side submission is wired in WP-4.8, never left
  ambiguous here, per MT-3.3-05's out-of-scope note). Lease ownership
  is the service's fencing gate behind it.
* **reports GET** → :class:`CanReadAuditReports`, the Section 9.2
  *Auditor / Owner* read cell as an endpoint-shape adapter (the
  ``CanReadResolutions`` pattern): owner sessions and agent tokens
  carrying ``auditor``; coder/decomposer/merge-executor agents, devices
  and anonymous callers answer ``ROLE_NOT_PERMITTED``/``AUTH_REQUIRED``.
  ``HasTaskProjectScope`` stays listed first so a foreign-project agent
  still answers ``AUTH_FORBIDDEN_PROJECT`` before any role logic
  (ADR-004 zero-bleed).
"""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.accounts.models import ApiToken, TokenKind


class CanReadAuditReports(BasePermission):
    """Section 9.2 Audit-row read caller: Owner session **or** auditor agent.

    The caller column reads "Auditor / Owner" — narrower than the
    "Agent / Owner" cells: a *coder* agent has no business reading the
    audit trail of its own work before review (and the §12.2 matrix
    prints no audit-read row at all, so this endpoint-shape adapter is
    the closest faithful transcription — recorded in the WP changelog).
    """

    message = "Audit reports are readable by the owner or an auditor agent."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Owner session, or an agent token carrying the auditor scope."""
        token = request.auth
        if not isinstance(token, ApiToken):
            return False  # anonymous → AUTH_REQUIRED via DRF
        if token.kind == TokenKind.OWNER_SESSION:
            return True
        if token.kind == TokenKind.AGENT:
            scopes = token.scopes if isinstance(token.scopes, list) else []
            return "auditor" in scopes
        return False


__all__ = ["CanReadAuditReports"]
