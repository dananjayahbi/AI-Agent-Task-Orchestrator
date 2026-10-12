"""MT-1.2-05 — permission classes: every Section 12.2 matrix row, cited (20.5).

The parent plan's authorization matrix is restated verbatim below and mapped to
the **named** class that enforces each row in ``apps.accounts.permissions``.
Section 20.5 traceability: the row names are hardcoded here exactly as
Section 12.2 prints them, and two tests fail if a row or a class goes missing —
no matrix row may be silently dropped:

| Capability | Owner | Agent (coder) | Agent (auditor) | Decomposer | Merge Executor | Device |
|---|---|---|---|---|---|---|
| Manage projects/policy | Yes | No | No | No | No | No |
| Create draft tasks | Yes | No | No | Yes | No | Yes (Could) |
| Publish tasks | Yes | No | No | No | No | Yes |
| Claim `pending` | No | Yes | No | No | No | No |
| Claim `to_be_audited` | No | No | Yes | No | No | No |
| Submit resolution | No | Yes (lease owner) | No | No | No | No |
| Submit verdict | No | No | Yes (lease owner) | No | No | No |
| Review decisions | Yes | No | No | No | No | Yes |
| Merge queue | Read | No | No | No | Yes | No |
| Read events | Yes | No | No | No | No | Yes |

Notes recorded from MT-1.2-05's risk notes (no hidden decisions):

* roles ride on agent-token ``scopes`` — kinds stay closed at three; an agent
  token with the role name in ``scopes`` *is* that actor;
* the *Merge queue* row is served by two classes because the Owner cell is
  *Read*: ``CanReadMergeQueue`` mirrors the printed grid, the write half
  (``POST /merge/{task}/start|result``) is ``CanOperateMergeQueue`` — the
  Merge Executor alone;
* the *Create draft tasks* ``Device: Yes (Could)`` cell is **granted**
  (recorded decision in ``CanCreateDraftTasks``'s docstring);
* *Claim*/*Submit resolution*/*Submit verdict* lease-owner qualifiers are
  WP-1.5/1.6 transition-layer guards — these classes enforce the coarse row
  only (out of scope per the MT).

These are class-level contract tests (the MT's unit layer). API-level
behaviour — real credentials, catalog codes on the wire, cross-project
rejection — is ``tests/test_authorization_matrix.py`` (MT-1.2-07).

Run with ``pytest backend/tests -k "permission or authz"`` (MT test command).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from apps.accounts import permissions as permissions_module
from apps.accounts.exceptions import AuthForbiddenProject
from apps.accounts.models import ApiToken, TokenKind
from apps.accounts.permissions import (
    CanClaimAuditTasks,
    CanClaimPendingTasks,
    CanCreateDraftTasks,
    CanManageProjects,
    CanOperateMergeQueue,
    CanPublishTasks,
    CanReadEvents,
    CanReadMergeQueue,
    CanReviewDecisions,
    CanSubmitAuditVerdict,
    CanSubmitResolution,
    HasProjectScope,
    IsOwnerSession,
)
from apps.core.errors import AUTH_FORBIDDEN_PROJECT

# --- Section 12.2 rows, verbatim -------------------------------------------

MATRIX_ROWS: tuple[str, ...] = (
    "Manage projects/policy",
    "Create draft tasks",
    "Publish tasks",
    "Claim pending",
    "Claim to_be_audited",
    "Submit resolution",
    "Submit verdict",
    "Review decisions",
    "Merge queue",
    "Read events",
)

# Row -> the named class(es) enforcing it. Merge queue carries two halves.
ROW_CLASSES: dict[str, tuple[type[BasePermission], ...]] = {
    "Manage projects/policy": (CanManageProjects,),
    "Create draft tasks": (CanCreateDraftTasks,),
    "Publish tasks": (CanPublishTasks,),
    "Claim pending": (CanClaimPendingTasks,),
    "Claim to_be_audited": (CanClaimAuditTasks,),
    "Submit resolution": (CanSubmitResolution,),
    "Submit verdict": (CanSubmitAuditVerdict,),
    "Review decisions": (CanReviewDecisions,),
    "Merge queue": (CanReadMergeQueue, CanOperateMergeQueue),
    "Read events": (CanReadEvents,),
}

# The printed grid: True where the Section 12.2 cell says Yes (the Device
# "Yes (Could)" cell for Create draft tasks is granted — recorded decision).
# `anonymous` is False for every row (unauthenticated -> AUTH_REQUIRED at the
# API layer; a permission class simply does not grant).
ROW_GRANTS: dict[str, dict[str, bool]] = {
    "Manage projects/policy": {
        "owner": True,
        "coder": False,
        "auditor": False,
        "decomposer": False,
        "merge_executor": False,
        "device": False,
        "anonymous": False,
    },
    "Create draft tasks": {
        "owner": True,
        "coder": False,
        "auditor": False,
        "decomposer": True,
        "merge_executor": False,
        "device": True,
        "anonymous": False,
    },
    "Publish tasks": {
        "owner": True,
        "coder": False,
        "auditor": False,
        "decomposer": False,
        "merge_executor": False,
        "device": True,
        "anonymous": False,
    },
    "Claim pending": {
        "owner": False,
        "coder": True,
        "auditor": False,
        "decomposer": False,
        "merge_executor": False,
        "device": False,
        "anonymous": False,
    },
    "Claim to_be_audited": {
        "owner": False,
        "coder": False,
        "auditor": True,
        "decomposer": False,
        "merge_executor": False,
        "device": False,
        "anonymous": False,
    },
    "Submit resolution": {
        "owner": False,
        "coder": True,
        "auditor": False,
        "decomposer": False,
        "merge_executor": False,
        "device": False,
        "anonymous": False,
    },
    "Submit verdict": {
        "owner": False,
        "coder": False,
        "auditor": True,
        "decomposer": False,
        "merge_executor": False,
        "device": False,
        "anonymous": False,
    },
    "Review decisions": {
        "owner": True,
        "coder": False,
        "auditor": False,
        "decomposer": False,
        "merge_executor": False,
        "device": True,
        "anonymous": False,
    },
    "Merge queue": {
        "owner": True,
        "coder": False,
        "auditor": False,
        "decomposer": False,
        "merge_executor": True,
        "device": False,
        "anonymous": False,
    },
    "Read events": {
        "owner": True,
        "coder": False,
        "auditor": False,
        "decomposer": False,
        "merge_executor": False,
        "device": True,
        "anonymous": False,
    },
}

ACTORS: tuple[str, ...] = (
    "owner",
    "coder",
    "auditor",
    "decomposer",
    "merge_executor",
    "device",
    "anonymous",
)

# The project-addressed probe used by the HasProjectScope tests below; the
# body deliberately claims a *different* project so any class that reads the
# body rather than the URL/token would show it here.
_PID_ONE = "PID00001"
_PID_TWO = "PID00002"


def _token_for(actor: str) -> ApiToken | None:
    """The credential an actor presents: roles ride on agent ``scopes``."""
    if actor == "anonymous":
        return None
    if actor == "owner":
        return ApiToken(kind=TokenKind.OWNER_SESSION, scopes=[])
    if actor == "device":
        return ApiToken(kind=TokenKind.DEVICE, scopes=[])
    # coder / auditor / decomposer / merge_executor — the Section 12.2 agent
    # columns, carried as agent-token scopes (MT-1.2-02/05 reading).
    return ApiToken(kind=TokenKind.AGENT, project_id=_PID_ONE, scopes=[actor])


def _request(actor: str) -> Request:
    """A DRF request authenticated as *actor* with a misleading body PID.

    The body always claims ``project_id=PID00002`` — permission classes must
    consult the token and the URL (on the view), never the body
    (Section 9.3 step 1; ADR-004).
    """
    raw = APIRequestFactory().post("/probe", {"project_id": _PID_TWO})
    request = Request(raw)
    request.user = AnonymousUser()
    request.auth = _token_for(actor)
    return request


def _view(pid: str | None = None) -> Any:
    """A stand-in view carrying the URL kwargs a real route would provide."""
    kwargs = {"pid": pid} if pid is not None else {}
    return SimpleNamespace(kwargs=kwargs)


def _allows(permission: type[BasePermission], actor: str, pid: str | None = None) -> bool:
    return bool(permission().has_permission(_request(actor), _view(pid)))


# --- traceability: no row, no class, no silence -----------------------------


def test_every_matrix_row_maps_to_named_classes_citing_the_row() -> None:
    """Section 20.5: rows and classes correspond 1:1 — nothing dropped."""
    assert set(ROW_CLASSES) == set(MATRIX_ROWS)
    module_classes = {
        name
        for name, obj in vars(permissions_module).items()
        if name.startswith("Can") and isinstance(obj, type)
    }
    mapped = {cls.__name__ for classes in ROW_CLASSES.values() for cls in classes}
    assert mapped == module_classes, "every named Can* class maps to a printed row"
    for row, classes in ROW_CLASSES.items():
        for cls in classes:
            doc = (cls.__doc__ or "").lower()
            assert row.lower() in doc, f"{cls.__name__} must cite its Section 12.2 row"


# --- the grid, one case per row per actor -----------------------------------


@pytest.mark.parametrize("row", MATRIX_ROWS)
@pytest.mark.parametrize("actor", ACTORS)
def test_matrix_row_grants_exactly_its_section_12_2_cells(row: str, actor: str) -> None:
    """Each named class allows precisely the actors its printed row allows."""
    expected = ROW_GRANTS[row][actor]
    for cls in ROW_CLASSES[row]:
        if cls is CanOperateMergeQueue:
            # Merge queue write half: Owner's cell is *Read*, so only the
            # Merge Executor starts/merges (split recorded above).
            assert _allows(cls, actor) is (actor == "merge_executor"), cls.__name__
        else:
            assert _allows(cls, actor) is expected, f"{cls.__name__} vs {actor}"


@pytest.mark.parametrize("actor", ACTORS)
def test_agents_never_read_events_for_any_role(actor: str) -> None:
    """Section 9.6 authorization per connection: events are never an agent's."""
    is_agent = actor in ("coder", "auditor", "decomposer", "merge_executor")
    assert _allows(CanReadEvents, actor) is (not is_agent and actor in ("owner", "device"))


def test_is_owner_session_is_the_owner_caller_guard_not_a_capability_row() -> None:
    """Owner-only endpoints (Section 9.2 Owner column): sessions, nobody else."""
    assert _allows(IsOwnerSession, "owner") is True
    for actor in ("coder", "auditor", "decomposer", "merge_executor", "device", "anonymous"):
        assert _allows(IsOwnerSession, actor) is False, actor


# --- HasProjectScope: ADR-004 / G-07 scope guard ---------------------------


def test_agent_scope_is_read_from_token_and_url_never_from_the_body() -> None:
    """Body claims PID00002: the URL's PID00001 wins because the token says so."""
    assert _allows(HasProjectScope, "coder", pid=_PID_ONE) is True

    # ...and the mirror: a body claiming the *token's* project cannot widen a
    # request that addresses PID00002.
    with pytest.raises(AuthForbiddenProject) as excinfo:
        _allows(HasProjectScope, "coder", pid=_PID_TWO)
    assert excinfo.value.default_code == AUTH_FORBIDDEN_PROJECT


def test_non_agent_credentials_are_not_project_bound() -> None:
    """Section 7.2: only agent tokens carry a project — others pass through."""
    for actor in ("owner", "device", "anonymous"):
        assert _allows(HasProjectScope, actor, pid=_PID_TWO) is True, actor


def test_route_without_a_pid_has_nothing_to_scope_against() -> None:
    """Row-level routes (e.g. /tokens/{id}) leave scoping to owning queries."""
    request = _request("coder")
    assert HasProjectScope().has_permission(request, _view(pid=None)) is True


def test_project_url_kwarg_name_is_overridable_per_view() -> None:
    """Future routes may name the PID differently — the attribute overrides."""
    request = _request("coder")
    view = SimpleNamespace(kwargs={"project_id": _PID_TWO}, project_url_kwarg="project_id")
    with pytest.raises(AuthForbiddenProject):
        HasProjectScope().has_permission(request, view)


# --- MT-1.1-03 preserved: health stays unauthenticated ----------------------


def test_health_endpoints_stay_unauthenticated(db: None) -> None:
    """/health/live and /health/ready answer anonymous callers (MT-1.1-03)."""
    client = APIClient()
    for path in ("/health/live", "/health/ready"):
        response = client.get(path)
        assert response.status_code == 200, path
