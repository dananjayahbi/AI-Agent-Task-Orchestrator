"""Permission classes enforcing Sections 12.2 and 9.2 authorization rules.

One **named class per Section 12.2 matrix row** (MT-1.2-05; no row is
silently dropped — the coverage test in ``tests/test_permission_classes.py``
cites every row), plus the ADR-004 project-scope guard. The classes are
deliberately role-*coarse*: the row's allowed actors only. Fine-grained
claim-time rules (lease owner, actor validation) belong to WP-1.5/WP-1.6
(MT-1.2-05 out of scope) and will narrow these at the transition layer.

How DRF turns a refusal into a catalog code (Section 20.4 item 5):

* no credential → the authenticators produced nothing → ``NotAuthenticated``
  → **``AUTH_REQUIRED``** (401);
* wrong kind/role → ``PermissionDenied`` → **``ROLE_NOT_PERMITTED``** (403);
* cross-project → ``AuthForbiddenProject`` raised directly →
  **``AUTH_FORBIDDEN_PROJECT``** (403).

Role vocabulary: agents carry roles in their token's ``scopes`` (the
MT-1.2-02/05 reading — kinds stay closed at three; an agent token with empty
scopes holds no roles). Devices and owner sessions are whole-role
credentials. Device rows were already verified live during authentication
(MT-1.2-04), so kind checks below are sufficient.

The guard resolves the addressed project from the **URL/view**, never from a
request body (Section 9.3 step 1; ADR-004; G-07 — a body-supplied PID can
never widen a token's scope). Endpoint wiring: rows whose endpoints exist
today are already guarded (``IsOwnerSession`` on auth/tokens/devices;
``/health/*`` stays unauthenticated per MT-1.1-03); the capability classes
below ship with this MT so WP-1.3/1.4 endpoints arrive protected by simply
naming the row class.
"""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.accounts.models import ApiToken, TokenKind

from .exceptions import AuthForbiddenProject


def _token(request: Request) -> ApiToken | None:
    """The authenticated API Token row, or ``None`` when unauthenticated."""
    auth = request.auth
    return auth if isinstance(auth, ApiToken) else None


def _has_role(request: Request, role: str) -> bool:
    """True iff an **agent** token carries *role* in its scopes."""
    token = _token(request)
    if token is None or token.kind != TokenKind.AGENT:
        return False
    scopes = token.scopes if isinstance(token.scopes, list) else []
    return role in scopes


def _is_owner_or_device(request: Request) -> bool:
    """Owner session **or** device credential (rows granting both)."""
    token = _token(request)
    return token is not None and token.kind in (
        TokenKind.OWNER_SESSION,
        TokenKind.DEVICE,
    )


def _is_owner(request: Request) -> bool:
    """Owner session credential only."""
    token = _token(request)
    return token is not None and token.kind == TokenKind.OWNER_SESSION


class IsOwnerSession(BasePermission):
    """Owner-session-only endpoints (the 9.2 Owner-caller rows).

    Token management (``/tokens``, ``/devices``) and the auth management
    endpoints answer to this guard on both transports — cookie session or
    the Section 15.4 bearer transport of the same ``owner_session`` token.
    Not a Section 12.2 capability row itself (the matrix has no token/device
    management row; those endpoints follow Section 9.2's Owner caller
    column), hence its own name rather than a capability alias.
    """

    message = "This endpoint requires an owner session."

    def has_permission(self, request: Request, view: Any) -> bool:
        """True iff authentication produced a live ``owner_session`` token."""
        return _is_owner(request)


# --- Section 12.2 matrix rows (one named class per row) --------------------


class CanManageProjects(BasePermission):
    """Matrix row **Manage projects/policy**: Owner only."""

    message = "Only the owner can manage projects and policy."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Owner sessions only — agents and devices are denied."""
        return _is_owner(request)


class CanCreateDraftTasks(BasePermission):
    """Matrix row **Create draft tasks**: Owner, Decomposer, Device (Could).

    The ``Device: Yes (Could)`` cell is **granted** (recorded decision, not a
    hidden one): the mobile app is the owner's own proxy and already holds
    publish/review rights in the same matrix — withholding only drafts would
    be inconsistent. Revisit if the owner later scopes device credentials.
    """

    message = "Only the owner, a decomposer agent or a device can create drafts."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Owner/device credential or the ``decomposer`` agent role."""
        return _is_owner_or_device(request) or _has_role(request, "decomposer")


class CanPublishTasks(BasePermission):
    """Matrix row **Publish tasks**: Owner, Device."""

    message = "Only the owner or a device can publish tasks."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Owner/device credential; agents of every role are denied."""
        return _is_owner_or_device(request)


class CanClaimPendingTasks(BasePermission):
    """Matrix row **Claim pending**: Agent (coder) only — not the owner."""

    message = "Only a coder agent can claim pending tasks."

    def has_permission(self, request: Request, view: Any) -> bool:
        """The ``coder`` role on a live agent token."""
        return _has_role(request, "coder")


class CanClaimAuditTasks(BasePermission):
    """Matrix row **Claim to_be_audited**: Agent (auditor) only."""

    message = "Only an auditor agent can claim audit tasks."

    def has_permission(self, request: Request, view: Any) -> bool:
        """The ``auditor`` role on a live agent token."""
        return _has_role(request, "auditor")


class CanSubmitResolution(BasePermission):
    """Matrix row **Submit resolution**: Agent (coder, lease owner).

    Lease-ownership is enforced by the claim/transition transaction in
    WP-1.5/WP-1.6 (out of scope here — coarse row only).
    """

    message = "Only a coder agent can submit resolutions."

    def has_permission(self, request: Request, view: Any) -> bool:
        """The ``coder`` role on a live agent token."""
        return _has_role(request, "coder")


class CanSubmitAuditVerdict(BasePermission):
    """Matrix row **Submit verdict**: Agent (auditor, lease owner).

    Lease-ownership is enforced by WP-1.5/WP-1.6 (coarse row only).
    """

    message = "Only an auditor agent can submit verdicts."

    def has_permission(self, request: Request, view: Any) -> bool:
        """The ``auditor`` role on a live agent token."""
        return _has_role(request, "auditor")


class CanReviewDecisions(BasePermission):
    """Matrix row **Review decisions**: Owner, Device."""

    message = "Only the owner or a device can record review decisions."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Owner/device credential; agents are denied."""
        return _is_owner_or_device(request)


class CanReadMergeQueue(BasePermission):
    """Matrix row **Merge queue** (the Owner cell is *Read*): Owner, merge executor.

    The row's write half — ``POST /merge/{task}/start|result`` — is the
    separate ``CanOperateMergeQueue`` below (Owner: read only).
    """

    message = "Only the owner or a merge executor agent can read the merge queue."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Owner credential or the ``merge_executor`` agent role."""
        return _is_owner(request) or _has_role(request, "merge_executor")


class CanOperateMergeQueue(BasePermission):
    """Matrix row **Merge queue** (write half): Merge Executor only.

    Owner's cell is *Read* — starting/merging is the merge executor's alone.
    """

    message = "Only a merge executor agent can operate the merge queue."

    def has_permission(self, request: Request, view: Any) -> bool:
        """The ``merge_executor`` role on a live agent token."""
        return _has_role(request, "merge_executor")


class CanReadEvents(BasePermission):
    """Matrix row **Read events**: Owner, Device — **never** an agent.

    Section 9.6: agents do not subscribe to events for any token kind or
    scope (event streams are the owner's dashboard surface), so no
    ``_has_role`` branch exists here by design.
    """

    message = "Agents cannot read events; the owner or a device can."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Owner/device credential; every agent token is denied."""
        return _is_owner_or_device(request)


class HasProjectScope(BasePermission):
    """ADR-004 backend scoping: the token's project **is** the boundary.

    Companion class for project-addressed endpoints (WP-1.3/1.4 and this
    MT's tests): when the caller holds an ``agent`` token, the addressed
    project — read from the URL kwargs under ``project_url_kwarg`` (default
    ``pid``), never from the body — must equal the token's ``project_id``,
    otherwise ``AuthForbiddenProject`` (``AUTH_FORBIDDEN_PROJECT``, 403)
    fires before any role logic. Non-agent tokens are not project-bound
    (Section 7.2) and pass through; list it **first** in
    ``permission_classes`` so Zero-Bleed outranks role errors.
    """

    message = "This token is not scoped to the addressed project."
    # View attribute overriding the URL kwarg name holding the PID.
    project_url_kwarg = "pid"

    def has_permission(self, request: Request, view: Any) -> bool:
        """Compare token scope to the URL project id (never the body)."""
        token = _token(request)
        if token is None or token.kind != TokenKind.AGENT:
            return True  # owner/device credentials are not project-bound
        kwargs = getattr(view, "kwargs", None) or {}
        kwarg_name = getattr(view, "project_url_kwarg", self.project_url_kwarg)
        addressed = kwargs.get(kwarg_name)
        if addressed is None:
            # No project in the route: nothing to scope against (row-level
            # endpoints such as /tokens/{id}); the owning queries scope data.
            return True
        if token.project_id is None or token.project_id != addressed:
            raise AuthForbiddenProject(
                f"Token is scoped to {token.project_id!r}, not {addressed!r}."
            )
        return True
